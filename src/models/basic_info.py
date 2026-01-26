"""BasicInfo model for patient basic information."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.patient import Patient


class BasicInfo(Base, UUIDMixin, TimestampMixin):
    """Patient basic information entity (基本信息).

    This corresponds to the PoC's "基本信息" entity type and contains
    patient demographics, medical history, and lifestyle information.
    """

    __tablename__ = "basic_info"

    # Foreign key to Patient
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Demographics
    patient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)  # male, female
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Lifestyle
    diet_preference: Mapped[str | None] = mapped_column(Text, nullable=True)
    likes_diet_preference: Mapped[str | None] = mapped_column(Text, nullable=True)
    dislikes_diet_preference: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifestyle: Mapped[str | None] = mapped_column(Text, nullable=True)
    daily_water_intake: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Medical history
    medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    stone_discovery_method: Mapped[str | None] = mapped_column(String(200), nullable=True)
    previous_urinary_infection_pathogen: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    previous_infection_medication: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Boolean flags (medical history checkboxes)
    family_history_of_stone: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    repeated_urinary_infection: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Dates
    first_urinary_infection_time: Mapped[date | None] = mapped_column(Date, nullable=True)
    surgery_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Surgery info
    surgery_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stone_composition: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    patient: Mapped["Patient"] = relationship("Patient", back_populates="basic_info")

    def __repr__(self) -> str:
        return f"<BasicInfo(id={self.id}, patient_id={self.patient_id}, name={self.patient_name})>"
