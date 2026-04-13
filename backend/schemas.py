"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# -- Enums -----------------------------------------------------------------

class RoleEnum(str, Enum):
    operator = "operator"
    supervisor = "supervisor"
    admin = "admin"

class JobStatusEnum(str, Enum):
    created = "created"
    extracting = "extracting"
    review = "review"
    inspecting = "inspecting"
    completed = "completed"
    deviation = "deviation"

class SensitivityEnum(str, Enum):
    general = "general"
    confidential = "confidential"
    highly_confidential = "highly_confidential"


# -- User ------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: RoleEnum = RoleEnum.operator

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Alias
UserResponse = UserOut

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -- Job -------------------------------------------------------------------

class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    sensitivity_label: SensitivityEnum = SensitivityEnum.general

class JobStatusUpdate(BaseModel):
    status: str

class JobOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    sensitivity_label: str
    created_by: int
    assigned_supervisor: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

JobResponse = JobOut


# -- Document --------------------------------------------------------------

class DocumentOut(BaseModel):
    id: int
    job_id: int
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    upload_time: datetime
    uploaded_by: int
    model_config = ConfigDict(from_attributes=True)

DocumentResponse = DocumentOut


# -- CriticalSpec ----------------------------------------------------------

class CriticalSpecCreate(BaseModel):
    characteristic: str = Field(..., max_length=200)
    nominal: float
    lower_limit: float
    upper_limit: float
    unit: Optional[str] = "mm"
    tool_required: Optional[str] = None
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None
    confidence: Optional[float] = None

class CriticalSpecOut(BaseModel):
    id: int
    job_id: int
    characteristic: str
    nominal: float
    lower_limit: float
    upper_limit: float
    unit: Optional[str] = None
    tool_required: Optional[str] = None
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None
    confirmed_by_user: bool = False
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

CriticalSpecResponse = CriticalSpecOut


# -- InspectionStep --------------------------------------------------------

class InspectionStepCreate(BaseModel):
    step_number: int
    title: Optional[str] = None
    description: Optional[str] = None
    instruction_text: Optional[str] = None
    related_spec_ids: Optional[str] = None
    spec_characteristic: Optional[str] = None
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None

class InspectionStepOut(BaseModel):
    id: int
    job_id: int
    step_number: int
    title: Optional[str] = None
    description: Optional[str] = None
    instruction_text: Optional[str] = None
    related_spec_ids: Optional[str] = None
    spec_characteristic: Optional[str] = None
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

InspectionStepResponse = InspectionStepOut


# -- Measurement -----------------------------------------------------------

class MeasurementCreate(BaseModel):
    job_id: int
    spec_id: int
    actual_value: float
    notes: Optional[str] = None

class MeasurementOut(BaseModel):
    id: int
    job_id: int
    spec_id: int
    actual_value: float
    passed: bool
    measured_by: int
    notes: Optional[str] = None
    timestamp: Optional[datetime] = None
    evidence_path: Optional[str] = None
    deviation: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)

MeasurementResponse = MeasurementOut


# -- Deviation -------------------------------------------------------------

class DeviationUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[str] = None

class DeviationOut(BaseModel):
    id: int
    job_id: int
    measurement_id: int
    spec_id: int
    expected_value: float
    actual_value: float
    notes: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

DeviationResponse = DeviationOut


# -- Approval --------------------------------------------------------------

class ApprovalCreate(BaseModel):
    disposition: str  # approved / rejected / conditional
    notes: Optional[str] = None

class ApprovalOut(BaseModel):
    id: int
    job_id: int
    deviation_id: Optional[int] = None
    approved_by: int
    disposition: str
    notes: Optional[str] = None
    timestamp: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

ApprovalResponse = ApprovalOut


# -- AuditLog --------------------------------------------------------------

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: Optional[datetime] = None
    ip_address: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

AuditLogResponse = AuditLogOut


# -- Report ----------------------------------------------------------------

class ReportBundleOut(BaseModel):
    id: int
    job_id: int
    generated_by: int
    pdf_path: str
    json_path: str
    generated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

ReportResponse = ReportBundleOut


# -- Progress --------------------------------------------------------------

class InspectionProgress(BaseModel):
    job_id: int
    total_specs: int
    measured: int
    passed: int
    failed: int
