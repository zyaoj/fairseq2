"""Tests for database connection module."""

import pytest
from sqlalchemy.orm import Session


class TestDatabase:
    """Test database module."""

    def test_get_db_returns_session(self) -> None:
        """Test that get_db yields a Session."""
        from src.core.database import get_db

        gen = get_db()
        db = next(gen)

        assert isinstance(db, Session)

        # Clean up
        try:
            next(gen)
        except StopIteration:
            pass

    def test_session_local_configured(self) -> None:
        """Test SessionLocal is properly configured."""
        from src.core.database import SessionLocal

        assert SessionLocal is not None

    def test_engine_configured(self) -> None:
        """Test engine is properly configured."""
        from src.core.database import engine

        assert engine is not None
        assert "urology" in str(engine.url)
