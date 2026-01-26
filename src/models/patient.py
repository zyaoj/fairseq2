"""Patient model."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.basic_info import BasicInfo
    from src.models.clinical_event import ClinicalEvent
    from src.models.clinical_followup import ClinicalFollowup
    from src.models.nursing_followup import NursingFollowup
    from src.models.surgery_indicator import SurgeryIndicator


class Patient(Base, UUIDMixin, TimestampMixin):
    """Patient entity representing a urology patient."""

    __tablename__ = "patients"

    mrn: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    hospital_id: Mapped[str] = mapped_column(String(50), nullable=True)

    # Relationships - Clinical events
    clinical_events: Mapped[list["ClinicalEvent"]] = relationship(
        "ClinicalEvent", back_populates="patient", cascade="all, delete-orphan"
    )

    # Relationships - Urology-specific entities
    basic_info: Mapped["BasicInfo | None"] = relationship(
        "BasicInfo", back_populates="patient", uselist=False, cascade="all, delete-orphan"
    )
    surgery_indicator: Mapped["SurgeryIndicator | None"] = relationship(
        "SurgeryIndicator",
        back_populates="patient",
        uselist=False,
        cascade="all, delete-orphan",
    )
    clinical_followups: Mapped[list["ClinicalFollowup"]] = relationship(
        "ClinicalFollowup",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="ClinicalFollowup.stage",
    )
    nursing_followups: Mapped[list["NursingFollowup"]] = relationship(
        "NursingFollowup",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="NursingFollowup.stage",
    )

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, mrn={self.mrn}, name={self.first_name} {self.last_name})>"
