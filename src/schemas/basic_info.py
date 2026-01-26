"""Pydantic schemas for BasicInfo entity."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BasicInfoBase(BaseModel):
    """Base schema for BasicInfo with common fields."""

    patient_name: str = Field(..., min_length=1, max_length=100)
    gender: str = Field(..., min_length=1, max_length=20)
    age: int = Field(..., ge=0, le=150)
    height: float | None = Field(None, ge=0, le=300)
    weight: float | None = Field(None, ge=0, le=500)
    occupation: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)

    # Lifestyle
    diet_preference: str | None = None
    likes_diet_preference: str | None = None
    dislikes_diet_preference: str | None = None
    lifestyle: str | None = None
    daily_water_intake: str | None = Field(None, max_length=100)

    # Medical history
    medical_history: str | None = None
    stone_discovery_method: str | None = Field(None, max_length=200)
    previous_urinary_infection_pathogen: str | None = None
    previous_infection_medication: str | None = None

    # Boolean flags
    family_history_of_stone: bool | None = None
    repeated_urinary_infection: bool | None = None

    # Dates
    first_urinary_infection_time: date | None = None
    surgery_date: date | None = None

    # Surgery info
    surgery_type: str | None = Field(None, max_length=200)
    stone_composition: str | None = None


class BasicInfoCreate(BasicInfoBase):
    """Schema for creating BasicInfo."""

    pass


class BasicInfoUpdate(BaseModel):
    """Schema for updating BasicInfo (all fields optional)."""

    patient_name: str | None = Field(None, min_length=1, max_length=100)
    gender: str | None = Field(None, min_length=1, max_length=20)
    age: int | None = Field(None, ge=0, le=150)
    height: float | None = Field(None, ge=0, le=300)
    weight: float | None = Field(None, ge=0, le=500)
    occupation: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)

    # Lifestyle
    diet_preference: str | None = None
    likes_diet_preference: str | None = None
    dislikes_diet_preference: str | None = None
    lifestyle: str | None = None
    daily_water_intake: str | None = Field(None, max_length=100)

    # Medical history
    medical_history: str | None = None
    stone_discovery_method: str | None = Field(None, max_length=200)
    previous_urinary_infection_pathogen: str | None = None
    previous_infection_medication: str | None = None

    # Boolean flags
    family_history_of_stone: bool | None = None
    repeated_urinary_infection: bool | None = None

    # Dates
    first_urinary_infection_time: date | None = None
    surgery_date: date | None = None

    # Surgery info
    surgery_type: str | None = Field(None, max_length=200)
    stone_composition: str | None = None


class BasicInfoRead(BasicInfoBase):
    """Schema for reading BasicInfo."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    created_at: datetime
    updated_at: datetime
