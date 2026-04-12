"""PDF extraction routes: LLM-based and regex-fallback spec extraction."""

import json
import re
from typing import List, Optional

import httpx
import pdfplumber
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
    r"(?P<name>[A-Za-z\s]*?)\s*[:=]?\s*"
    r"(?P<nom>[\d]+\.?\d*)\s*"
    r"(?:[±\+\-/]+)\s*"
    r"(?P<tol>[\d]+\.?\d*)\s*"
    r"(?P<unit>[a-zA-Zμ°\"\']+)?"
)

_PAT_ASYM = re.compile(
    r"[ØD]?\s*(?P<nom>[\d]+\.?\d*)\s+"
    r"\+(?P<upper>[\d]+\.?\d*)\s*/\s*-\s*(?P<lower>[\d]+\.?\d*)"
)

_PAT_RANGE = re.compile(
    r"(?P<nom>[\d]+\.?\d*)\s*(?P<unit>[a-zA-Zμ°\"\']*)\s*"
    r"\(\s*(?P<lo>[\d]+\.?\d*)\s*[-–]\s*(?P<hi>[\d]+\.?\d*)\s*\)"
)

_PAT_LABELED = re.compile(
    r"(?P<name>[A-Za-z\s]+):\s*(?P<nom>[\d]+\.?\d*)\s*(?P<unit>[a-zA-Zμ°\"\']*)"
    r",?\s*[Tt]olerance:\s*[±]?\s*(?P<tol>[\d]+\.?\d*)"
)


def _regex_extract_specs(text: str, doc_name: str = "") -> List[dict]:
    specs: List[dict] = []
    seen: set = set()

    def _add(name: str, nominal: float, lower: float, upper: float, unit: str, page: int = 0):
        key = (round(nominal, 5), round(lower, 5), round(upper, 5))
        if key in seen:
            return
        seen.add(key)
        specs.append({
            "characteristic": name.strip() or f"Dimension {nominal}",
            "nominal": nominal,
            "lower_limit": lower,
            "upper_limit": upper,
            "unit": unit or "mm",
            "source_document": doc_name,
            "source_page": page,
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
You are an expert metrology engineer. Analyze the following engineering document text
and extract ALL critical dimensional specifications and inspection steps.

Return ONLY valid JSON in this exact schema (no markdown fences, no extra text):
{{
  "specs": [
    {{
      "characteristic": "descriptive name",
      "nominal": 0.0,
      "upper_limit": 0.0,
      "lower_limit": 0.0,
      "unit": "mm"
    }}
  ],
  "steps": [
    {{
      "step_number": 1,
      "title": "short title",
      "description": "detailed description",
      "spec_characteristic": "matching characteristic name from specs"
    }}
  ]
}}

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
            raw = body.get("response", "")
            return json.loads(raw)
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
        spec = CriticalSpec(
            job_id=job_id,
            characteristic=s.get("characteristic", "Unknown"),
            nominal=s.get("nominal", 0.0),
            upper_limit=s.get("upper_limit", 0.0),
            lower_limit=s.get("lower_limit", 0.0),
            unit=s.get("unit", "mm"),
            source_document=s.get("source_document", ""),
            source_page=s.get("source_page"),
            confirmed_by_user=False,
            confidence=0.7 if extraction_method == "regex" else 0.85,
        )
        db.add(spec)
        created_specs.append(spec)

    # Persist steps
    created_steps = []
    for st_data in result.get("steps", []):
        step = InspectionStep(
            job_id=job_id,
            step_number=st_data.get("step_number", 0),
            title=st_data.get("title", ""),
            description=st_data.get("description", ""),
            spec_characteristic=st_data.get("spec_characteristic", ""),
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
    }


def _step_dict(s: InspectionStep) -> dict:
    return {
        "id": s.id,
        "step_number": s.step_number,
        "title": s.title,
        "description": s.description,
        "spec_characteristic": s.spec_characteristic,
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
