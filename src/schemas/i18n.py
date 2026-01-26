"""Schemas for translation feedback."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.translation_feedback import FeedbackStatus


class TranslationFeedbackCreate(BaseModel):
    """Schema for creating translation feedback."""

    translation_key: str = Field(..., min_length=1, max_length=255)
    locale: str = Field(default="zh-CN", max_length=10)
    original_value: str = Field(..., min_length=1)
    suggested_value: str = Field(..., min_length=1)


class TranslationFeedbackRead(BaseModel):
    """Schema for reading translation feedback."""

    id: str
    user_id: str
    translation_key: str
    locale: str
    original_value: str
    suggested_value: str
    status: FeedbackStatus
    reviewed_by: str | None
    created_at: datetime
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class TranslationFeedbackUpdate(BaseModel):
    """Schema for updating translation feedback (admin review)."""

    status: FeedbackStatus
