"""Tests for patient API endpoints."""


class TestCreatePatient:
    """Tests for creating patients."""

    def test_create_patient(self, client, auth_headers: dict[str, str]) -> None:
        """Test creating a patient successfully."""
        response = client.post(
            "/api/patients/",
            json={
                "mrn": "MRN001",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "gender": "male",
                "hospital_id": "HOSP001",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["mrn"] == "MRN001"
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert "id" in data
        assert "created_at" in data

    def test_create_patient_duplicate_mrn(self, client, auth_headers: dict[str, str]) -> None:
        """Test creating patient with duplicate MRN fails."""
        patient_data = {
            "mrn": "MRN001",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "gender": "male",
        }
        # First patient
        response = client.post("/api/patients/", json=patient_data, headers=auth_headers)
        assert response.status_code == 201

        # Duplicate MRN
        patient_data["first_name"] = "Jane"
        response = client.post("/api/patients/", json=patient_data, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_patient_unauthenticated(self, client) -> None:
        """Test creating patient without authentication fails."""
        response = client.post(
            "/api/patients/",
            json={
                "mrn": "MRN001",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "gender": "male",
            },
        )
        assert response.status_code == 401


class TestListPatients:
    """Tests for listing patients."""

    def test_list_patients_empty(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing patients when none exist."""
        response = client.get("/api/patients/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_patients(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing patients."""
        # Create two patients
        for i in range(2):
            client.post(
                "/api/patients/",
                json={
                    "mrn": f"MRN00{i}",
                    "first_name": f"Patient{i}",
                    "last_name": "Test",
                    "date_of_birth": "1990-01-15",
                    "gender": "male",
                },
                headers=auth_headers,
            )

        response = client.get("/api/patients/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_patients_with_search(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing patients with search filter."""
        # Create patients
        client.post(
            "/api/patients/",
            json={
                "mrn": "MRN001",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "gender": "male",
            },
            headers=auth_headers,
        )
        client.post(
            "/api/patients/",
            json={
                "mrn": "MRN002",
                "first_name": "Jane",
                "last_name": "Smith",
                "date_of_birth": "1985-06-20",
                "gender": "female",
            },
            headers=auth_headers,
        )

        # Search by name
        response = client.get("/api/patients/?search=John", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["first_name"] == "John"

    def test_list_patients_pagination(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing patients with pagination."""
        # Create 5 patients
        for i in range(5):
            client.post(
                "/api/patients/",
                json={
                    "mrn": f"MRN00{i}",
                    "first_name": f"Patient{i}",
                    "last_name": "Test",
                    "date_of_birth": "1990-01-15",
                    "gender": "male",
                },
                headers=auth_headers,
            )

        # Get first 2
        response = client.get("/api/patients/?limit=2", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Skip first 2, get next 2
        response = client.get("/api/patients/?skip=2&limit=2", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestGetPatient:
    """Tests for getting a single patient."""

    def test_get_patient(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting a patient by ID."""
        # Create patient
        create_response = client.post(
            "/api/patients/",
            json={
                "mrn": "MRN001",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "gender": "male",
            },
            headers=auth_headers,
        )
        patient_id = create_response.json()["id"]

        # Get patient
        response = client.get(f"/api/patients/{patient_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == patient_id
        assert data["mrn"] == "MRN001"

    def test_get_patient_not_found(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting a non-existent patient."""
        response = client.get(
            "/api/patients/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdatePatient:
    """Tests for updating patients."""

    def test_update_patient(self, client, auth_headers: dict[str, str]) -> None:
        """Test updating a patient."""
        # Create patient
        create_response = client.post(
            "/api/patients/",
            json={
                "mrn": "MRN001",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "gender": "male",
            },
            headers=auth_headers,
        )
        patient_id = create_response.json()["id"]

        # Update patient
        response = client.patch(
            f"/api/patients/{patient_id}",
            json={"first_name": "Johnny", "hospital_id": "HOSP001"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Johnny"
        assert data["hospital_id"] == "HOSP001"
        assert data["last_name"] == "Doe"  # Unchanged

    def test_update_patient_not_found(self, client, auth_headers: dict[str, str]) -> None:
        """Test updating a non-existent patient."""
        response = client.patch(
            "/api/patients/00000000-0000-0000-0000-000000000000",
            json={"first_name": "Johnny"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeletePatient:
    """Tests for deleting patients."""

    def test_delete_patient(self, client, auth_headers: dict[str, str]) -> None:
        """Test deleting a patient."""
        # Create patient
        create_response = client.post(
            "/api/patients/",
            json={
                "mrn": "MRN001",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "gender": "male",
            },
            headers=auth_headers,
        )
        patient_id = create_response.json()["id"]

        # Delete patient
        response = client.delete(f"/api/patients/{patient_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f"/api/patients/{patient_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_patient_not_found(self, client, auth_headers: dict[str, str]) -> None:
        """Test deleting a non-existent patient."""
        response = client.delete(
            "/api/patients/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404
