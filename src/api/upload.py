"""Lab result upload API router."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_active_user
from src.core.database import get_db
from src.models.clinical_event import ExtractionStatus, LabResult, LifecyclePhase
from src.models.patient import Patient
from src.models.user import User
from src.schemas.clinical_event import ExtractionStatusResponse, LabResultRead
from src.services.storage import StorageService, get_storage_service
from src.workers.extraction_task import create_extraction_background_task

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

# Maximum file size: 50 MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif"}


def validate_file_extension(filename: str) -> str:
    """Validate file extension and return it.

    Args:
        filename: Original filename

    Returns:
        Lowercase file extension

    Raises:
        HTTPException: If file extension is not allowed
    """
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


def get_lab_result_with_hospital_check(
    lab_result_id: str,
    db: Session,
    current_user: User,
) -> LabResult:
    """Get lab result with hospital/tenant scoping.

    Verifies that the lab result belongs to a patient in the same hospital
    as the current user. This prevents cross-tenant data access.

    Args:
        lab_result_id: Lab result UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        The lab result if found and accessible

    Raises:
        HTTPException: If lab result not found or user lacks access
    """
    # Join through Patient to verify hospital access
    lab_result = (
        db.query(LabResult)
        .join(Patient, LabResult.patient_id == Patient.id)
        .filter(LabResult.id == lab_result_id)
        .first()
    )

    if not lab_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab result not found",
        )

    # Verify hospital access - get the patient to check hospital_id
    patient = db.query(Patient).filter(Patient.id == lab_result.patient_id).first()

    # Check hospital scoping (skip if user has no hospital_id - e.g., admin)
    if current_user.hospital_id and patient and patient.hospital_id:
        if patient.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab result not found",
            )

    return lab_result


@router.post("/lab-result", response_model=LabResultRead, status_code=status.HTTP_201_CREATED)
async def upload_lab_result(
    file: Annotated[UploadFile, File(description="Lab result file (PDF or image)")],
    patient_id: Annotated[str, Form(description="Patient UUID")],
    title: Annotated[str, Form(description="Title for the lab result")],
    phase: Annotated[LifecyclePhase, Form(description="Lifecycle phase")],
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    description: Annotated[str | None, Form(description="Optional description")] = None,
    event_date: Annotated[datetime | None, Form(description="Event date (defaults to now)")] = None,
) -> LabResult:
    """Upload a lab result file for a patient.

    The file will be stored in MinIO and a LabResult record will be created
    with extraction_status=PENDING. A background task will process the file
    for data extraction.

    Args:
        file: The lab result file (PDF or image)
        patient_id: Patient UUID
        title: Title for the lab result
        phase: Lifecycle phase (e.g., PRE_SURGERY, POST_SURGERY)
        db: Database session
        current_user: Current authenticated user
        storage_service: Storage service for file operations
        description: Optional description
        event_date: Optional event date (defaults to now)

    Returns:
        The created LabResult record

    Raises:
        HTTPException: If patient not found or file type not allowed
    """
    # Validate patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Verify hospital scoping - user can only upload for patients in their hospital
    if current_user.hospital_id and patient.hospital_id:
        if patient.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

    # Validate filename exists
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Validate file extension
    ext = validate_file_extension(file.filename)

    # Check Content-Length header first if available (early rejection)
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # Read file content in chunks to avoid memory exhaustion
    # and validate size during streaming
    chunks = []
    total_size = 0
    chunk_size = 1024 * 1024  # 1 MB chunks

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB",
            )
        chunks.append(chunk)

    content = b"".join(chunks)

    # Upload to storage
    object_key = storage_service.upload_file(
        file_content=content,
        original_filename=file.filename,
        folder="lab-results",
    )

    # Detect file type category
    file_type = storage_service.detect_file_type(file.filename)

    # Create lab result record
    lab_result = LabResult(
        patient_id=patient_id,
        phase=phase,
        event_type="lab_result",
        event_date=event_date or datetime.now(timezone.utc),
        title=title,
        description=description,
        uploaded_by=current_user.id,
        original_file_path=object_key,
        file_type=file_type,
        extraction_status=ExtractionStatus.PENDING,
    )

    db.add(lab_result)
    db.commit()
    db.refresh(lab_result)

    # Dispatch background task for extraction
    task = create_extraction_background_task(
        lab_result_id=str(lab_result.id),
        hospital_id=current_user.hospital_id,
    )
    background_tasks.add_task(task)

    return lab_result


@router.get("/lab-result/{lab_result_id}", response_model=LabResultRead)
def get_lab_result(
    lab_result_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> LabResult:
    """Get a lab result by ID.

    Args:
        lab_result_id: Lab result UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        The lab result

    Raises:
        HTTPException: If lab result not found or user lacks access
    """
    return get_lab_result_with_hospital_check(lab_result_id, db, current_user)


@router.get("/lab-result/{lab_result_id}/download-url")
def get_lab_result_download_url(
    lab_result_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    expires_hours: int = 1,
) -> dict[str, str]:
    """Get a presigned download URL for a lab result file.

    Args:
        lab_result_id: Lab result UUID
        db: Database session
        current_user: Current authenticated user
        storage_service: Storage service for file operations
        expires_hours: Hours until URL expires (default: 1)

    Returns:
        Dictionary with presigned URL

    Raises:
        HTTPException: If lab result not found or user lacks access
    """
    lab_result = get_lab_result_with_hospital_check(lab_result_id, db, current_user)

    url = storage_service.get_presigned_url(
        object_key=lab_result.original_file_path,
        expires_hours=expires_hours,
    )

    return {"download_url": url}


@router.post("/lab-result/{lab_result_id}/reprocess", response_model=LabResultRead)
def reprocess_lab_result(
    lab_result_id: str,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> LabResult:
    """Reprocess a lab result for data extraction.

    This will reset the extraction status to PENDING and trigger
    a new extraction attempt.

    Args:
        lab_result_id: Lab result UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        The updated lab result

    Raises:
        HTTPException: If lab result not found or user lacks access
    """
    lab_result = get_lab_result_with_hospital_check(lab_result_id, db, current_user)

    # Reset extraction status
    lab_result.extraction_status = ExtractionStatus.PENDING
    lab_result.extracted_data = None
    lab_result.extraction_confidence = None

    db.commit()
    db.refresh(lab_result)

    # Dispatch background task for extraction
    task = create_extraction_background_task(
        lab_result_id=str(lab_result.id),
        hospital_id=current_user.hospital_id,
    )
    background_tasks.add_task(task)

    return lab_result


@router.get("/lab-result/{lab_result_id}/status", response_model=ExtractionStatusResponse)
def get_lab_result_status(
    lab_result_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Get extraction status for a lab result (lightweight endpoint for polling).

    This endpoint returns only the extraction status fields, making it
    efficient for polling during background extraction processing.

    Args:
        lab_result_id: Lab result UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Extraction status information

    Raises:
        HTTPException: If lab result not found or user lacks access
    """
    lab_result = get_lab_result_with_hospital_check(lab_result_id, db, current_user)

    # Extract error message if extraction failed
    error_message = None
    if lab_result.extraction_status == ExtractionStatus.FAILED and lab_result.extracted_data:
        error_message = lab_result.extracted_data.get("error")

    return {
        "id": str(lab_result.id),
        "extraction_status": lab_result.extraction_status,
        "extraction_confidence": lab_result.extraction_confidence,
        "has_extracted_data": lab_result.extracted_data is not None
        and lab_result.extraction_status == ExtractionStatus.COMPLETED,
        "error_message": error_message,
    }


@router.get("/lab-results/pending", response_model=list[ExtractionStatusResponse])
def list_pending_lab_results(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = 50,
) -> list[dict]:
    """List lab results with pending or processing extraction status.

    Results are filtered by hospital/tenant scoping based on the current user.

    Args:
        db: Database session
        current_user: Current authenticated user
        limit: Maximum number of results (default: 50)

    Returns:
        List of lab results with pending/processing extraction
    """
    # Build query with hospital scoping via JOIN through Patient
    query = (
        db.query(LabResult)
        .join(Patient, LabResult.patient_id == Patient.id)
        .filter(
            LabResult.extraction_status.in_(
                [ExtractionStatus.PENDING, ExtractionStatus.PROCESSING]
            )
        )
    )

    # Apply hospital filter if user has hospital_id (non-admin)
    if current_user.hospital_id:
        query = query.filter(Patient.hospital_id == current_user.hospital_id)

    lab_results = query.order_by(LabResult.created_at.desc()).limit(limit).all()

    return [
        {
            "id": str(lr.id),
            "extraction_status": lr.extraction_status,
            "extraction_confidence": lr.extraction_confidence,
            "has_extracted_data": False,
            "error_message": None,
        }
        for lr in lab_results
    ]


@router.get("/lab-results/failed", response_model=list[ExtractionStatusResponse])
def list_failed_lab_results(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = 50,
) -> list[dict]:
    """List lab results with failed extraction status.

    Results are filtered by hospital/tenant scoping based on the current user.

    Args:
        db: Database session
        current_user: Current authenticated user
        limit: Maximum number of results (default: 50)

    Returns:
        List of lab results with failed extraction
    """
    # Build query with hospital scoping via JOIN through Patient
    query = (
        db.query(LabResult)
        .join(Patient, LabResult.patient_id == Patient.id)
        .filter(LabResult.extraction_status == ExtractionStatus.FAILED)
    )

    # Apply hospital filter if user has hospital_id (non-admin)
    if current_user.hospital_id:
        query = query.filter(Patient.hospital_id == current_user.hospital_id)

    lab_results = query.order_by(LabResult.created_at.desc()).limit(limit).all()

    return [
        {
            "id": str(lr.id),
            "extraction_status": lr.extraction_status,
            "extraction_confidence": lr.extraction_confidence,
            "has_extracted_data": False,
            "error_message": lr.extracted_data.get("error") if lr.extracted_data else None,
        }
        for lr in lab_results
    ]


@router.delete("/lab-result/{lab_result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lab_result(
    lab_result_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> None:
    """Delete a lab result and its associated file.

    Verifies hospital/tenant scoping before deletion.

    Args:
        lab_result_id: Lab result UUID
        db: Database session
        current_user: Current authenticated user
        storage_service: Storage service for file operations

    Raises:
        HTTPException: If lab result not found or user lacks access
    """
    # Use helper function to verify hospital access
    lab_result = get_lab_result_with_hospital_check(lab_result_id, db, current_user)

    # Delete file from storage
    try:
        storage_service.delete_file(lab_result.original_file_path)
    except Exception:
        # Log error but continue with deletion
        pass

    # Delete database record
    db.delete(lab_result)
    db.commit()
