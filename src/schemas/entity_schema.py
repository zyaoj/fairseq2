"""Pydantic schemas for entity schema introspection API."""

from typing import Any

from pydantic import BaseModel, Field


class EnumOption(BaseModel):
    """Schema for an enum option."""

    key: str = Field(..., description="Option key/value")
    i18n_key: str = Field(..., description="Translation key for this option")


class FieldValidationSchema(BaseModel):
    """Schema for field validation rules."""

    required: bool = Field(default=False, description="Whether field is required")
    min_value: float | None = Field(default=None, description="Minimum numeric value")
    max_value: float | None = Field(default=None, description="Maximum numeric value")
    min_length: int | None = Field(default=None, description="Minimum string length")
    max_length: int | None = Field(default=None, description="Maximum string length")
    pattern: str | None = Field(default=None, description="Regex pattern for validation")


class EntityFieldSchema(BaseModel):
    """Schema for a single field in an entity."""

    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type (string, integer, float, boolean, date, enum, etc.)")
    i18n_key: str = Field(..., description="Translation key for field label")
    description: str = Field(default="", description="Field description")
    validation: FieldValidationSchema = Field(default_factory=FieldValidationSchema)
    enum_options: list[EnumOption] | None = Field(default=None, description="Options for enum fields")
    default: Any = Field(default=None, description="Default value")
    stage_specific: bool = Field(default=False, description="Whether field is stage-specific (for followups)")


class StageSchema(BaseModel):
    """Schema for a follow-up stage."""

    number: int = Field(..., description="Stage number")
    name: str = Field(..., description="Stage name (e.g., '术后7天')")
    i18n_key: str = Field(..., description="Translation key for stage name")
    days_after_surgery: int = Field(..., description="Days after surgery for this stage")


class EntitySchemaResponse(BaseModel):
    """Full entity schema response."""

    entity_type: str = Field(..., description="Entity type identifier")
    display_name_key: str = Field(..., description="Translation key for entity display name")
    description: str = Field(default="", description="Entity description")
    fields: list[EntityFieldSchema] = Field(..., description="List of entity fields")
    stages: list[StageSchema] | None = Field(default=None, description="Follow-up stages (for clinical/nursing followups)")


class EntitySchemaListItem(BaseModel):
    """Summary item for listing available schemas."""

    entity_type: str = Field(..., description="Entity type identifier")
    display_name_key: str = Field(..., description="Translation key for entity display name")
    description: str = Field(default="", description="Entity description")
    field_count: int = Field(..., description="Number of fields in this entity")
    has_stages: bool = Field(default=False, description="Whether entity has follow-up stages")


class EntitySchemaListResponse(BaseModel):
    """Response for listing all available schemas."""

    schemas: list[EntitySchemaListItem] = Field(..., description="List of available entity schemas")


class NormalizationRuleSchema(BaseModel):
    """Schema for a normalization rule."""

    type: str = Field(..., description="Normalization type (yes_no, none_has, multi_checkbox, etc.)")
    spacing: int | None = Field(default=None, description="Spacing for checkbox formats")
    format: str | None = Field(default=None, description="Format name reference")
    has_detail: bool | None = Field(default=None, description="Whether to extract detail text")


class CheckboxFormatSchema(BaseModel):
    """Schema for a checkbox format definition."""

    description: str = Field(default="", description="Format description")
    variants: list[dict[str, Any]] | None = Field(default=None, description="Format variants with spacing options")
    detection_patterns: list[str] | None = Field(default=None, description="Patterns for detecting this format")
    true_values: list[str] | None = Field(default=None, description="Values indicating true/yes")
    false_values: list[str] | None = Field(default=None, description="Values indicating false/no")


class NormalizationRulesResponse(BaseModel):
    """Response for normalization rules."""

    character_mappings: dict[str, str] = Field(default_factory=dict, description="Character normalization mappings")
    checkbox_formats: dict[str, Any] = Field(default_factory=dict, description="Checkbox format definitions")
    multi_checkbox_formats: dict[str, Any] = Field(default_factory=dict, description="Multi-checkbox format definitions")
    field_normalizations: dict[str, NormalizationRuleSchema] = Field(default_factory=dict, description="Field-specific normalization rules")
    wildcard_rules: list[dict[str, Any]] = Field(default_factory=list, description="Wildcard pattern rules")
