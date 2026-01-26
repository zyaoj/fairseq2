"""Pydantic schemas for SurgeryIndicator entity."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SurgeryIndicatorBase(BaseModel):
    """Base schema for SurgeryIndicator with common fields."""

    patient_name: str | None = Field(None, max_length=100)

    # Clinical info
    clinical_diagnosis: str | None = None
    stone_location: list[str] | None = None  # multi_enum: left_kidney, right_kidney, etc.
    stone_size: str | None = Field(None, max_length=100)
    hydronephrosis_degree: str | None = Field(
        None, max_length=50
    )  # none, mild, moderate, severe

    # Pre-operative lab values (术前)
    alt_value_before: float | None = None
    ast_value_before: float | None = None
    ggt_value_before: float | None = None
    scr_value_before: float | None = None
    wbc_value_before: float | None = None
    hb_value_before: float | None = None
    urine_ph_value_before: float | None = None
    urine_nit_value_before: str | None = Field(None, max_length=100)
    urine_wbc_value_before: str | None = Field(None, max_length=100)
    urine_culture_result_before: str | None = None
    urine_ngs_result_before: str | None = None

    # Post-operative lab values (术后)
    alt_value_after: float | None = None
    ast_value_after: float | None = None
    ggt_value_after: float | None = None
    scr_value_after: float | None = None
    wbc_value_after: float | None = None
    hb_value_after: float | None = None
    urine_ph_value_after: float | None = None
    urine_nit_value_after: str | None = Field(None, max_length=100)
    urine_wbc_value_after: str | None = Field(None, max_length=100)
    urine_culture_result_after: str | None = None
    urine_ngs_result_after: str | None = None

    # Post-op stone analysis
    stone_culture_result_after: str | None = None
    stone_ngs_result_after: str | None = None
    stone_composition_after: list[str] | None = None
    stone_clearance_after: str | None = Field(None, max_length=100)
    imaging_method_after: str | None = Field(None, max_length=200)


class SurgeryIndicatorCreate(SurgeryIndicatorBase):
    """Schema for creating SurgeryIndicator."""

    pass


class SurgeryIndicatorUpdate(SurgeryIndicatorBase):
    """Schema for updating SurgeryIndicator (all fields already optional)."""

    pass


class SurgeryIndicatorRead(SurgeryIndicatorBase):
    """Schema for reading SurgeryIndicator."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    created_at: datetime
    updated_at: datetime
