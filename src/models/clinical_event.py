"""Clinical event models including LabResult."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class LifecyclePhase(str, enum.Enum):
    """Patient lifecycle phases in urology care."""

    CONSULTATION = "consultation"
    PRE_SURGERY = "pre_surgery"
    SURGERY = "surgery"
    POST_SURGERY = "post_surgery"
    FOLLOW_UP = "follow_up"


class ExtractionStatus(str, enum.Enum):
    """Status of data extraction from uploaded files."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ClinicalEvent(Base, UUIDMixin, TimestampMixin):
    """Base clinical event in a patient's timeline."""

    __tablename__ = "clinical_events"

    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase: Mapped[LifecyclePhase] = mapped_column(
        Enum(LifecyclePhase),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Polymorphic identity
    type: Mapped[str] = mapped_column(String(50), nullable=False)

    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "clinical_event",
    }

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="clinical_events")

    def __repr__(self) -> str:
        return f"<ClinicalEvent(id={self.id}, type={self.event_type}, date={self.event_date})>"


class LabResult(ClinicalEvent):
    """Lab result clinical event with extraction data."""

    __tablename__ = "lab_results"

    id: Mapped[str] = mapped_column(
        ForeignKey("clinical_events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    original_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # image, pdf
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus),
        default=ExtractionStatus.PENDING,
        nullable=False,
    )
    extracted_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    vector_embedding_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "lab_result",
    }

    def __repr__(self) -> str:
        return f"<LabResult(id={self.id}, status={self.extraction_status})>"


# Import here to avoid circular imports
from src.models.patient import Patient  # noqa: E402, F401
