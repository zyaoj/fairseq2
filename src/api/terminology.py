"""Terminology override API router.

Provides endpoints for managing terminology overrides with hierarchical resolution:
User Override → Hospital Override → Base Locale Translation
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_active_user
from src.core.database import get_db
from src.i18n import SUPPORTED_LOCALES, get_i18n_service
from src.models.terminology_override import TerminologyOverride
from src.models.user import User
from src.schemas.terminology_override import (
    ScopeType,
    TerminologyBulkRequest,
    TerminologyBulkResponse,
    TerminologyOverrideCreate,
    TerminologyOverrideRead,
    TerminologyOverrideUpdate,
    TerminologyResolution,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/terminology", tags=["terminology"])


def resolve_term(
    db: Session,
    term_key: str,
    user_id: str,
    hospital_id: str | None,
    locale: str,
) -> TerminologyResolution:
    """Resolve a term using hierarchical override lookup.

    Resolution Order: User Override → Hospital Override → Base Locale Translation

    Args:
        db: Database session
        term_key: The term key to resolve
        user_id: Current user's ID
        hospital_id: User's hospital ID (if any)
        locale: Locale code

    Returns:
        TerminologyResolution with the resolved value and source
    """
    # 1. Check user-level override
    user_override = (
        db.query(TerminologyOverride)
        .filter(
            TerminologyOverride.scope_type == ScopeType.USER.value,
            TerminologyOverride.scope_id == user_id,
            TerminologyOverride.term_key == term_key,
            TerminologyOverride.locale == locale,
        )
        .first()
    )
    if user_override:
        return TerminologyResolution(
            term_key=term_key,
            locale=locale,
            display_value=user_override.display_value,
            source="user",
        )

    # 2. Check hospital-level override
    if hospital_id:
        hospital_override = (
            db.query(TerminologyOverride)
            .filter(
                TerminologyOverride.scope_type == ScopeType.HOSPITAL.value,
                TerminologyOverride.scope_id == hospital_id,
                TerminologyOverride.term_key == term_key,
                TerminologyOverride.locale == locale,
            )
            .first()
        )
        if hospital_override:
            return TerminologyResolution(
                term_key=term_key,
                locale=locale,
                display_value=hospital_override.display_value,
                source="hospital",
            )

    # 3. Fall back to base translation
    i18n = get_i18n_service()
    base_value = i18n.get_translation(term_key, locale, default=term_key)

    return TerminologyResolution(
        term_key=term_key,
        locale=locale,
        display_value=base_value,
        source="base",
    )


@router.post("/resolve", response_model=TerminologyBulkResponse)
def resolve_terminology(
    request: TerminologyBulkRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TerminologyBulkResponse:
    """Resolve multiple term keys using hierarchical overrides.

    Resolution Order: User Override → Hospital Override → Base Locale Translation

    Args:
        request: Bulk request with term keys and locale
        db: Database session
        current_user: Current authenticated user

    Returns:
        TerminologyBulkResponse with resolved terms
    """
    if request.locale not in SUPPORTED_LOCALES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported locale: {request.locale}. Supported: {SUPPORTED_LOCALES}",
        )

    resolutions: dict[str, TerminologyResolution] = {}
    for term_key in request.term_keys:
        resolution = resolve_term(
            db=db,
            term_key=term_key,
            user_id=str(current_user.id),
            hospital_id=str(current_user.hospital_id) if current_user.hospital_id else None,
            locale=request.locale,
        )
        resolutions[term_key] = resolution

    return TerminologyBulkResponse(resolutions=resolutions)


@router.post("", response_model=TerminologyOverrideRead, status_code=status.HTTP_201_CREATED)
def create_terminology_override(
    override_in: TerminologyOverrideCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TerminologyOverride:
    """Create a new terminology override.

    - Users can create overrides with scope_type='user' for themselves
    - Only admins can create hospital-level overrides

    Args:
        override_in: Override data
        db: Database session
        current_user: Current authenticated user

    Returns:
        The created terminology override

    Raises:
        HTTPException: If validation fails or permission denied
    """
    if override_in.locale not in SUPPORTED_LOCALES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported locale: {override_in.locale}. Supported: {SUPPORTED_LOCALES}",
        )

    # Permission check
    if override_in.scope_type == ScopeType.USER:
        # Users can only create overrides for themselves
        if override_in.scope_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create override for another user",
            )
    elif override_in.scope_type == ScopeType.HOSPITAL:
        # Only admins can create hospital-level overrides
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create hospital-level overrides",
            )

    # Check for existing override (upsert logic)
    existing = (
        db.query(TerminologyOverride)
        .filter(
            TerminologyOverride.scope_type == override_in.scope_type.value,
            TerminologyOverride.scope_id == override_in.scope_id,
            TerminologyOverride.term_key == override_in.term_key,
            TerminologyOverride.locale == override_in.locale,
        )
        .first()
    )

    if existing:
        # Update existing override
        existing.display_value = override_in.display_value
        db.commit()
        db.refresh(existing)
        return existing

    # Create new override
    override = TerminologyOverride(
        scope_type=override_in.scope_type.value,
        scope_id=override_in.scope_id,
        term_key=override_in.term_key,
        locale=override_in.locale,
        display_value=override_in.display_value,
    )
    db.add(override)
    db.commit()
    db.refresh(override)

    return override


@router.get("/my-overrides", response_model=list[TerminologyOverrideRead])
def list_my_overrides(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    locale: str | None = Query(None, description="Filter by locale"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[TerminologyOverride]:
    """List the current user's terminology overrides.

    Args:
        db: Database session
        current_user: Current authenticated user
        locale: Optional locale filter
        skip: Number of records to skip
        limit: Maximum records to return

    Returns:
        List of user's terminology overrides
    """
    query = db.query(TerminologyOverride).filter(
        TerminologyOverride.scope_type == ScopeType.USER.value,
        TerminologyOverride.scope_id == str(current_user.id),
    )

    if locale:
        query = query.filter(TerminologyOverride.locale == locale)

    query = query.order_by(TerminologyOverride.term_key)

    return query.offset(skip).limit(limit).all()


@router.get("/hospital-overrides", response_model=list[TerminologyOverrideRead])
def list_hospital_overrides(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    locale: str | None = Query(None, description="Filter by locale"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[TerminologyOverride]:
    """List hospital-level terminology overrides for the user's hospital.

    Args:
        db: Database session
        current_user: Current authenticated user
        locale: Optional locale filter
        skip: Number of records to skip
        limit: Maximum records to return

    Returns:
        List of hospital terminology overrides

    Raises:
        HTTPException: If user has no hospital assigned
    """
    if not current_user.hospital_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hospital assigned to user",
        )

    query = db.query(TerminologyOverride).filter(
        TerminologyOverride.scope_type == ScopeType.HOSPITAL.value,
        TerminologyOverride.scope_id == str(current_user.hospital_id),
    )

    if locale:
        query = query.filter(TerminologyOverride.locale == locale)

    query = query.order_by(TerminologyOverride.term_key)

    return query.offset(skip).limit(limit).all()


@router.put("/{override_id}", response_model=TerminologyOverrideRead)
def update_terminology_override(
    override_id: str,
    override_update: TerminologyOverrideUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TerminologyOverride:
    """Update a terminology override.

    - Users can update their own overrides
    - Admins can update hospital-level overrides

    Args:
        override_id: Override UUID
        override_update: Update data (display_value only)
        db: Database session
        current_user: Current authenticated user

    Returns:
        The updated terminology override

    Raises:
        HTTPException: If not found or permission denied
    """
    override = (
        db.query(TerminologyOverride)
        .filter(TerminologyOverride.id == override_id)
        .first()
    )

    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminology override not found",
        )

    # Permission check
    if override.scope_type == ScopeType.USER.value:
        if override.scope_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update another user's override",
            )
    elif override.scope_type == ScopeType.HOSPITAL.value:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update hospital-level overrides",
            )

    override.display_value = override_update.display_value
    db.commit()
    db.refresh(override)

    return override


@router.delete("/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_terminology_override(
    override_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete a terminology override.

    - Users can delete their own overrides
    - Admins can delete hospital-level overrides

    Args:
        override_id: Override UUID
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If not found or permission denied
    """
    override = (
        db.query(TerminologyOverride)
        .filter(TerminologyOverride.id == override_id)
        .first()
    )

    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminology override not found",
        )

    # Permission check
    if override.scope_type == ScopeType.USER.value:
        if override.scope_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete another user's override",
            )
    elif override.scope_type == ScopeType.HOSPITAL.value:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete hospital-level overrides",
            )

    db.delete(override)
    db.commit()
