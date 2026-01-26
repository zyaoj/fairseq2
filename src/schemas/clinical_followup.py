"""Pydantic schemas for ClinicalFollowup entity."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ClinicalFollowupBase(BaseModel):
    """Base schema for ClinicalFollowup with common fields."""

    patient_name: str | None = Field(None, max_length=100)
    stage: int = Field(..., ge=1, le=5, description="Follow-up stage (1-5)")
    followup_date: date | None = None

    # Clinical findings
    followup_recurrence: str | None = Field(None, max_length=200)
    followup_stone_size: str | None = Field(None, max_length=100)
    followup_imaging: str | None = None

    # Lab values at follow-up
    followup_alt: float | None = None
    followup_ast: float | None = None
    followup_ggt: float | None = None
    followup_scr: float | None = None
    followup_wbc: float | None = None
    followup_hb: float | None = None
    followup_urine_ph: float | None = None
    followup_urine_nit: str | None = Field(None, max_length=100)
    followup_urine_wbc: str | None = Field(None, max_length=100)
    followup_urine_culture: str | None = None

    # Medication tracking
    followup_medication: str | None = Field(None, max_length=200)
    followup_medication_dose: float | None = None
    followup_medication_days: float | None = None
    followup_compliance: str | None = Field(None, max_length=100)
    followup_adverse: str | None = None
    followup_plan: str | None = None


class ClinicalFollowupCreate(ClinicalFollowupBase):
    """Schema for creating ClinicalFollowup."""

    pass


class ClinicalFollowupUpdate(BaseModel):
    """Schema for updating ClinicalFollowup (all fields optional except stage)."""

    patient_name: str | None = Field(None, max_length=100)
    followup_date: date | None = None

    # Clinical findings
    followup_recurrence: str | None = Field(None, max_length=200)
    followup_stone_size: str | None = Field(None, max_length=100)
    followup_imaging: str | None = None

    # Lab values at follow-up
    followup_alt: float | None = None
    followup_ast: float | None = None
    followup_ggt: float | None = None
    followup_scr: float | None = None
    followup_wbc: float | None = None
    followup_hb: float | None = None
    followup_urine_ph: float | None = None
    followup_urine_nit: str | None = Field(None, max_length=100)
    followup_urine_wbc: str | None = Field(None, max_length=100)
    followup_urine_culture: str | None = None

    # Medication tracking
    followup_medication: str | None = Field(None, max_length=200)
    followup_medication_dose: float | None = None
    followup_medication_days: float | None = None
    followup_compliance: str | None = Field(None, max_length=100)
    followup_adverse: str | None = None
    followup_plan: str | None = None


class ClinicalFollowupRead(ClinicalFollowupBase):
    """Schema for reading ClinicalFollowup."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    created_at: datetime
    updated_at: datetime

    # Computed properties from model
    stage_name: str = Field(..., description="Display name for the stage (e.g., '术后7天')")
    days_after_surgery: int = Field(
        ..., description="Expected days after surgery for this stage"
    )


class ClinicalFollowupList(BaseModel):
    """Schema for listing all clinical follow-ups for a patient."""

    patient_id: str
    followups: list[ClinicalFollowupRead]
    total_stages: int = 5
