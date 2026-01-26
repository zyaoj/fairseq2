"""Pydantic schemas for NursingFollowup entity."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class NursingFollowupBase(BaseModel):
    """Base schema for NursingFollowup with common fields."""

    patient_name: str | None = Field(None, max_length=100)
    stage: int = Field(..., ge=1, le=6, description="Follow-up stage (1-6)")
    followup_date: date | None = None

    # Follow-up mode
    nursing_mode: str | None = Field(None, max_length=50)  # phone, video, home_visit

    # Medication info
    nursing_discharge_drug: str | None = None
    nursing_antibiotic: str | None = Field(None, max_length=200)
    nursing_antibiotic_dose: str | None = Field(None, max_length=100)
    nursing_other_drug: str | None = Field(None, max_length=200)
    nursing_other_drug_dose: str | None = Field(None, max_length=100)
    nursing_timed_med: bool | None = None

    # Urine monitoring
    nursing_urine_ph: float | None = None
    nursing_urine_output: bool | None = None  # >2L
    nursing_urine_color: int | None = Field(None, ge=0, le=8)  # 0-8 scale

    # Adverse effects and conditions
    nursing_adverse_effects: str | None = None
    nursing_acidosis: bool | None = None
    nursing_hco3: float | None = None

    # Location and stone tracking
    nursing_followup_location: str | None = Field(None, max_length=200)
    nursing_residual_stone: str | None = Field(None, max_length=200)

    # Lifestyle
    nursing_water: str | None = Field(None, max_length=200)
    nursing_diet: str | None = None

    # Mental health
    nursing_psqi: str | None = Field(None, max_length=100)
    nursing_psqi_drug: str | None = Field(None, max_length=200)
    nursing_depression: str | None = Field(None, max_length=100)
    nursing_depression_anxiety: str | None = Field(None, max_length=200)
    nursing_support: str | None = None


class NursingFollowupCreate(NursingFollowupBase):
    """Schema for creating NursingFollowup."""

    pass


class NursingFollowupUpdate(BaseModel):
    """Schema for updating NursingFollowup (all fields optional except stage)."""

    patient_name: str | None = Field(None, max_length=100)
    followup_date: date | None = None

    # Follow-up mode
    nursing_mode: str | None = Field(None, max_length=50)

    # Medication info
    nursing_discharge_drug: str | None = None
    nursing_antibiotic: str | None = Field(None, max_length=200)
    nursing_antibiotic_dose: str | None = Field(None, max_length=100)
    nursing_other_drug: str | None = Field(None, max_length=200)
    nursing_other_drug_dose: str | None = Field(None, max_length=100)
    nursing_timed_med: bool | None = None

    # Urine monitoring
    nursing_urine_ph: float | None = None
    nursing_urine_output: bool | None = None
    nursing_urine_color: int | None = Field(None, ge=0, le=8)

    # Adverse effects and conditions
    nursing_adverse_effects: str | None = None
    nursing_acidosis: bool | None = None
    nursing_hco3: float | None = None

    # Location and stone tracking
    nursing_followup_location: str | None = Field(None, max_length=200)
    nursing_residual_stone: str | None = Field(None, max_length=200)

    # Lifestyle
    nursing_water: str | None = Field(None, max_length=200)
    nursing_diet: str | None = None

    # Mental health
    nursing_psqi: str | None = Field(None, max_length=100)
    nursing_psqi_drug: str | None = Field(None, max_length=200)
    nursing_depression: str | None = Field(None, max_length=100)
    nursing_depression_anxiety: str | None = Field(None, max_length=200)
    nursing_support: str | None = None


class NursingFollowupRead(NursingFollowupBase):
    """Schema for reading NursingFollowup."""

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


class NursingFollowupList(BaseModel):
    """Schema for listing all nursing follow-ups for a patient."""

    patient_id: str
    followups: list[NursingFollowupRead]
    total_stages: int = 6
