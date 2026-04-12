"""
SQLAlchemy ORM models for TracePilot.
Covers users, jobs, documents, specs, inspections, measurements,
deviations, approvals, audit logs, and report bundles.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="operator")
    created_at = Column(DateTime, default=_utcnow)

    jobs_created = relationship("Job", foreign_keys="Job.created_by", back_populates="creator")
    documents = relationship("Document", back_populates="uploader")
    measurements = relationship("MeasurementEntry", back_populates="measured_by_user")
    approvals = relationship("Approval", back_populates="approver")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="created")
    sensitivity_label = Column(String(30), nullable=False, default="general")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_supervisor = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    creator = relationship("User", foreign_keys=[created_by], back_populates="jobs_created")
    supervisor = relationship("User", foreign_keys=[assigned_supervisor])
    documents = relationship("Document", back_populates="job", cascade="all, delete-orphan")
    specs = relationship("CriticalSpec", back_populates="job", cascade="all, delete-orphan")
    steps = relationship("InspectionStep", back_populates="job", cascade="all, delete-orphan")
    measurements = relationship("MeasurementEntry", back_populates="job", cascade="all, delete-orphan")
    deviations = relationship("Deviation", back_populates="job", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="job", cascade="all, delete-orphan")
    reports = relationship("ReportBundle", back_populates="job", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    filename = Column(String(255), nullable=False)       # stored name on disk
    original_filename = Column(String(255), nullable=False)  # user's original name
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_time = Column(DateTime, default=_utcnow)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    job = relationship("Job", back_populates="documents")
    uploader = relationship("User", back_populates="documents")


class CriticalSpec(Base):
    __tablename__ = "critical_specs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    characteristic = Column(String(200), nullable=False)  # feature/dimension name
    nominal = Column(Float, nullable=False)
    lower_limit = Column(Float, nullable=False)
    upper_limit = Column(Float, nullable=False)
    unit = Column(String(30), nullable=True, default="mm")
    tool_required = Column(String(100), nullable=True)
    source_document = Column(String(255), nullable=True)
    source_page = Column(Integer, nullable=True)
    source_snippet = Column(Text, nullable=True)
    confirmed_by_user = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    job = relationship("Job", back_populates="specs")
    measurements = relationship("MeasurementEntry", back_populates="spec", cascade="all, delete-orphan")
    deviations = relationship("Deviation", back_populates="spec", cascade="all, delete-orphan")


class InspectionStep(Base):
    __tablename__ = "inspection_steps"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    instruction_text = Column(Text, nullable=True)
    related_spec_ids = Column(String(500), nullable=True)  # JSON list as string
    spec_characteristic = Column(String(200), nullable=True)
    source_document = Column(String(255), nullable=True)
    source_page = Column(Integer, nullable=True)
    source_snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    job = relationship("Job", back_populates="steps")


class MeasurementEntry(Base):
    __tablename__ = "measurement_entries"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    spec_id = Column(Integer, ForeignKey("critical_specs.id"), nullable=False)
    actual_value = Column(Float, nullable=False)
    passed = Column(Boolean, nullable=False, default=False)
    measured_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)
    evidence_path = Column(String(500), nullable=True)

    job = relationship("Job", back_populates="measurements")
    spec = relationship("CriticalSpec", back_populates="measurements")
    measured_by_user = relationship("User", back_populates="measurements")
    deviations = relationship("Deviation", back_populates="measurement", cascade="all, delete-orphan")


class Deviation(Base):
    __tablename__ = "deviations"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    measurement_id = Column(Integer, ForeignKey("measurement_entries.id"), nullable=False)
    spec_id = Column(Integer, ForeignKey("critical_specs.id"), nullable=False)
    expected_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="open")
    created_at = Column(DateTime, default=_utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    job = relationship("Job", back_populates="deviations")
    measurement = relationship("MeasurementEntry", back_populates="deviations")
    spec = relationship("CriticalSpec", back_populates="deviations")
    resolver = relationship("User", foreign_keys=[resolved_by])
    approvals = relationship("Approval", back_populates="deviation", cascade="all, delete-orphan")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    deviation_id = Column(Integer, ForeignKey("deviations.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    disposition = Column(String(30), nullable=False)  # approved / rejected / conditional
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)

    job = relationship("Job", back_populates="approvals")
    deviation = relationship("Deviation", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50), nullable=False, default="system")
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)
    ip_address = Column(String(45), nullable=True)


class ReportBundle(Base):
    __tablename__ = "report_bundles"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    pdf_path = Column(String(500), nullable=False)
    json_path = Column(String(500), nullable=False)
    generated_at = Column(DateTime, default=_utcnow)

    job = relationship("Job", back_populates="reports")
    generator = relationship("User", foreign_keys=[generated_by])
