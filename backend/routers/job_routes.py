"""Job CRUD and status management routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Approval, CriticalSpec, Deviation, Document, Job,
    MeasurementEntry, User,
)
from backend.auth import get_current_user, require_role
from backend.audit import create_audit_log
from backend.schemas import JobCreate, JobOut, JobStatusUpdate

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# "uploading" removed -- document upload never set that status, so it was
# dead state.  Transitions now go directly created → extracting.
VALID_TRANSITIONS = {
    "created": ["extracting"],
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
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Job)
    if current_user.role == "operator":
        q = q.filter(Job.created_by == current_user.id)
    return q.order_by(Job.id.desc()).offset(skip).limit(limit).all()


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


@router.get("/{job_id}/summary")
def get_job_summary(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return job + docs + specs + measurements + deviations in one call."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role == "operator" and job.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    docs = db.query(Document).filter(Document.job_id == job_id).all()
    specs = (
        db.query(CriticalSpec)
        .filter(CriticalSpec.job_id == job_id)
        .all()
    )
    measurements = (
        db.query(MeasurementEntry)
        .filter(MeasurementEntry.job_id == job_id)
        .all()
    )
    deviations = db.query(Deviation).filter(Deviation.job_id == job_id).all()

    # Lookup usernames for measured_by
    user_ids = {m.measured_by for m in measurements}
    user_ids.add(job.created_by)
    if job.assigned_supervisor:
        user_ids.add(job.assigned_supervisor)
    users = {u.id: u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    spec_map = {s.id: s for s in specs}

    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "status": job.status,
            "sensitivity_label": job.sensitivity_label,
            "created_by": job.created_by,
            "creator_name": users.get(job.created_by, str(job.created_by)),
            "assigned_supervisor": job.assigned_supervisor,
            "supervisor_name": users.get(job.assigned_supervisor) if job.assigned_supervisor else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        },
        "documents": [
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "file_size": d.file_size,
                "upload_time": d.upload_time.isoformat() if d.upload_time else None,
            }
            for d in docs
        ],
        "specs": [
            {
                "id": s.id,
                "characteristic": s.characteristic,
                "nominal": s.nominal,
                "lower_limit": s.lower_limit,
                "upper_limit": s.upper_limit,
                "unit": s.unit,
                "confirmed_by_user": s.confirmed_by_user,
            }
            for s in specs
        ],
        "measurements": [
            {
                "id": m.id,
                "spec_id": m.spec_id,
                "spec_name": spec_map[m.spec_id].characteristic if m.spec_id in spec_map else f"Spec {m.spec_id}",
                "actual_value": m.actual_value,
                "passed": m.passed,
                "measured_by": m.measured_by,
                "measured_by_name": users.get(m.measured_by, str(m.measured_by)),
                "notes": m.notes,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in measurements
        ],
        "deviations": [
            {
                "id": dv.id,
                "spec_id": dv.spec_id,
                "expected_value": dv.expected_value,
                "actual_value": dv.actual_value,
                "status": dv.status,
                "notes": dv.notes,
            }
            for dv in deviations
        ],
    }


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
