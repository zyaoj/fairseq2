"""SurgeryIndicator model for surgery indicators and lab values."""

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.patient import Patient


class SurgeryIndicator(Base, UUIDMixin, TimestampMixin):
    """Surgery indicators entity (手术指标).

    This corresponds to the PoC's "手术指标" entity type and contains
    pre/post operative lab values and clinical findings.
    """

    __tablename__ = "surgery_indicators"

    # Foreign key to Patient
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Patient reference (denormalized for easier access)
    patient_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Clinical info
    clinical_diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    stone_location: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )  # multi_enum: left_kidney, right_kidney, etc.
    stone_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hydronephrosis_degree: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # none, mild, moderate, severe

    # Pre-operative lab values (术前)
    alt_value_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    ast_value_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    ggt_value_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    scr_value_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    wbc_value_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    hb_value_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    urine_ph_value_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    urine_nit_value_before: Mapped[str | None] = mapped_column(String(100), nullable=True)
    urine_wbc_value_before: Mapped[str | None] = mapped_column(String(100), nullable=True)
    urine_culture_result_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    urine_ngs_result_before: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Post-operative lab values (术后)
    alt_value_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    ast_value_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    ggt_value_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    scr_value_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    wbc_value_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    hb_value_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    urine_ph_value_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    urine_nit_value_after: Mapped[str | None] = mapped_column(String(100), nullable=True)
    urine_wbc_value_after: Mapped[str | None] = mapped_column(String(100), nullable=True)
    urine_culture_result_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    urine_ngs_result_after: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Post-op stone analysis
    stone_culture_result_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    stone_ngs_result_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    stone_composition_after: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )
    stone_clearance_after: Mapped[str | None] = mapped_column(String(100), nullable=True)
    imaging_method_after: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationship
    patient: Mapped["Patient"] = relationship("Patient", back_populates="surgery_indicator")

    def __repr__(self) -> str:
        return f"<SurgeryIndicator(id={self.id}, patient_id={self.patient_id})>"
