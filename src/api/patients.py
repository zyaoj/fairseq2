"""Patient API router."""

from typing import Annotated, Any

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_current_active_user
from src.core.database import get_db
from src.i18n import DEFAULT_LOCALE, Locale
from src.models.patient import Patient
from src.models.user import User
from src.schemas import PatientCreate, PatientRead, PatientUpdate
from src.services.summary import (
    SummaryServiceError,
    get_summary_service,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["patients"])

# Default and maximum pagination limits
DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def get_patient_with_hospital_check(
    db: Session,
    patient_id: str,
    current_user: User,
) -> Patient:
    """Get patient by ID with hospital scoping or raise 404.

    Enforces hospital/tenant scoping to prevent cross-tenant data access.

    Args:
        db: Database session
        patient_id: Patient UUID
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


class PatientSummaryResponse(BaseModel):
    """Response model for patient summary."""

    patient_id: str
    summary_text: str
    key_findings: list[str]
    recommendations: list[str]
    risk_factors: list[str]
    followup_status: dict[str, Any]
    generated_at: str
    model: str


@router.post("/", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: PatientCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Patient:
    """Create a new patient.

    Args:
        patient_in: Patient creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The created patient

    Raises:
        HTTPException: If MRN already exists
    """
    # Check if MRN already exists
    existing_patient = db.query(Patient).filter(Patient.mrn == patient_in.mrn).first()
    if existing_patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient with this MRN already exists",
        )

    # Create new patient
    patient = Patient(
        mrn=patient_in.mrn,
        first_name=patient_in.first_name,
        last_name=patient_in.last_name,
        date_of_birth=patient_in.date_of_birth,
        gender=patient_in.gender,
        hospital_id=patient_in.hospital_id,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return patient


@router.get("/", response_model=list[PatientRead])
def list_patients(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Maximum number of records to return"),
    search: str | None = Query(None, description="Search by name or MRN"),
) -> list[Patient]:
    """List patients with optional search and pagination.

    Results are scoped to the current user's hospital unless the user is an admin.

    Args:
        db: Database session
        current_user: Current authenticated user
        skip: Number of records to skip
        limit: Maximum records to return (default 50, max 100)
        search: Optional search term

    Returns:
        List of patients
    """
    query = db.query(Patient)

    # Apply hospital scoping for non-admin users
    if current_user.hospital_id:
        query = query.filter(Patient.hospital_id == current_user.hospital_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Patient.mrn.ilike(search_term))
            | (Patient.first_name.ilike(search_term))
            | (Patient.last_name.ilike(search_term))
        )

    return query.offset(skip).limit(limit).all()


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Patient:
    """Get a patient by ID.

    Args:
        patient_id: Patient UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        The patient

    Raises:
        HTTPException: If patient not found or user lacks access
    """
    return get_patient_with_hospital_check(db, patient_id, current_user)


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(
    patient_id: str,
    patient_in: PatientUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Patient:
    """Update a patient.

    Args:
        patient_id: Patient UUID
        patient_in: Patient update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The updated patient

    Raises:
        HTTPException: If patient not found or user lacks access
    """
    patient = get_patient_with_hospital_check(db, patient_id, current_user)

    # Update only provided fields
    update_data = patient_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)

    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete a patient.

    Args:
        patient_id: Patient UUID
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If patient not found or user lacks access
    """
    patient = get_patient_with_hospital_check(db, patient_id, current_user)

    db.delete(patient)
    db.commit()


@router.get("/{patient_id}/summary", response_model=PatientSummaryResponse)
def get_patient_summary(
    patient_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    include_lab_results: bool = Query(True, description="Include lab result data in summary"),
    locale: Locale = Query(Locale.ZH_CN, description="Locale for summary language"),
) -> PatientSummaryResponse:
    """Generate an AI-powered summary for a patient.

    This endpoint uses Claude to generate a comprehensive clinical summary
    by aggregating data from all patient-related entities.

    Args:
        patient_id: Patient UUID
        db: Database session
        current_user: Current authenticated user
        include_lab_results: Whether to include extracted lab result data
        locale: Locale for summary language (default: Chinese)

    Returns:
        Generated patient summary with key findings and recommendations

    Raises:
        HTTPException: If patient not found, user lacks access, or summary generation fails
    """
    # Get patient with hospital scoping
    patient = get_patient_with_hospital_check(db, patient_id, current_user)

    try:
        # Create Anthropic client
        client = anthropic.Anthropic()

        # Get summary service and generate summary
        summary_service = get_summary_service(anthropic_client=client)
        summary = summary_service.generate_summary(
            patient=patient,
            db=db,
            include_lab_results=include_lab_results,
            locale=locale.value,
        )

        return PatientSummaryResponse(
            patient_id=summary.patient_id,
            summary_text=summary.summary_text,
            key_findings=summary.key_findings,
            recommendations=summary.recommendations,
            risk_factors=summary.risk_factors,
            followup_status=summary.followup_status,
            generated_at=summary.generated_at,
            model=summary.model,
        )

    except SummaryServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Summary generation failed: {str(e)}",
        ) from e
    except anthropic.APIError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Anthropic API error: {str(e)}",
        ) from e
