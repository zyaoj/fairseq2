"""User Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: str = Field(default="urologist", max_length=50)
    hospital_id: str | None = Field(None, max_length=50)
    locale: str = Field(default="zh-CN", max_length=10)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    email: EmailStr | None = None
    role: str | None = Field(None, max_length=50)
    hospital_id: str | None = Field(None, max_length=50)
    is_active: bool | None = None
    locale: str | None = Field(None, max_length=10)


class UserRead(UserBase):
    """Schema for reading user data (excludes password)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str
    password: str
