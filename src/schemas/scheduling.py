"""Pydantic schemas for follow-up scheduling."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class FollowupType(str, Enum):
    """Type of follow-up."""

    CLINICAL = "clinical"
    NURSING = "nursing"


class FollowupStatus(str, Enum):
    """Status of a follow-up."""

    PENDING = "pending"  # Not yet due
    DUE = "due"  # Due within the window
    OVERDUE = "overdue"  # Past due date
    COMPLETED = "completed"  # Already recorded


class ScheduledFollowup(BaseModel):
    """Schema for a scheduled follow-up item."""

    patient_id: str
    patient_name: str | None = None
    followup_type: FollowupType
    stage: int
    stage_name: str
    expected_date: date
    status: FollowupStatus
    days_until_due: int = Field(
        ..., description="Negative if overdue, positive if in future"
    )
    completed_date: date | None = Field(
        None, description="Date when follow-up was completed (if any)"
    )


class FollowupScheduleResponse(BaseModel):
    """Schema for the follow-up schedule response."""

    overdue: list[ScheduledFollowup] = Field(default_factory=list)
    due: list[ScheduledFollowup] = Field(default_factory=list)
    upcoming: list[ScheduledFollowup] = Field(default_factory=list)
    total_overdue: int = 0
    total_due: int = 0
    total_upcoming: int = 0


class NextFollowupResponse(BaseModel):
    """Schema for the next follow-up response for a patient."""

    patient_id: str
    patient_name: str | None = None
    surgery_date: date | None = None
    next_clinical: ScheduledFollowup | None = None
    next_nursing: ScheduledFollowup | None = None
    all_followups: list[ScheduledFollowup] = Field(
        default_factory=list, description="All pending/due/overdue follow-ups"
    )
