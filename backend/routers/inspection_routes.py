"""Inspection measurement routes with deterministic pass/fail logic."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import CriticalSpec, Deviation, Job, MeasurementEntry, User
from backend.auth import get_current_user
from backend.audit import create_audit_log
from backend.config import settings
from backend.schemas import MeasurementCreate, InspectionProgress

router = APIRouter(prefix="/api/inspection", tags=["inspection"])


@router.post("/measure", status_code=201)
def record_measurement(
    payload: MeasurementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    spec = db.query(CriticalSpec).filter(CriticalSpec.id == payload.spec_id).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not spec.confirmed_by_user:
        raise HTTPException(status_code=400, detail="Spec has not been confirmed yet")

    # Deterministic pass/fail
    passed = spec.lower_limit <= payload.actual_value <= spec.upper_limit

    measurement = MeasurementEntry(
        job_id=payload.job_id,
        spec_id=payload.spec_id,
        actual_value=payload.actual_value,
        passed=passed,
        measured_by=current_user.id,
        notes=payload.notes,
    )
    db.add(measurement)
    db.flush()

    deviation_info = None
    if not passed:
        deviation = Deviation(
            job_id=payload.job_id,
            spec_id=payload.spec_id,
            measurement_id=measurement.id,
            expected_value=spec.nominal,
            actual_value=payload.actual_value,
            status="open",
        )
        db.add(deviation)
        job.status = "deviation"
        db.flush()

        deviation_info = {
            "id": deviation.id,
            "status": deviation.status,
            "expected_value": deviation.expected_value,
            "actual_value": deviation.actual_value,
        }

        create_audit_log(
            db,
            user_id=current_user.id,
            username=current_user.username,
            action="deviation_created",
            resource_type="deviation",
            resource_id=str(deviation.id),
            details=f"Spec '{spec.characteristic}': expected {spec.nominal}, got {payload.actual_value}",
        )

    db.commit()
    db.refresh(measurement)

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="record_measurement",
        resource_type="measurement",
        resource_id=str(measurement.id),
        details=f"Spec '{spec.characteristic}': {payload.actual_value} ({'PASS' if passed else 'FAIL'})",
    )

    return {
        "id": measurement.id,
        "job_id": measurement.job_id,
        "spec_id": measurement.spec_id,
        "actual_value": measurement.actual_value,
        "passed": measurement.passed,
        "measured_by": measurement.measured_by,
        "notes": measurement.notes,
        "deviation": deviation_info,
    }


@router.delete("/measurements/{measurement_id}", status_code=200)
def delete_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a measurement (and its linked deviation) so a spec can be re-measured."""
    measurement = db.query(MeasurementEntry).filter(MeasurementEntry.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")

    # Delete linked deviations first (cascade would handle it, but be explicit)
    db.query(Deviation).filter(Deviation.measurement_id == measurement_id).delete()
    db.delete(measurement)
    db.commit()

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="delete_measurement",
        resource_type="measurement",
        resource_id=str(measurement_id),
        details=f"Deleted measurement for spec_id={measurement.spec_id} (re-entry)",
    )

    return {"detail": "Measurement deleted", "id": measurement_id}


@router.get("/{job_id}/measurements")
def get_measurements(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    measurements = db.query(MeasurementEntry).filter(MeasurementEntry.job_id == job_id).all()
    return [
        {
            "id": m.id,
            "job_id": m.job_id,
            "spec_id": m.spec_id,
            "actual_value": m.actual_value,
            "passed": m.passed,
            "measured_by": m.measured_by,
            "notes": m.notes,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
        }
        for m in measurements
    ]


@router.post("/evidence/{measurement_id}", status_code=201)
async def upload_evidence(
    measurement_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    measurement = db.query(MeasurementEntry).filter(MeasurementEntry.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")

    evidence_dir = os.path.join(settings.UPLOAD_DIR, "evidence", str(measurement.job_id))
    os.makedirs(evidence_dir, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(evidence_dir, safe_name)

    content = await file.read()
    with open(file_path, "wb") as out:
        out.write(content)

    measurement.evidence_path = file_path
    db.commit()

    return {"measurement_id": measurement_id, "evidence_path": file_path}


@router.get("/{job_id}/progress", response_model=InspectionProgress)
def get_progress(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    total_specs = (
        db.query(CriticalSpec)
        .filter(CriticalSpec.job_id == job_id, CriticalSpec.confirmed_by_user == True)
        .count()
    )

    measurements = (
        db.query(MeasurementEntry)
        .filter(MeasurementEntry.job_id == job_id)
        .all()
    )

    measured = len(measurements)
    passed_count = sum(1 for m in measurements if m.passed)
    failed_count = sum(1 for m in measurements if not m.passed)

    return {
        "job_id": job_id,
        "total_specs": total_specs,
        "measured": measured,
        "passed": passed_count,
        "failed": failed_count,
    }
