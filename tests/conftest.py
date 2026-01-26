"""Shared test fixtures and configuration."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.database import get_db
from src.core.security import get_password_hash
from src.main import app
from src.models.base import Base
from src.models.user import User


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Apply the override once at module level
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Provide a database session for tests that need direct DB access."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Register and login a user, return authorization headers."""
    # Register a user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123",
        },
    )
    # Login
    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "securepassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(client: TestClient, db_session) -> dict[str, str]:
    """Create admin user directly in DB (simulating admin provisioning), then login.

    Note: Admin users cannot be created via self-registration for security.
    They must be provisioned by another admin or created directly in the database.
    """
    # Create admin user directly in database (bypassing registration security)
    admin_user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        role="admin",
    )
    db_session.add(admin_user)
    db_session.commit()

    # Login
    response = client.post(
        "/api/auth/login",
        data={"username": "adminuser", "password": "adminpassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
