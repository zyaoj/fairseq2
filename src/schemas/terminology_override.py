"""Pydantic schemas for TerminologyOverride entity."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ScopeType(str, Enum):
    """Scope type for terminology overrides."""

    USER = "user"
    HOSPITAL = "hospital"


class TerminologyOverrideBase(BaseModel):
    """Base schema for TerminologyOverride with common fields."""

    scope_type: ScopeType = Field(..., description="Scope type: 'user' or 'hospital'")
    scope_id: str = Field(..., description="User ID or Hospital ID")
    term_key: str = Field(
        ..., min_length=1, max_length=255, description="Term key, e.g., 'stone_location.left_kidney'"
    )
    locale: str = Field(default="zh-CN", max_length=10, description="Locale code, e.g., 'zh-CN'")
    display_value: str = Field(..., min_length=1, description="Custom display text")


class TerminologyOverrideCreate(TerminologyOverrideBase):
    """Schema for creating TerminologyOverride."""

    pass


class TerminologyOverrideUpdate(BaseModel):
    """Schema for updating TerminologyOverride (only display_value can be updated)."""

    display_value: str = Field(..., min_length=1, description="Custom display text")


class TerminologyOverrideRead(TerminologyOverrideBase):
    """Schema for reading TerminologyOverride."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class TerminologyResolution(BaseModel):
    """Schema for resolved terminology with hierarchy information."""

    term_key: str
    locale: str
    display_value: str
    source: str = Field(
        ..., description="Source of resolution: 'user', 'hospital', or 'base'"
    )


class TerminologyBulkRequest(BaseModel):
    """Schema for requesting multiple terminology resolutions."""

    term_keys: list[str] = Field(..., min_length=1, description="List of term keys to resolve")
    locale: str = Field(default="zh-CN", max_length=10)


class TerminologyBulkResponse(BaseModel):
    """Schema for bulk terminology resolution response."""

    resolutions: dict[str, TerminologyResolution] = Field(
        ..., description="Map of term_key to resolved terminology"
    )
