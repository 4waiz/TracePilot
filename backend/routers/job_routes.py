"""Job CRUD and status management routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Job, User
from backend.auth import get_current_user, require_role
from backend.audit import create_audit_log
from backend.schemas import JobCreate, JobOut, JobStatusUpdate

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

VALID_TRANSITIONS = {
    "created": ["uploading", "extracting"],
    "uploading": ["extracting"],
    "extracting": ["review"],
    "review": ["inspecting"],
    "inspecting": ["deviation", "completed"],
    "deviation": ["inspecting", "completed"],
    "completed": [],
}


@router.post("/", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator", "supervisor", "admin")),
):
    job = Job(
        title=payload.title,
        sensitivity_label=payload.sensitivity_label.value if hasattr(payload.sensitivity_label, 'value') else payload.sensitivity_label,
        description=payload.description,
        status="created",
        created_by=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="create_job",
        resource_type="job",
        resource_id=str(job.id),
        details=f"Created job '{job.title}' [{job.sensitivity_label}]",
    )
    return job


@router.get("/", response_model=List[JobOut])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "operator":
        return db.query(Job).filter(Job.created_by == current_user.id).all()
    return db.query(Job).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role == "operator" and job.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return job


@router.patch("/{job_id}/status", response_model=JobOut)
def update_job_status(
    job_id: int,
    payload: JobStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    allowed = VALID_TRANSITIONS.get(job.status, [])
    if payload.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{job.status}' to '{payload.status}'. Allowed: {allowed}",
        )

    old_status = job.status
    job.status = payload.status
    db.commit()
    db.refresh(job)

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="update_job_status",
        resource_type="job",
        resource_id=str(job.id),
        details=f"Status changed from '{old_status}' to '{job.status}'",
    )
    return job
