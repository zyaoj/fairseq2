"""Follow-up API router for urology-specific entities."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_active_user
from src.core.database import get_db
from src.models.basic_info import BasicInfo
from src.models.clinical_followup import ClinicalFollowup
from src.models.nursing_followup import NursingFollowup
from src.models.patient import Patient
from src.models.surgery_indicator import SurgeryIndicator
from src.models.user import User
from src.schemas.basic_info import BasicInfoCreate, BasicInfoRead, BasicInfoUpdate
from src.schemas.clinical_followup import (
    ClinicalFollowupCreate,
    ClinicalFollowupList,
    ClinicalFollowupRead,
    ClinicalFollowupUpdate,
)
from src.schemas.nursing_followup import (
    NursingFollowupCreate,
    NursingFollowupList,
    NursingFollowupRead,
    NursingFollowupUpdate,
)
from src.schemas.surgery_indicator import (
    SurgeryIndicatorCreate,
    SurgeryIndicatorRead,
    SurgeryIndicatorUpdate,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["followups"])


def get_patient_or_404(db: Session, patient_id: str, current_user: User) -> Patient:
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


# =============================================================================
# BasicInfo Endpoints
# =============================================================================


@router.get("/{patient_id}/basic-info", response_model=BasicInfoRead | None)
def get_basic_info(
    patient_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> BasicInfo | None:
    """Get patient basic info.

    Args:
        patient_id: Patient UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        BasicInfo or None if not set
    """
    patient = get_patient_or_404(db, patient_id, current_user)
    return patient.basic_info


@router.put("/{patient_id}/basic-info", response_model=BasicInfoRead)
def upsert_basic_info(
    patient_id: str,
    basic_info_in: BasicInfoCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> BasicInfo:
    """Create or update patient basic info.

    Args:
        patient_id: Patient UUID
        basic_info_in: BasicInfo data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The created/updated BasicInfo
    """
    patient = get_patient_or_404(db, patient_id, current_user)

    if patient.basic_info:
        # Update existing
        update_data = basic_info_in.model_dump()
        for field, value in update_data.items():
            setattr(patient.basic_info, field, value)
        db.commit()
        db.refresh(patient.basic_info)
        return patient.basic_info
    else:
        # Create new
        basic_info = BasicInfo(patient_id=patient_id, **basic_info_in.model_dump())
        db.add(basic_info)
        db.commit()
        db.refresh(basic_info)
        return basic_info


@router.patch("/{patient_id}/basic-info", response_model=BasicInfoRead)
def update_basic_info(
    patient_id: str,
    basic_info_in: BasicInfoUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> BasicInfo:
    """Partially update patient basic info.

    Args:
        patient_id: Patient UUID
        basic_info_in: Partial BasicInfo update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The updated BasicInfo

    Raises:
        HTTPException: If BasicInfo not found
    """
    patient = get_patient_or_404(db, patient_id, current_user)

    if not patient.basic_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BasicInfo not found. Use PUT to create.",
        )

    update_data = basic_info_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient.basic_info, field, value)

    db.commit()
    db.refresh(patient.basic_info)
    return patient.basic_info


# =============================================================================
# SurgeryIndicator Endpoints
# =============================================================================


@router.get("/{patient_id}/surgery", response_model=SurgeryIndicatorRead | None)
def get_surgery_indicator(
    patient_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SurgeryIndicator | None:
    """Get patient surgery indicators.

    Args:
        patient_id: Patient UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        SurgeryIndicator or None if not set
    """
    patient = get_patient_or_404(db, patient_id, current_user)
    return patient.surgery_indicator


@router.put("/{patient_id}/surgery", response_model=SurgeryIndicatorRead)
def upsert_surgery_indicator(
    patient_id: str,
    surgery_in: SurgeryIndicatorCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SurgeryIndicator:
    """Create or update patient surgery indicators.

    Args:
        patient_id: Patient UUID
        surgery_in: SurgeryIndicator data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The created/updated SurgeryIndicator
    """
    patient = get_patient_or_404(db, patient_id, current_user)

    if patient.surgery_indicator:
        # Update existing
        update_data = surgery_in.model_dump()
        for field, value in update_data.items():
            setattr(patient.surgery_indicator, field, value)
        db.commit()
        db.refresh(patient.surgery_indicator)
        return patient.surgery_indicator
    else:
        # Create new
        surgery = SurgeryIndicator(patient_id=patient_id, **surgery_in.model_dump())
        db.add(surgery)
        db.commit()
        db.refresh(surgery)
        return surgery


@router.patch("/{patient_id}/surgery", response_model=SurgeryIndicatorRead)
def update_surgery_indicator(
    patient_id: str,
    surgery_in: SurgeryIndicatorUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SurgeryIndicator:
    """Partially update patient surgery indicators.

    Args:
        patient_id: Patient UUID
        surgery_in: Partial SurgeryIndicator update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The updated SurgeryIndicator

    Raises:
        HTTPException: If SurgeryIndicator not found
    """
    patient = get_patient_or_404(db, patient_id, current_user)

    if not patient.surgery_indicator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SurgeryIndicator not found. Use PUT to create.",
        )

    update_data = surgery_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient.surgery_indicator, field, value)

    db.commit()
    db.refresh(patient.surgery_indicator)
    return patient.surgery_indicator


# =============================================================================
# ClinicalFollowup Endpoints
# =============================================================================


@router.get("/{patient_id}/clinical-followups", response_model=ClinicalFollowupList)
def list_clinical_followups(
    patient_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Get all clinical follow-ups for a patient.

    Args:
        patient_id: Patient UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of clinical follow-ups with stage info
    """
    patient = get_patient_or_404(db, patient_id, current_user)
    return {
        "patient_id": patient_id,
        "followups": patient.clinical_followups,
        "total_stages": 5,
    }


@router.get(
    "/{patient_id}/clinical-followups/{stage}", response_model=ClinicalFollowupRead | None
)
def get_clinical_followup(
    patient_id: str,
    stage: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ClinicalFollowup | None:
    """Get a specific clinical follow-up stage.

    Args:
        patient_id: Patient UUID
        stage: Follow-up stage (1-5)
        db: Database session
        current_user: Current authenticated user

    Returns:
        ClinicalFollowup or None if not recorded

    Raises:
        HTTPException: If stage is invalid
    """
    if stage < 1 or stage > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage must be between 1 and 5",
        )

    patient = get_patient_or_404(db, patient_id, current_user)

    followup = (
        db.query(ClinicalFollowup)
        .filter(ClinicalFollowup.patient_id == patient_id, ClinicalFollowup.stage == stage)
        .first()
    )
    return followup


@router.put("/{patient_id}/clinical-followups/{stage}", response_model=ClinicalFollowupRead)
def upsert_clinical_followup(
    patient_id: str,
    stage: int,
    followup_in: ClinicalFollowupCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ClinicalFollowup:
    """Create or update a clinical follow-up stage.

    Args:
        patient_id: Patient UUID
        stage: Follow-up stage (1-5)
        followup_in: ClinicalFollowup data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The created/updated ClinicalFollowup

    Raises:
        HTTPException: If stage is invalid or doesn't match body
    """
    if stage < 1 or stage > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage must be between 1 and 5",
        )

    if followup_in.stage != stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stage in URL ({stage}) must match stage in body ({followup_in.stage})",
        )

    patient = get_patient_or_404(db, patient_id, current_user)

    existing = (
        db.query(ClinicalFollowup)
        .filter(ClinicalFollowup.patient_id == patient_id, ClinicalFollowup.stage == stage)
        .first()
    )

    if existing:
        # Update existing
        update_data = followup_in.model_dump()
        for field, value in update_data.items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        followup = ClinicalFollowup(patient_id=patient_id, **followup_in.model_dump())
        db.add(followup)
        db.commit()
        db.refresh(followup)
        return followup


@router.patch("/{patient_id}/clinical-followups/{stage}", response_model=ClinicalFollowupRead)
def update_clinical_followup(
    patient_id: str,
    stage: int,
    followup_in: ClinicalFollowupUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ClinicalFollowup:
    """Partially update a clinical follow-up stage.

    Args:
        patient_id: Patient UUID
        stage: Follow-up stage (1-5)
        followup_in: Partial ClinicalFollowup update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The updated ClinicalFollowup

    Raises:
        HTTPException: If follow-up not found
    """
    if stage < 1 or stage > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage must be between 1 and 5",
        )

    patient = get_patient_or_404(db, patient_id, current_user)

    existing = (
        db.query(ClinicalFollowup)
        .filter(ClinicalFollowup.patient_id == patient_id, ClinicalFollowup.stage == stage)
        .first()
    )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ClinicalFollowup stage {stage} not found. Use PUT to create.",
        )

    update_data = followup_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)

    db.commit()
    db.refresh(existing)
    return existing


@router.delete(
    "/{patient_id}/clinical-followups/{stage}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_clinical_followup(
    patient_id: str,
    stage: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete a clinical follow-up stage.

    Args:
        patient_id: Patient UUID
        stage: Follow-up stage (1-5)
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If stage is invalid or follow-up not found
    """
    if stage < 1 or stage > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage must be between 1 and 5",
        )

    patient = get_patient_or_404(db, patient_id, current_user)

    existing = (
        db.query(ClinicalFollowup)
        .filter(ClinicalFollowup.patient_id == patient_id, ClinicalFollowup.stage == stage)
        .first()
    )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ClinicalFollowup stage {stage} not found.",
        )

    db.delete(existing)
    db.commit()


# =============================================================================
# NursingFollowup Endpoints
# =============================================================================


@router.get("/{patient_id}/nursing-followups", response_model=NursingFollowupList)
def list_nursing_followups(
    patient_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Get all nursing follow-ups for a patient.

    Args:
        patient_id: Patient UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of nursing follow-ups with stage info
    """
    patient = get_patient_or_404(db, patient_id, current_user)
    return {
        "patient_id": patient_id,
        "followups": patient.nursing_followups,
        "total_stages": 6,
    }


@router.get(
    "/{patient_id}/nursing-followups/{stage}", response_model=NursingFollowupRead | None
)
def get_nursing_followup(
    patient_id: str,
    stage: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NursingFollowup | None:
    """Get a specific nursing follow-up stage.

    Args:
        patient_id: Patient UUID
        stage: Follow-up stage (1-6)
        db: Database session
        current_user: Current authenticated user

    Returns:
        NursingFollowup or None if not recorded

    Raises:
        HTTPException: If stage is invalid
    """
    if stage < 1 or stage > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage must be between 1 and 6",
        )

    patient = get_patient_or_404(db, patient_id, current_user)

    followup = (
        db.query(NursingFollowup)
        .filter(NursingFollowup.patient_id == patient_id, NursingFollowup.stage == stage)
        .first()
    )
    return followup


@router.put("/{patient_id}/nursing-followups/{stage}", response_model=NursingFollowupRead)
def upsert_nursing_followup(
    patient_id: str,
    stage: int,
    followup_in: NursingFollowupCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NursingFollowup:
    """Create or update a nursing follow-up stage.

    Args:
        patient_id: Patient UUID
        stage: Follow-up stage (1-6)
        followup_in: NursingFollowup data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The created/updated NursingFollowup

    Raises:
        HTTPException: If stage is invalid or doesn't match body
    """
    if stage < 1 or stage > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage must be between 1 and 6",
        )

    if followup_in.stage != stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stage in URL ({stage}) must match stage in body ({followup_in.stage})",
        )

    patient = get_patient_or_404(db, patient_id, current_user)

    existing = (
        db.query(NursingFollowup)
        .filter(NursingFollowup.patient_id == patient_id, NursingFollowup.stage == stage)
        .first()
    )

    if existing:
        # Update existing
        update_data = followup_in.model_dump()
        for field, value in update_data.items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        followup = NursingFollowup(patient_id=patient_id, **followup_in.model_dump())
        db.add(followup)
        db.commit()
        db.refresh(followup)
        return followup


@router.patch("/{patient_id}/nursing-followups/{stage}", response_model=NursingFollowupRead)
def update_nursing_followup(
    patient_id: str,
    stage: int,
    followup_in: NursingFollowupUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NursingFollowup:
    """Partially update a nursing follow-up stage.

    Args:
        patient_id: Patient UUID
        stage: Follow-up stage (1-6)
        followup_in: Partial NursingFollowup update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The updated NursingFollowup

    Raises:
        HTTPException: If follow-up not found
    """
    if stage < 1 or stage > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage must be between 1 and 6",
        )

    patient = get_patient_or_404(db, patient_id, current_user)

    existing = (
        db.query(NursingFollowup)
        .filter(NursingFollowup.patient_id == patient_id, NursingFollowup.stage == stage)
        .first()
    )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NursingFollowup stage {stage} not found. Use PUT to create.",
        )

    update_data = followup_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)

    db.commit()
    db.refresh(existing)
    return existing


@router.delete(
    "/{patient_id}/nursing-followups/{stage}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_nursing_followup(
    patient_id: str,
    stage: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete a nursing follow-up stage.

    Args:
        patient_id: Patient UUID
        stage: Follow-up stage (1-6)
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If stage is invalid or follow-up not found
    """
    if stage < 1 or stage > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage must be between 1 and 6",
        )

    patient = get_patient_or_404(db, patient_id, current_user)

    existing = (
        db.query(NursingFollowup)
        .filter(NursingFollowup.patient_id == patient_id, NursingFollowup.stage == stage)
        .first()
    )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NursingFollowup stage {stage} not found.",
        )

    db.delete(existing)
    db.commit()
