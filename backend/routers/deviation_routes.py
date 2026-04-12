"""Deviation management and approval routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Approval, CriticalSpec, Deviation, Job, MeasurementEntry, User
from backend.auth import get_current_user, require_role
from backend.audit import create_audit_log
from backend.schemas import DeviationOut, DeviationUpdate, ApprovalCreate, ApprovalOut

router = APIRouter(prefix="/api/deviations", tags=["deviations"])


@router.get("/{job_id}", response_model=List[DeviationOut])
def list_deviations(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db.query(Deviation).filter(Deviation.job_id == job_id).all()


@router.get("/detail/{deviation_id}", response_model=DeviationOut)
def get_deviation(
    deviation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dev = db.query(Deviation).filter(Deviation.id == deviation_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Deviation not found")
    return dev


@router.patch("/{deviation_id}", response_model=DeviationOut)
def update_deviation(
    deviation_id: int,
    payload: DeviationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("supervisor", "admin")),
):
    dev = db.query(Deviation).filter(Deviation.id == deviation_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Deviation not found")

    if payload.status is not None:
        dev.status = payload.status
    if payload.notes is not None:
        dev.notes = payload.notes

    db.commit()
    db.refresh(dev)

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="update_deviation",
        resource_type="deviation",
        resource_id=str(dev.id),
        details=f"Updated deviation status={dev.status}",
    )
    return dev


@router.post("/{deviation_id}/approve", response_model=ApprovalOut, status_code=201)
def approve_deviation(
    deviation_id: int,
    payload: ApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("supervisor", "admin")),
):
    dev = db.query(Deviation).filter(Deviation.id == deviation_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Deviation not found")

    approval = Approval(
        job_id=dev.job_id,
        deviation_id=deviation_id,
        approved_by=current_user.id,
        disposition=payload.disposition,
        notes=payload.notes,
    )
    db.add(approval)

    dev.status = payload.disposition
    db.flush()

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="approve_deviation",
        resource_type="deviation",
        resource_id=str(deviation_id),
        details=f"Disposition: {payload.disposition}",
    )

    # Check if all deviations for this job are resolved
    job = db.query(Job).filter(Job.id == dev.job_id).first()
    if job:
        open_devs = (
            db.query(Deviation)
            .filter(Deviation.job_id == job.id, Deviation.status == "open")
            .count()
        )
        if open_devs == 0:
            total_specs = (
                db.query(CriticalSpec)
                .filter(CriticalSpec.job_id == job.id, CriticalSpec.confirmed_by_user == True)
                .count()
            )
            measured = (
                db.query(MeasurementEntry)
                .filter(MeasurementEntry.job_id == job.id)
                .count()
            )
            if measured >= total_specs and total_specs > 0:
                job.status = "completed"
            else:
                job.status = "inspecting"

    db.commit()
    db.refresh(approval)
    return approval
