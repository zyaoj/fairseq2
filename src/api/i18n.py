"""Internationalization (i18n) API router."""

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_active_user
from src.core.database import get_db
from src.i18n import SUPPORTED_LOCALES, get_i18n_service
from src.models.translation_feedback import FeedbackStatus, TranslationFeedback
from src.models.user import User
from src.schemas.i18n import (
    TranslationFeedbackCreate,
    TranslationFeedbackRead,
    TranslationFeedbackUpdate,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/i18n", tags=["i18n"])


@router.post("/feedback", response_model=TranslationFeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_translation_feedback(
    feedback_in: TranslationFeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TranslationFeedback:
    """Submit translation feedback.

    Args:
        feedback_in: Translation feedback data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The created translation feedback

    Raises:
        HTTPException: If locale is not supported
    """
    if feedback_in.locale not in SUPPORTED_LOCALES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported locale: {feedback_in.locale}. Supported locales: {SUPPORTED_LOCALES}",
        )

    # Create new translation feedback
    feedback = TranslationFeedback(
        user_id=current_user.id,
        translation_key=feedback_in.translation_key,
        locale=feedback_in.locale,
        original_value=feedback_in.original_value,
        suggested_value=feedback_in.suggested_value,
        status=FeedbackStatus.PENDING,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return feedback


@router.get("/feedback", response_model=list[TranslationFeedbackRead])
def list_translation_feedback(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    status_filter: FeedbackStatus | None = Query(None, description="Filter by status"),
    locale: str | None = Query(None, description="Filter by locale"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
) -> list[TranslationFeedback]:
    """List translation feedback entries (admin only).

    Args:
        db: Database session
        current_user: Current authenticated user
        status_filter: Optional status filter
        locale: Optional locale filter
        skip: Number of records to skip
        limit: Maximum records to return

    Returns:
        List of translation feedback entries

    Raises:
        HTTPException: If user is not an admin
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view all translation feedback",
        )

    query = db.query(TranslationFeedback)

    if status_filter:
        query = query.filter(TranslationFeedback.status == status_filter)

    if locale:
        query = query.filter(TranslationFeedback.locale == locale)

    # Order by creation date, newest first
    query = query.order_by(TranslationFeedback.created_at.desc())

    return query.offset(skip).limit(limit).all()


@router.patch("/feedback/{feedback_id}", response_model=TranslationFeedbackRead)
def update_translation_feedback(
    feedback_id: str,
    feedback_update: TranslationFeedbackUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TranslationFeedback:
    """Update translation feedback status (admin only).

    Args:
        feedback_id: Feedback UUID
        feedback_update: Feedback update data (status)
        db: Database session
        current_user: Current authenticated user

    Returns:
        The updated translation feedback

    Raises:
        HTTPException: If user is not admin or feedback not found
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update translation feedback",
        )

    # Find the feedback
    feedback = db.query(TranslationFeedback).filter(TranslationFeedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Translation feedback not found",
        )

    # Update status
    feedback.status = feedback_update.status
    feedback.reviewed_by = current_user.id
    feedback.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(feedback)

    return feedback


@router.get("/{locale}")
def get_translations(locale: str) -> dict[str, Any]:
    """Get all translations for a locale.

    Args:
        locale: Locale code (e.g., "zh-CN", "en")

    Returns:
        Dictionary of translations for the locale

    Raises:
        HTTPException: If locale is not supported
    """
    if locale not in SUPPORTED_LOCALES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported locale: {locale}. Supported locales: {SUPPORTED_LOCALES}",
        )

    i18n = get_i18n_service()
    translations = i18n.get_all_translations(locale)

    return {"locale": locale, "translations": translations}
