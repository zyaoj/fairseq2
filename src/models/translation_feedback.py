"""TranslationFeedback model for i18n user feedback."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class FeedbackStatus(str, enum.Enum):
    """Status of translation feedback."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TranslationFeedback(Base):
    """Model for storing user translation feedback."""

    __tablename__ = "translation_feedback"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )
    translation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="zh-CN")
    original_value: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_value: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[FeedbackStatus] = mapped_column(
        Enum(FeedbackStatus),
        default=FeedbackStatus.PENDING,
        nullable=False,
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "User",
        foreign_keys=[user_id],
        back_populates="translation_feedback",
    )
    reviewer: Mapped["User | None"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "User",
        foreign_keys=[reviewed_by],
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<TranslationFeedback(key={self.translation_key}, status={self.status})>"
