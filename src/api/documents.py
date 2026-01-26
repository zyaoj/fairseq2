"""Document processing API endpoints.

This module provides endpoints for:
- Generating Word documents from patient data
- Parsing Word documents to extract structured data
- Listing and downloading templates
"""

import logging
from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.api.deps import get_current_active_user, get_db
from src.models.patient import Patient
from src.models.user import User
from src.schemas.document import (
    DocumentGenerateResponse,
    DocumentParseResponse,
    TemplateInfo,
    TemplateListResponse,
)
from src.services.template_service import TemplateNotFoundError, get_template_service
from src.services.word_extractor import WordExtractorError, get_word_extractor_service
from src.services.word_generator import WordGeneratorError, get_word_generator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Maximum file size for document uploads: 20 MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024

# Allowed MIME types for Word documents
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def get_patient_with_hospital_check(
    patient_id: str,
    db: Session,
    current_user: User,
) -> Patient:
    """Get patient with hospital/tenant scoping.

    Verifies that the patient belongs to the same hospital as the current user.
    This prevents cross-tenant data access.

    Args:
        patient_id: Patient UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        The patient if found and accessible

    Raises:
        HTTPException: If patient not found or user lacks access
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Check hospital scoping (skip if user has no hospital_id - e.g., admin)
    if current_user.hospital_id and patient.hospital_id:
        if patient.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

    return patient


@router.post(
    "/generate/{patient_id}",
    response_model=DocumentGenerateResponse,
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}},
            "description": "Generated Word document",
        },
        404: {"description": "Patient not found"},
        500: {"description": "Document generation failed"},
    },
)
async def generate_document(
    patient_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    include_sections: list[str] | None = None,
) -> StreamingResponse:
    """Generate a Word document for a patient.

    Uses the hospital-specific template if available, otherwise falls back to base template.
    The hospital_id is resolved from the current user's profile.

    Args:
        patient_id: UUID of the patient
        current_user: Current authenticated user
        db: Database session
        include_sections: Optional list of sections to include

    Returns:
        StreamingResponse with the generated Word document
    """
    # Get the patient with hospital scoping (prevents cross-tenant access)
    patient = get_patient_with_hospital_check(
        patient_id=str(patient_id),
        db=db,
        current_user=current_user,
    )

    try:
        # Get hospital-aware word generator
        generator = get_word_generator_service(hospital_id=current_user.hospital_id)

        # Generate the document
        doc_bytes = generator.generate_followup_registration(
            patient=patient,
            include_sections=include_sections,
        )

        # Create filename with patient info
        patient_name = ""
        if patient.basic_info:
            patient_name = patient.basic_info.patient_name or ""
        filename = f"followup_registration_{patient_name or patient_id}.docx"

        return StreamingResponse(
            doc_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except WordGeneratorError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate document: {str(e)}",
        )


@router.post(
    "/parse",
    response_model=DocumentParseResponse,
    responses={
        400: {"description": "Invalid file format or size"},
        413: {"description": "File too large"},
        500: {"description": "Document parsing failed"},
    },
)
async def parse_document(
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: Annotated[UploadFile, File(description="Word document to parse")],
    sections: list[str] | None = None,
    use_llm: bool = True,
) -> DocumentParseResponse:
    """Parse a Word document and extract structured data.

    Uses hospital-specific normalization rules if available.
    If use_llm is True and ANTHROPIC_API_KEY is configured, uses Claude for extraction.
    Otherwise, falls back to pattern-based extraction.

    Args:
        current_user: Current authenticated user
        file: Uploaded Word document
        sections: Optional list of sections to extract
        use_llm: Whether to use LLM for extraction (default True)

    Returns:
        Extracted structured data by entity type
    """
    # Validate file extension
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx files are supported",
        )

    # Validate MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(
            "Rejected file upload with invalid content type: %s", file.content_type
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type. Expected Word document, got: {file.content_type}",
        )

    try:
        # Read file with streaming size check to prevent memory exhaustion
        chunks = []
        total_size = 0
        chunk_size = 64 * 1024  # 64KB chunks

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_DOCUMENT_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size is {MAX_DOCUMENT_SIZE // (1024 * 1024)} MB",
                )
            chunks.append(chunk)

        content = b"".join(chunks)

        # Get Anthropic client if LLM extraction is requested
        anthropic_client = None
        if use_llm:
            try:
                import anthropic
                anthropic_client = anthropic.Anthropic()
            except Exception:
                # Fall back to pattern-based extraction if Anthropic is not configured
                pass

        # Get hospital-aware extractor
        extractor = get_word_extractor_service(
            hospital_id=current_user.hospital_id,
            anthropic_client=anthropic_client,
        )

        # Extract data
        extracted_data = extractor.extract_from_bytes(
            content=content,
            sections=sections,
        )

        return DocumentParseResponse(extracted_data=extracted_data)

    except WordExtractorError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse document: {str(e)}",
        )


@router.get(
    "/templates",
    response_model=TemplateListResponse,
)
async def list_templates(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TemplateListResponse:
    """List available Word templates.

    Returns templates available for the current user's hospital.
    Hospital-specific templates take precedence over base templates.

    Args:
        current_user: Current authenticated user

    Returns:
        List of available templates with their sources
    """
    template_service = get_template_service()

    templates_raw = template_service.list_available_templates(
        hospital_id=current_user.hospital_id
    )

    templates = [
        TemplateInfo(
            name=t["name"],
            source=t["source"],
            path=t["path"],
        )
        for t in templates_raw
    ]

    return TemplateListResponse(
        templates=templates,
        hospital_id=current_user.hospital_id,
    )


@router.get(
    "/templates/{template_name}/download",
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}},
            "description": "Template Word document",
        },
        404: {"description": "Template not found"},
    },
)
async def download_template(
    template_name: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> StreamingResponse:
    """Download a Word template.

    Returns the hospital-specific template if available, otherwise the base template.

    Args:
        template_name: Name of the template (without .docx extension)
        current_user: Current authenticated user

    Returns:
        StreamingResponse with the template file
    """
    template_service = get_template_service()

    try:
        template_path = template_service.get_template_path(
            template_name=template_name,
            hospital_id=current_user.hospital_id,
        )

        # Read the template file
        with open(template_path, "rb") as f:
            content = f.read()

        filename = f"{template_name}.docx"

        return StreamingResponse(
            BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found",
        )
