"""Document upload and download routes."""

import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Document, Job, User
from backend.auth import get_current_user
from backend.audit import create_audit_log
from backend.config import settings
from backend.schemas import DocumentOut

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf"}
MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _validate_pdf(filename: str) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only PDF files are allowed. Got '{ext}'",
        )


@router.post("/upload/{job_id}", response_model=List[DocumentOut], status_code=201)
async def upload_documents(
    job_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_upload_dir = os.path.join(settings.UPLOAD_DIR, str(job_id))
    os.makedirs(job_upload_dir, exist_ok=True)

    created_docs: List[Document] = []
    for f in files:
        _validate_pdf(f.filename)

        safe_name = f"{uuid.uuid4().hex}_{f.filename}"
        file_path = os.path.join(job_upload_dir, safe_name)

        content = await f.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File '{f.filename}' exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit",
            )
        with open(file_path, "wb") as out:
            out.write(content)

        doc = Document(
            job_id=job_id,
            filename=safe_name,
            original_filename=f.filename,
            file_path=file_path,
            file_size=len(content),
            uploaded_by=current_user.id,
        )
        db.add(doc)
        created_docs.append(doc)

    db.commit()
    for doc in created_docs:
        db.refresh(doc)

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="upload_documents",
        resource_type="document",
        resource_id=str(job_id),
        details=f"Uploaded {len(created_docs)} document(s)",
    )
    return created_docs


@router.get("/job/{job_id}", response_model=List[DocumentOut])
def list_documents(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db.query(Document).filter(Document.job_id == job_id).all()


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.isfile(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        doc.file_path,
        media_type="application/pdf",
        filename=doc.original_filename,
    )
