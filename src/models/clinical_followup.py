"""ClinicalFollowup model for clinical follow-up records."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.patient import Patient


class ClinicalFollowup(Base, UUIDMixin, TimestampMixin):
    """Clinical follow-up entity (临床随访).

    This corresponds to the PoC's "临床随访" entity type.
    5 stages: 术后7天, 1个月, 3个月, 6个月, 12个月

    Stage schedule:
    - Stage 1: 7 days post-surgery
    - Stage 2: 1 month post-surgery (30 days)
    - Stage 3: 3 months post-surgery (90 days)
    - Stage 4: 6 months post-surgery (180 days)
    - Stage 5: 12 months post-surgery (365 days)
    """

    __tablename__ = "clinical_followups"

    # Foreign key to Patient
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Patient reference (denormalized for easier access)
    patient_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Stage info (1-5)
    stage: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    followup_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Clinical findings
    followup_recurrence: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # 复发情况
    followup_stone_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    followup_imaging: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lab values at follow-up
    followup_alt: Mapped[float | None] = mapped_column(Float, nullable=True)
    followup_ast: Mapped[float | None] = mapped_column(Float, nullable=True)
    followup_ggt: Mapped[float | None] = mapped_column(Float, nullable=True)
    followup_scr: Mapped[float | None] = mapped_column(Float, nullable=True)
    followup_wbc: Mapped[float | None] = mapped_column(Float, nullable=True)
    followup_hb: Mapped[float | None] = mapped_column(Float, nullable=True)
    followup_urine_ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    followup_urine_nit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    followup_urine_wbc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    followup_urine_culture: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Medication tracking
    followup_medication: Mapped[str | None] = mapped_column(String(200), nullable=True)
    followup_medication_dose: Mapped[float | None] = mapped_column(Float, nullable=True)
    followup_medication_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    followup_compliance: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # 用药依从性
    followup_adverse: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # 不良反应
    followup_plan: Mapped[str | None] = mapped_column(Text, nullable=True)  # 随访计划

    # Relationship
    patient: Mapped["Patient"] = relationship(
        "Patient", back_populates="clinical_followups"
    )

    def __repr__(self) -> str:
        return f"<ClinicalFollowup(id={self.id}, patient_id={self.patient_id}, stage={self.stage})>"

    @property
    def stage_name(self) -> str:
        """Get the display name for this stage."""
        stage_names = {
            1: "术后7天",
            2: "术后1个月",
            3: "术后3个月",
            4: "术后6个月",
            5: "术后12个月",
        }
        return stage_names.get(self.stage, f"Stage {self.stage}")

    @property
    def days_after_surgery(self) -> int:
        """Get the expected days after surgery for this stage."""
        days_map = {
            1: 7,
            2: 30,
            3: 90,
            4: 180,
            5: 365,
        }
        return days_map.get(self.stage, 0)
