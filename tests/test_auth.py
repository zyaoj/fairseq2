"""Tests for authentication API endpoints."""


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client) -> None:
        """Test health check returns status with services."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Check response structure
        assert "status" in data
        assert "services" in data
        assert isinstance(data["services"], list)
        # PostgreSQL should always be checked
        pg_status = next((s for s in data["services"] if s["name"] == "postgresql"), None)
        assert pg_status is not None
        assert pg_status["status"] == "healthy"

    def test_liveness_check(self, client) -> None:
        """Test liveness probe returns alive status."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    def test_readiness_check(self, client) -> None:
        """Test readiness probe returns database status."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        # Only checks PostgreSQL for readiness
        assert len(data["services"]) == 1
        assert data["services"][0]["name"] == "postgresql"
        assert data["services"][0]["status"] == "healthy"


class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_user(self, client) -> None:
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepassword123",
                "role": "urologist",
                "hospital_id": "HOSP001",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "urologist"
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client) -> None:
        """Test registration fails with duplicate username."""
        user_data = {
            "username": "duplicateuser",
            "email": "first@example.com",
            "password": "securepassword123",
        }
        # First registration
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201

        # Duplicate registration
        user_data["email"] = "second@example.com"
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client) -> None:
        """Test registration fails with duplicate email."""
        user_data = {
            "username": "firstuser",
            "email": "duplicate@example.com",
            "password": "securepassword123",
        }
        # First registration
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201

        # Duplicate registration
        user_data["username"] = "seconduser"
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client) -> None:
        """Test registration fails with invalid email."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser2",
                "email": "invalid-email",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_register_short_password(self, client) -> None:
        """Test registration fails with short password."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser3",
                "email": "testuser3@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client) -> None:
        """Test successful login returns access token."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "securepassword123",
            },
        )

        # Then login
        response = client.post(
            "/api/auth/login",
            data={"username": "loginuser", "password": "securepassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_username(self, client) -> None:
        """Test login fails with wrong username."""
        response = client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "somepassword"},
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_wrong_password(self, client) -> None:
        """Test login fails with wrong password."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "username": "passwordtest",
                "email": "passwordtest@example.com",
                "password": "correctpassword",
            },
        )

        # Try login with wrong password
        response = client.post(
            "/api/auth/login",
            data={"username": "passwordtest", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]


class TestProtectedEndpoint:
    """Tests for authentication flow with protected endpoints."""

    def test_access_with_valid_token(self, client) -> None:
        """Test accessing protected endpoint with valid token."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={
                "username": "protecteduser",
                "email": "protected@example.com",
                "password": "securepassword123",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            data={"username": "protecteduser", "password": "securepassword123"},
        )
        token = login_response.json()["access_token"]

        # Access health endpoint (not protected, but verifies token format)
        response = client.get(
            "/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
