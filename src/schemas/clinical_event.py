"""Clinical event Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.models.clinical_event import ExtractionStatus, LifecyclePhase


class ClinicalEventBase(BaseModel):
    """Base clinical event schema."""

    patient_id: str
    phase: LifecyclePhase
    event_type: str = Field(..., min_length=1, max_length=50)
    event_date: datetime
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ClinicalEventCreate(ClinicalEventBase):
    """Schema for creating a clinical event."""

    pass


class ClinicalEventRead(ClinicalEventBase):
    """Schema for reading clinical event data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    uploaded_by: str | None = None
    type: str
    created_at: datetime
    updated_at: datetime


class LabResultBase(BaseModel):
    """Base lab result schema."""

    original_file_path: str = Field(..., max_length=500)
    file_type: str = Field(..., max_length=50)  # image, pdf


class LabResultCreate(ClinicalEventBase, LabResultBase):
    """Schema for creating a lab result."""

    pass


class LabResultRead(ClinicalEventRead, LabResultBase):
    """Schema for reading lab result data."""

    model_config = ConfigDict(from_attributes=True)

    extraction_status: ExtractionStatus
    extracted_data: dict[str, Any] | None = None
    extraction_confidence: float | None = None
    vector_embedding_id: str | None = None


class ExtractionStatusResponse(BaseModel):
    """Lightweight schema for extraction status polling."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    extraction_status: ExtractionStatus
    extraction_confidence: float | None = None
    has_extracted_data: bool = False
    error_message: str | None = None


class LabResultExtractedData(BaseModel):
    """Schema for extracted lab result data."""

    test_name: str
    value: float | str
    unit: str | None = None
    reference_range: str | None = None
    is_abnormal: bool | None = None
    notes: str | None = None


class PatientTimeline(BaseModel):
    """Schema for patient timeline with events grouped by phase."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    events: list[ClinicalEventRead]
    events_by_phase: dict[str, list[ClinicalEventRead]]
