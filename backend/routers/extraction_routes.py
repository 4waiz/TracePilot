"""PDF extraction routes: LLM-based and regex-fallback spec extraction."""

import json
import re
from typing import List, Optional

import chromadb
import httpx
import pdfplumber
from chromadb.config import Settings as ChromaSettings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import CriticalSpec, Document, InspectionStep, Job, User
from backend.auth import get_current_user
from backend.audit import create_audit_log
from backend.config import settings
from backend.schemas import CriticalSpecCreate, CriticalSpecOut, InspectionStepCreate, InspectionStepOut

router = APIRouter(prefix="/api/extraction", tags=["extraction"])

# ---------------------------------------------------------------------------
# Regex-based fallback extractor
# ---------------------------------------------------------------------------

_PAT_PLUSMINUS = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z\s]{0,40}?)\s*[:=]\s*"
    r"(?P<nom>\d{1,6}\.?\d*)\s*[±]\s*"
    r"(?P<tol>\d{1,5}\.?\d*)\s*"
    r"(?P<unit>[a-zA-Zμ°\"\']{1,6})"
)

_PAT_ASYM = re.compile(
    r"[ØD]?\s*(?P<nom>[\d]+\.?\d*)\s+"
    r"\+(?P<upper>[\d]+\.?\d*)\s*/\s*-\s*(?P<lower>[\d]+\.?\d*)"
)

_PAT_RANGE = re.compile(
    r"(?P<nom>\d{1,6}\.\d+)\s*(?P<unit>[a-zA-Zμ°\"\']{1,6})\s*"
    r"\(\s*(?P<lo>\d{1,6}\.\d+)\s*[-–]\s*(?P<hi>\d{1,6}\.\d+)\s*\)"
)

_PAT_LABELED = re.compile(
    r"(?P<name>[A-Za-z\s]+):\s*(?P<nom>[\d]+\.?\d*)\s*(?P<unit>[a-zA-Zμ°\"\']*)"
    r",?\s*[Tt]olerance:\s*[±]?\s*(?P<tol>[\d]+\.?\d*)"
)

_VALID_UNITS = {"mm", "cm", "m", "in", "μm", "um", "deg", "°", '"', "'", "ra"}


def _regex_extract_specs(text: str, doc_name: str = "") -> List[dict]:
    specs: List[dict] = []
    seen: set = set()

    def _add(name: str, nominal: float, lower: float, upper: float, unit: str, page: int = 0):
        # Sanity check 1: reject physically implausible nominals
        if nominal < 0.01 or nominal > 10_000:
            return
        # Sanity check 2: limits must be ordered and band must be non-zero
        if lower >= upper:
            return
        # Sanity check 3: reject non-engineering units (catches dates, revision codes)
        if unit and unit.lower() not in _VALID_UNITS:
            return
        key = (round(nominal, 5), round(lower, 5), round(upper, 5))
        if key in seen:
            return
        seen.add(key)
        # Real confidence scoring based on how many fields are populated
        score = 0.40  # base: we have a nominal
        if name.strip():
            score += 0.15   # named feature is more trustworthy
        if unit:
            score += 0.15   # has a unit
        if lower != nominal and upper != nominal:
            score += 0.20   # has both tolerance bounds (not degenerate)
        if nominal > 0 and abs(upper - lower) < nominal * 0.05:
            score += 0.10   # tight tolerance = probably real engineering spec
        specs.append({
            "characteristic": name.strip() or f"Dimension {nominal}",
            "nominal": nominal,
            "lower_limit": lower,
            "upper_limit": upper,
            "unit": unit or "mm",
            "source_document": doc_name,
            "source_page": page,
            "confidence": round(score, 2),
        })

    for m in _PAT_LABELED.finditer(text):
        nom = float(m.group("nom"))
        tol = float(m.group("tol"))
        _add(m.group("name"), nom, nom - tol, nom + tol, m.group("unit"))

    for m in _PAT_RANGE.finditer(text):
        nom = float(m.group("nom"))
        _add("", nom, float(m.group("lo")), float(m.group("hi")), m.group("unit"))

    for m in _PAT_ASYM.finditer(text):
        nom = float(m.group("nom"))
        _add("", nom, nom - float(m.group("lower")), nom + float(m.group("upper")), "mm")

    for m in _PAT_PLUSMINUS.finditer(text):
        nom = float(m.group("nom"))
        tol = float(m.group("tol"))
        _add(m.group("name"), nom, nom - tol, nom + tol, m.group("unit"))

    return specs


def _generate_default_steps(specs: List[dict]) -> List[dict]:
    steps = []
    for i, spec in enumerate(specs, 1):
        steps.append({
            "step_number": i,
            "title": f"Measure {spec['characteristic']}",
            "description": (
                f"Measure {spec['characteristic']}: "
                f"nominal {spec['nominal']} {spec['unit']}, "
                f"limits [{spec['lower_limit']}, {spec['upper_limit']}]"
            ),
            "spec_characteristic": spec["characteristic"],
        })
    return steps


# ---------------------------------------------------------------------------
# LLM extraction via Ollama
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
You are a certified metrology engineer and GD&T (Geometric Dimensioning & Tolerancing) specialist.
Analyze the following engineering drawing or inspection document text and extract ALL critical
dimensional specifications and the inspection steps needed to verify them.

CONTEXT — Engineering documents use notation like:
  - "Ø25.400 ±0.013" → diameter 25.400mm, bilateral tolerance ±0.013mm
  - "10.000 +0.018/-0.000" → asymmetric: lower_limit=nominal, upper_limit=nominal+0.018
  - "Ra 0.800 (max 1.600) μm" → surface roughness, nominal=0.800, upper_limit=1.600
  - "M12.700 ±0.025" → thread pitch diameter in mm
  - "150.000 ±0.050" → linear dimension, bilateral tolerance
  - "Unless otherwise specified: ±0.050mm" → general tolerance block

Return ONLY valid JSON — no markdown fences, no explanation, no trailing text:
{{
  "specs": [
    {{
      "characteristic": "human-readable name (e.g. Outer Diameter, Bore ID, Thread Pitch Dia)",
      "nominal": 25.400,
      "upper_limit": 25.413,
      "lower_limit": 25.387,
      "unit": "mm",
      "source_page": 1,
      "confidence": 0.95
    }}
  ],
  "steps": [
    {{
      "step_number": 1,
      "title": "short action title (e.g. Measure Outer Diameter)",
      "description": "detailed procedure including measurement points, instrument, and technique",
      "spec_characteristic": "must match a characteristic name from specs above",
      "source_page": 1
    }}
  ]
}}

Rules:
- confidence: 0.95 if tolerance is explicitly stated, 0.70 if inferred from a general tolerance block
- unit: use "mm" for linear dimensions, "μm" for surface finish, "°" for angles
- Do NOT invent specs not present in the document text
- Do NOT extract dates, revision numbers, document numbers, or part numbers — these are never dimensional specs
- If a dimension appears multiple times, emit it once with the strictest (smallest) tolerance

DOCUMENT TEXT:
{text}
"""


async def _llm_extract(text: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": _EXTRACTION_PROMPT.format(text=text[:8000]),
                    "stream": False,
                    "format": "json",
                },
            )
            if resp.status_code != 200:
                return None
            body = resp.json()
            raw = body.get("response", "").strip()
            # Strip accidental markdown fences some models add despite format=json
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ChromaDB RAG pipeline
# ---------------------------------------------------------------------------

_chroma_client: Optional[chromadb.PersistentClient] = None


def _get_chroma_client() -> Optional[chromadb.PersistentClient]:
    global _chroma_client
    if _chroma_client is None:
        try:
            _chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_DIR,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        except Exception:
            return None
    return _chroma_client


async def _embed_text(text: str) -> Optional[List[float]]:
    """Call Ollama nomic-embed-text to get an embedding vector."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text},
            )
            if resp.status_code != 200:
                return None
            return resp.json().get("embedding")
    except Exception:
        return None


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[dict]:
    """Split text into overlapping word-boundary chunks."""
    chunks = []
    start = 0
    chunk_id = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            space = text.rfind(" ", start, end)
            if space > start:
                end = space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"text": chunk, "chunk_id": chunk_id})
            chunk_id += 1
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks


async def _build_rag_collection(job_id: int, full_text: str) -> Optional[str]:
    """
    Chunk full_text, embed each chunk via Ollama, store in ChromaDB.
    Returns collection name on success, None if Ollama or ChromaDB unavailable.
    """
    chunks = _chunk_text(full_text)
    if not chunks:
        return None

    # Probe: check Ollama is reachable before committing to the full build
    probe = await _embed_text(chunks[0]["text"])
    if probe is None:
        return None

    client = _get_chroma_client()
    if client is None:
        return None

    collection_name = f"job_{job_id}"
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    ids, embeddings, documents = [], [], []
    for chunk in chunks:
        vec = await _embed_text(chunk["text"])
        if vec is None:
            continue
        ids.append(f"{collection_name}_chunk_{chunk['chunk_id']}")
        embeddings.append(vec)
        documents.append(chunk["text"])

    if ids:
        collection.add(ids=ids, embeddings=embeddings, documents=documents)

    return collection_name


async def _find_source_snippet(collection_name: str, query: str) -> Optional[str]:
    """
    Search the ChromaDB collection for the chunk most similar to query.
    Returns the chunk text (≤400 chars) or None if not relevant enough.
    """
    try:
        client = _get_chroma_client()
        if client is None:
            return None
        collection = client.get_collection(collection_name)
        vec = await _embed_text(query)
        if vec is None:
            return None
        results = collection.query(
            query_embeddings=[vec],
            n_results=1,
            include=["documents", "distances"],
        )
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        if not docs:
            return None
        # Only accept if cosine distance < 0.5 (reasonably relevant)
        if distances[0] > 0.5:
            return None
        return docs[0][:400]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/{job_id}/extract")
async def extract_specs(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    docs = db.query(Document).filter(Document.job_id == job_id).all()
    if not docs:
        raise HTTPException(status_code=400, detail="No documents uploaded for this job")

    full_text = ""
    for doc in docs:
        try:
            with pdfplumber.open(doc.file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to read PDF '{doc.original_filename}': {exc}",
            )

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the PDFs")

    job.status = "extracting"
    db.commit()

    # Build RAG collection (silently skipped if Ollama is down or ChromaDB unavailable)
    rag_collection = await _build_rag_collection(job_id, full_text)

    # Try LLM first, then regex fallback
    extraction_method = "llm"
    result = await _llm_extract(full_text)

    if result is None or "specs" not in result:
        extraction_method = "regex"
        doc_name = docs[0].original_filename if docs else ""
        raw_specs = _regex_extract_specs(full_text, doc_name)
        raw_steps = _generate_default_steps(raw_specs)
        result = {"specs": raw_specs, "steps": raw_steps}

    # Persist specs
    created_specs = []
    for s in result.get("specs", []):
        # RAG: find the most relevant source snippet for this spec
        snippet = None
        if rag_collection:
            query = f"{s.get('characteristic', '')} {s.get('nominal', '')} {s.get('unit', '')}"
            snippet = await _find_source_snippet(rag_collection, query)

        spec = CriticalSpec(
            job_id=job_id,
            characteristic=s.get("characteristic", "Unknown"),
            nominal=s.get("nominal", 0.0),
            upper_limit=s.get("upper_limit", 0.0),
            lower_limit=s.get("lower_limit", 0.0),
            unit=s.get("unit", "mm"),
            source_document=s.get("source_document", docs[0].original_filename if docs else ""),
            source_page=s.get("source_page"),
            source_snippet=snippet,
            confirmed_by_user=False,
            confidence=s.get("confidence") or (0.7 if extraction_method == "regex" else 0.85),
        )
        db.add(spec)
        created_specs.append(spec)

    # Persist steps
    created_steps = []
    for st_data in result.get("steps", []):
        # RAG: find the most relevant source snippet for this step
        snippet = None
        if rag_collection:
            query = f"{st_data.get('title', '')} {st_data.get('spec_characteristic', '')}"
            snippet = await _find_source_snippet(rag_collection, query)

        step = InspectionStep(
            job_id=job_id,
            step_number=st_data.get("step_number", 0),
            title=st_data.get("title", ""),
            description=st_data.get("description", ""),
            spec_characteristic=st_data.get("spec_characteristic", ""),
            source_page=st_data.get("source_page"),
            source_snippet=snippet,
        )
        db.add(step)
        created_steps.append(step)

    job.status = "review"
    db.commit()
    for obj in created_specs + created_steps:
        db.refresh(obj)

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="extract_specs",
        resource_type="job",
        resource_id=str(job_id),
        details=f"Extracted {len(created_specs)} spec(s) and {len(created_steps)} step(s) using {extraction_method}",
    )

    return {
        "method": extraction_method,
        "specs_count": len(created_specs),
        "steps_count": len(created_steps),
        "specs": [_spec_dict(s) for s in created_specs],
        "steps": [_step_dict(s) for s in created_steps],
    }


def _spec_dict(s: CriticalSpec) -> dict:
    return {
        "id": s.id,
        "characteristic": s.characteristic,
        "nominal": s.nominal,
        "upper_limit": s.upper_limit,
        "lower_limit": s.lower_limit,
        "unit": s.unit,
        "confirmed_by_user": s.confirmed_by_user,
        "confidence": s.confidence,
        "source_document": s.source_document,
        "source_page": s.source_page,
        "source_snippet": s.source_snippet,
    }


def _step_dict(s: InspectionStep) -> dict:
    return {
        "id": s.id,
        "step_number": s.step_number,
        "title": s.title,
        "description": s.description,
        "spec_characteristic": s.spec_characteristic,
        "source_document": s.source_document,
        "source_page": s.source_page,
        "source_snippet": s.source_snippet,
    }


# -- Specs CRUD --

@router.get("/{job_id}/specs", response_model=List[CriticalSpecOut])
def get_specs(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db.query(CriticalSpec).filter(CriticalSpec.job_id == job_id).all()


@router.put("/specs/{spec_id}", response_model=CriticalSpecOut)
def update_spec(
    spec_id: int,
    payload: CriticalSpecCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    spec = db.query(CriticalSpec).filter(CriticalSpec.id == spec_id).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    for field in ("characteristic", "nominal", "upper_limit", "lower_limit", "unit", "tool_required"):
        val = getattr(payload, field, None)
        if val is not None:
            setattr(spec, field, val)
    spec.confirmed_by_user = False
    db.commit()
    db.refresh(spec)
    return spec


@router.delete("/specs/{spec_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spec(
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    spec = db.query(CriticalSpec).filter(CriticalSpec.id == spec_id).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    db.delete(spec)
    db.commit()


@router.post("/{job_id}/specs", response_model=CriticalSpecOut, status_code=201)
def add_spec(
    job_id: int,
    payload: CriticalSpecCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    spec = CriticalSpec(
        job_id=job_id,
        characteristic=payload.characteristic,
        nominal=payload.nominal,
        upper_limit=payload.upper_limit,
        lower_limit=payload.lower_limit,
        unit=payload.unit,
        tool_required=payload.tool_required,
        confirmed_by_user=False,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


@router.post("/{job_id}/confirm")
def confirm_specs(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    specs = db.query(CriticalSpec).filter(CriticalSpec.job_id == job_id).all()
    if not specs:
        raise HTTPException(status_code=400, detail="No specs to confirm")

    for spec in specs:
        spec.confirmed_by_user = True

    job.status = "inspecting"
    db.commit()

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="confirm_specs",
        resource_type="job",
        resource_id=str(job_id),
        details=f"Confirmed {len(specs)} spec(s)",
    )
    return {"confirmed": len(specs)}


# -- Steps CRUD --

@router.get("/{job_id}/steps", response_model=List[InspectionStepOut])
def get_steps(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return (
        db.query(InspectionStep)
        .filter(InspectionStep.job_id == job_id)
        .order_by(InspectionStep.step_number)
        .all()
    )


@router.put("/steps/{step_id}", response_model=InspectionStepOut)
def update_step(
    step_id: int,
    payload: InspectionStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    step = db.query(InspectionStep).filter(InspectionStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    for field in ("step_number", "title", "description", "spec_characteristic"):
        val = getattr(payload, field, None)
        if val is not None:
            setattr(step, field, val)
    db.commit()
    db.refresh(step)
    return step


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step(
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    step = db.query(InspectionStep).filter(InspectionStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    db.delete(step)
    db.commit()


@router.post("/{job_id}/steps", response_model=InspectionStepOut, status_code=201)
def add_step(
    job_id: int,
    payload: InspectionStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    step = InspectionStep(
        job_id=job_id,
        step_number=payload.step_number,
        title=payload.title,
        description=payload.description,
        spec_characteristic=payload.spec_characteristic,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step
