"""Patient Pydantic schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    """Base patient schema with common fields."""

    mrn: str = Field(..., min_length=1, max_length=50, description="Medical Record Number")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: str = Field(..., min_length=1, max_length=20)
    hospital_id: str | None = Field(None, max_length=50)


class PatientCreate(PatientBase):
    """Schema for creating a new patient."""

    pass


class PatientUpdate(BaseModel):
    """Schema for updating an existing patient."""

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(None, min_length=1, max_length=20)
    hospital_id: str | None = Field(None, max_length=50)


class PatientRead(PatientBase):
    """Schema for reading patient data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class PatientSummary(BaseModel):
    """Schema for patient with LLM-generated summary."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    mrn: str
    first_name: str
    last_name: str
    summary: str = Field(..., description="LLM-generated patient summary")
