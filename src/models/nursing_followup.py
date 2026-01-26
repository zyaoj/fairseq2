"""NursingFollowup model for nursing follow-up records."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.patient import Patient


class NursingFollowup(Base, UUIDMixin, TimestampMixin):
    """Nursing follow-up entity (护理随访).

    This corresponds to the PoC's "护理随访" entity type.
    6 stages: 术后7天, 1个月, 3个月, 6个月, 9个月, 12个月

    Stage schedule:
    - Stage 1: 7 days post-surgery
    - Stage 2: 1 month post-surgery (30 days)
    - Stage 3: 3 months post-surgery (90 days)
    - Stage 4: 6 months post-surgery (180 days)
    - Stage 5: 9 months post-surgery (270 days)
    - Stage 6: 12 months post-surgery (365 days)
    """

    __tablename__ = "nursing_followups"

    # Foreign key to Patient
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Patient reference (denormalized for easier access)
    patient_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Stage info (1-6)
    stage: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    followup_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Follow-up mode
    nursing_mode: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # phone, video, home_visit

    # Medication info
    nursing_discharge_drug: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # 出院带药
    nursing_antibiotic: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # 抗生素
    nursing_antibiotic_dose: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    nursing_other_drug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nursing_other_drug_dose: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    nursing_timed_med: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )  # 定时服药

    # Urine monitoring
    nursing_urine_ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    nursing_urine_output: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )  # 排尿量>2L
    nursing_urine_color: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 0-8 scale

    # Adverse effects and conditions
    nursing_adverse_effects: Mapped[str | None] = mapped_column(Text, nullable=True)
    nursing_acidosis: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # 酸中毒
    nursing_hco3: Mapped[float | None] = mapped_column(Float, nullable=True)  # HCO3 value

    # Location and stone tracking
    nursing_followup_location: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    nursing_residual_stone: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # 残石排出

    # Lifestyle
    nursing_water: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # 饮水提醒
    nursing_diet: Mapped[str | None] = mapped_column(Text, nullable=True)  # 饮食偏好

    # Mental health
    nursing_psqi: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Pittsburgh Sleep Quality Index
    nursing_psqi_drug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nursing_depression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nursing_depression_anxiety: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    nursing_support: Mapped[str | None] = mapped_column(Text, nullable=True)  # 心理疏导

    # Relationship
    patient: Mapped["Patient"] = relationship(
        "Patient", back_populates="nursing_followups"
    )

    def __repr__(self) -> str:
        return f"<NursingFollowup(id={self.id}, patient_id={self.patient_id}, stage={self.stage})>"

    @property
    def stage_name(self) -> str:
        """Get the display name for this stage."""
        stage_names = {
            1: "术后7天",
            2: "术后1个月",
            3: "术后3个月",
            4: "术后6个月",
            5: "术后9个月",
            6: "术后12个月",
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
            5: 270,
            6: 365,
        }
        return days_map.get(self.stage, 0)
