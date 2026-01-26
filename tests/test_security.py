"""Tests for security module."""

from datetime import timedelta

from src.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self) -> None:
        """Test password hashing."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self) -> None:
        """Test verifying correct password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Test verifying incorrect password."""
        password = "mysecretpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False

    def test_different_hashes_for_same_password(self) -> None:
        """Test that same password produces different hashes (salting)."""
        password = "mysecretpassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_access_token(self) -> None:
        """Test creating an access token."""
        subject = "user-123"
        token = create_access_token(subject)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self) -> None:
        """Test decoding a valid access token."""
        subject = "user-456"
        token = create_access_token(subject)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == subject

    def test_decode_invalid_token(self) -> None:
        """Test decoding an invalid token returns None."""
        payload = decode_access_token("invalid-token")
        assert payload is None

    def test_decode_expired_token(self) -> None:
        """Test decoding an expired token returns None."""
        subject = "user-789"
        # Create a token that expired 1 hour ago
        token = create_access_token(subject, expires_delta=timedelta(hours=-1))
        payload = decode_access_token(token)
        assert payload is None

    def test_custom_expiration(self) -> None:
        """Test creating token with custom expiration."""
        subject = "user-abc"
        token = create_access_token(subject, expires_delta=timedelta(days=7))
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == subject
