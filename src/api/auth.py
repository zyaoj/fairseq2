"""Authentication API router."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.api.deps import get_current_active_user
from src.core.database import get_db
from src.core.security import create_access_token, get_password_hash, verify_password
from src.models.user import User
from src.schemas import Token, UserCreate, UserRead

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Safe default role for self-registration
# Elevated roles (admin) require explicit assignment by existing admin
DEFAULT_REGISTRATION_ROLE = "urologist"
ALLOWED_SELF_REGISTRATION_ROLES = {"urologist", "nurse"}


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Register a new user.

    Args:
        user_in: User registration data
        db: Database session

    Returns:
        The created user

    Raises:
        HTTPException: If username or email already exists
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate and override role - prevent privilege escalation
    # Only allow safe roles during self-registration
    requested_role = user_in.role if user_in.role else DEFAULT_REGISTRATION_ROLE
    if requested_role not in ALLOWED_SELF_REGISTRATION_ROLES:
        # Silently override to safe default instead of exposing valid role names
        requested_role = DEFAULT_REGISTRATION_ROLE

    # Create new user
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=requested_role,
        hospital_id=user_in.hospital_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.get("/me", response_model=UserRead)
def get_current_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Get current authenticated user.

    Args:
        current_user: The authenticated user from JWT token

    Returns:
        The current user's information
    """
    return current_user


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Authenticate user and return access token.

    Args:
        form_data: OAuth2 form with username and password
        db: Database session

    Returns:
        Access token and token type

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by username
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Create access token
    access_token = create_access_token(subject=user.id)

    return {"access_token": access_token, "token_type": "bearer"}
