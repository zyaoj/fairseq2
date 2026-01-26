"""TerminologyOverride model for hierarchical terminology customization."""

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDMixin


class TerminologyOverride(Base, UUIDMixin, TimestampMixin):
    """Terminology override for hierarchical terminology customization.

    Allows hospitals and individual users to customize medical terminology
    display names without modifying core translation files.

    Resolution Order: User Override → Hospital Override → Base Locale Translation

    Scope types:
    - 'user': User-specific override, scope_id is user_id
    - 'hospital': Hospital-wide override, scope_id is hospital_id
    """

    __tablename__ = "terminology_overrides"

    # Scope configuration
    scope_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'user' or 'hospital'
    scope_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )  # user_id or hospital_id (UUID as string)

    # Term identification
    term_key: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # e.g., "stone_location.left_kidney"
    locale: Mapped[str] = mapped_column(
        String(10), nullable=False, default="zh-CN"
    )  # e.g., "zh-CN", "en"

    # Custom display value
    display_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Unique constraint: one override per (scope_type, scope_id, term_key, locale)
    __table_args__ = (
        UniqueConstraint(
            "scope_type", "scope_id", "term_key", "locale", name="uq_terminology_override"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TerminologyOverride("
            f"scope_type={self.scope_type}, "
            f"scope_id={self.scope_id}, "
            f"term_key={self.term_key}, "
            f"locale={self.locale})>"
        )
