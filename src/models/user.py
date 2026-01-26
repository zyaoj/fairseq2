"""User model for authentication."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.translation_feedback import TranslationFeedback


class User(Base, UUIDMixin, TimestampMixin):
    """User entity for authentication and authorization."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="urologist", nullable=False)
    hospital_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="zh-CN", nullable=False)

    # Relationships
    translation_feedback: Mapped[list["TranslationFeedback"]] = relationship(
        "TranslationFeedback",
        back_populates="user",
        foreign_keys="TranslationFeedback.user_id",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
