"""Common Pydantic schemas."""

from pydantic import BaseModel


class Token(BaseModel):
    """JWT token response schema."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: str  # User ID
    exp: int  # Expiration timestamp


class Message(BaseModel):
    """Generic message response schema."""

    message: str
