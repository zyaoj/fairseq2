"""Follow-up scheduling API router."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_active_user
from src.core.database import get_db
from src.models.basic_info import BasicInfo
from src.models.clinical_followup import ClinicalFollowup
from src.models.nursing_followup import NursingFollowup
from src.models.patient import Patient
from src.models.user import User
from src.schemas.scheduling import (
    FollowupScheduleResponse,
    FollowupStatus,
    FollowupType,
    NextFollowupResponse,
    ScheduledFollowup,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scheduling"])

# Days before due date to consider "due"
DUE_WINDOW_DAYS = 7

# Stage mappings
CLINICAL_STAGE_DAYS = {1: 7, 2: 30, 3: 90, 4: 180, 5: 365}
NURSING_STAGE_DAYS = {1: 7, 2: 30, 3: 90, 4: 180, 5: 270, 6: 365}

CLINICAL_STAGE_NAMES = {
    1: "术后7天",
    2: "术后1个月",
    3: "术后3个月",
    4: "术后6个月",
    5: "术后12个月",
}

NURSING_STAGE_NAMES = {
    1: "术后7天",
    2: "术后1个月",
    3: "术后3个月",
    4: "术后6个月",
    5: "术后9个月",
    6: "术后12个月",
}


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


def calculate_scheduled_followups(
    patient: Patient,
    surgery_date: date,
    today: date,
) -> list[ScheduledFollowup]:
    """Calculate all scheduled follow-ups for a patient.

    Args:
        patient: Patient object with follow-ups loaded
        surgery_date: Date of surgery
        today: Today's date for comparison

    Returns:
        List of scheduled follow-ups with status
    """
    result: list[ScheduledFollowup] = []

    # Get existing follow-up dates by stage
    clinical_completed: dict[int, date | None] = {}
    for fu in patient.clinical_followups:
        clinical_completed[fu.stage] = fu.followup_date

    nursing_completed: dict[int, date | None] = {}
    for fu in patient.nursing_followups:
        nursing_completed[fu.stage] = fu.followup_date

    patient_name = patient.basic_info.patient_name if patient.basic_info else None

    # Clinical follow-ups (5 stages)
    for stage, days in CLINICAL_STAGE_DAYS.items():
        expected_date = surgery_date + timedelta(days=days)
        completed_date = clinical_completed.get(stage)
        days_until_due = (expected_date - today).days

        if completed_date:
            status = FollowupStatus.COMPLETED
        elif days_until_due < 0:
            status = FollowupStatus.OVERDUE
        elif days_until_due <= DUE_WINDOW_DAYS:
            status = FollowupStatus.DUE
        else:
            status = FollowupStatus.PENDING

        result.append(
            ScheduledFollowup(
                patient_id=patient.id,
                patient_name=patient_name,
                followup_type=FollowupType.CLINICAL,
                stage=stage,
                stage_name=CLINICAL_STAGE_NAMES[stage],
                expected_date=expected_date,
                status=status,
                days_until_due=days_until_due,
                completed_date=completed_date,
            )
        )

    # Nursing follow-ups (6 stages)
    for stage, days in NURSING_STAGE_DAYS.items():
        expected_date = surgery_date + timedelta(days=days)
        completed_date = nursing_completed.get(stage)
        days_until_due = (expected_date - today).days

        if completed_date:
            status = FollowupStatus.COMPLETED
        elif days_until_due < 0:
            status = FollowupStatus.OVERDUE
        elif days_until_due <= DUE_WINDOW_DAYS:
            status = FollowupStatus.DUE
        else:
            status = FollowupStatus.PENDING

        result.append(
            ScheduledFollowup(
                patient_id=patient.id,
                patient_name=patient_name,
                followup_type=FollowupType.NURSING,
                stage=stage,
                stage_name=NURSING_STAGE_NAMES[stage],
                expected_date=expected_date,
                status=status,
                days_until_due=days_until_due,
                completed_date=completed_date,
            )
        )

    return result


@router.get("/followup-schedule", response_model=FollowupScheduleResponse)
def get_followup_schedule(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    days_ahead: int = Query(30, ge=1, le=365, description="Days ahead to show upcoming"),
) -> FollowupScheduleResponse:
    """Get follow-up schedule for all patients.

    Returns lists of overdue, due, and upcoming follow-ups.

    Args:
        db: Database session
        current_user: Current authenticated user
        days_ahead: Number of days ahead to include in upcoming list

    Returns:
        FollowupScheduleResponse with categorized follow-ups
    """
    today = date.today()

    # Build query for patients with surgery dates
    query = (
        db.query(Patient)
        .join(BasicInfo, Patient.id == BasicInfo.patient_id)
        .filter(BasicInfo.surgery_date.isnot(None))
    )

    # Apply hospital scoping for non-admin users
    if current_user.hospital_id:
        query = query.filter(Patient.hospital_id == current_user.hospital_id)

    patients_with_surgery = query.all()

    overdue: list[ScheduledFollowup] = []
    due: list[ScheduledFollowup] = []
    upcoming: list[ScheduledFollowup] = []

    for patient in patients_with_surgery:
        if not patient.basic_info or not patient.basic_info.surgery_date:
            continue

        surgery_date = patient.basic_info.surgery_date
        followups = calculate_scheduled_followups(patient, surgery_date, today)

        for fu in followups:
            if fu.status == FollowupStatus.OVERDUE:
                overdue.append(fu)
            elif fu.status == FollowupStatus.DUE:
                due.append(fu)
            elif fu.status == FollowupStatus.PENDING and fu.days_until_due <= days_ahead:
                upcoming.append(fu)

    # Sort by urgency
    overdue.sort(key=lambda x: x.days_until_due)  # Most overdue first
    due.sort(key=lambda x: x.days_until_due)  # Soonest due first
    upcoming.sort(key=lambda x: x.days_until_due)  # Soonest upcoming first

    return FollowupScheduleResponse(
        overdue=overdue,
        due=due,
        upcoming=upcoming,
        total_overdue=len(overdue),
        total_due=len(due),
        total_upcoming=len(upcoming),
    )


@router.get("/patients/{patient_id}/next-followup", response_model=NextFollowupResponse)
def get_next_followup(
    patient_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NextFollowupResponse:
    """Get the next due follow-ups for a patient.

    Args:
        patient_id: Patient UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        NextFollowupResponse with next clinical and nursing follow-ups
    """
    patient = get_patient_or_404(db, patient_id, current_user)

    if not patient.basic_info:
        return NextFollowupResponse(
            patient_id=patient_id,
            patient_name=None,
            surgery_date=None,
            next_clinical=None,
            next_nursing=None,
            all_followups=[],
        )

    surgery_date = patient.basic_info.surgery_date
    patient_name = patient.basic_info.patient_name

    if not surgery_date:
        return NextFollowupResponse(
            patient_id=patient_id,
            patient_name=patient_name,
            surgery_date=None,
            next_clinical=None,
            next_nursing=None,
            all_followups=[],
        )

    today = date.today()
    followups = calculate_scheduled_followups(patient, surgery_date, today)

    # Filter to only non-completed
    pending_followups = [
        fu for fu in followups if fu.status != FollowupStatus.COMPLETED
    ]

    # Find next clinical and nursing
    next_clinical = None
    next_nursing = None

    for fu in sorted(pending_followups, key=lambda x: x.expected_date):
        if fu.followup_type == FollowupType.CLINICAL and next_clinical is None:
            next_clinical = fu
        elif fu.followup_type == FollowupType.NURSING and next_nursing is None:
            next_nursing = fu

        if next_clinical and next_nursing:
            break

    return NextFollowupResponse(
        patient_id=patient_id,
        patient_name=patient_name,
        surgery_date=surgery_date,
        next_clinical=next_clinical,
        next_nursing=next_nursing,
        all_followups=pending_followups,
    )
