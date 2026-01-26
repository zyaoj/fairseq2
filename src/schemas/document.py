"""Document processing Pydantic schemas."""

from typing import Any

from pydantic import BaseModel, Field


class DocumentGenerateRequest(BaseModel):
    """Schema for generating a Word document."""

    patient_id: str = Field(..., description="Patient ID to generate document for")
    include_sections: list[str] | None = Field(
        None,
        description="Sections to include. Options: basic_info, surgery_indicator, "
        "clinical_followups, nursing_followups. If None, includes all.",
    )


class DocumentGenerateResponse(BaseModel):
    """Schema for document generation response."""

    message: str
    filename: str


class DocumentParseRequest(BaseModel):
    """Schema for parsing a Word document."""

    sections: list[str] | None = Field(
        None,
        description="Sections to extract. Options: basic_info, surgery_indicator, "
        "clinical_followup, nursing_followup. If None, extracts all.",
    )


class DocumentParseResponse(BaseModel):
    """Schema for document parsing response."""

    extracted_data: dict[str, Any] = Field(
        ..., description="Extracted structured data by entity type"
    )


class TemplateInfo(BaseModel):
    """Schema for template information."""

    name: str = Field(..., description="Template name (without extension)")
    source: str = Field(..., description="Template source: 'base' or 'hospital'")
    path: str = Field(..., description="Relative path to template file")


class TemplateListResponse(BaseModel):
    """Schema for listing available templates."""

    templates: list[TemplateInfo]
    hospital_id: str | None = Field(
        None, description="Hospital ID used for resolution"
    )
