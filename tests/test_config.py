"""Tests for core configuration module."""

import os

import pytest


class TestSettings:
    """Test Settings class."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        # Import inside test to avoid caching issues
        from src.core.config import Settings

        settings = Settings()

        assert settings.database_url == "postgresql://urology:urology_dev@localhost:5432/urology_db"
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30
        assert settings.milvus_host == "localhost"
        assert settings.milvus_port == 19530

    def test_environment_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that environment variables override defaults."""
        from src.core.config import Settings

        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@testhost:5432/test_db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        settings = Settings()

        assert settings.database_url == "postgresql://test:test@testhost:5432/test_db"
        assert settings.secret_key == "test-secret"

    def test_get_settings(self) -> None:
        """Test get_settings returns Settings instance."""
        from src.core.config import get_settings

        settings = get_settings()

        assert isinstance(settings, object)
        assert hasattr(settings, "database_url")
