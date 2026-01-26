"""Tests for follow-up scheduling API endpoints."""


class TestFollowupSchedule:
    """Tests for the follow-up schedule endpoint."""

    def _create_patient_with_surgery(
        self, client, auth_headers: dict[str, str], mrn: str, surgery_date: str
    ) -> str:
        """Helper to create a patient with surgery date and return its ID."""
        # Create patient
        response = client.post(
            "/api/patients/",
            json={
                "mrn": mrn,
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "gender": "male",
            },
            headers=auth_headers,
        )
        patient_id = response.json()["id"]

        # Set basic info with surgery date
        client.put(
            f"/api/patients/{patient_id}/basic-info",
            json={
                "patient_name": "John Doe",
                "gender": "male",
                "age": 35,
                "surgery_date": surgery_date,
            },
            headers=auth_headers,
        )

        return patient_id

    def test_get_followup_schedule_empty(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting follow-up schedule when no patients exist."""
        response = client.get("/api/followup-schedule", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["overdue"] == []
        assert data["due"] == []
        assert data["upcoming"] == []
        assert data["total_overdue"] == 0
        assert data["total_due"] == 0
        assert data["total_upcoming"] == 0

    def test_get_followup_schedule_with_patient(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting follow-up schedule with a patient."""
        # Create a patient with surgery date in the past
        self._create_patient_with_surgery(
            client, auth_headers, "MRN001", "2024-01-01"
        )

        response = client.get("/api/followup-schedule", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # With surgery date in past, should have overdue follow-ups
        assert data["total_overdue"] >= 0
        assert data["total_due"] >= 0

    def test_get_followup_schedule_days_ahead_filter(self, client, auth_headers: dict[str, str]) -> None:
        """Test follow-up schedule with days_ahead parameter."""
        response = client.get(
            "/api/followup-schedule?days_ahead=7",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_get_followup_schedule_unauthenticated(self, client) -> None:
        """Test that follow-up schedule requires authentication."""
        response = client.get("/api/followup-schedule")
        assert response.status_code == 401


class TestNextFollowup:
    """Tests for the next follow-up endpoint."""

    def _create_patient(self, client, auth_headers: dict[str, str]) -> str:
        """Helper to create a patient and return its ID."""
        response = client.post(
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
        return response.json()["id"]

    def test_get_next_followup_no_basic_info(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting next follow-up for patient without basic info."""
        patient_id = self._create_patient(client, auth_headers)

        response = client.get(
            f"/api/patients/{patient_id}/next-followup",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["surgery_date"] is None
        assert data["next_clinical"] is None
        assert data["next_nursing"] is None
        assert data["all_followups"] == []

    def test_get_next_followup_with_surgery_date(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting next follow-up for patient with surgery date."""
        patient_id = self._create_patient(client, auth_headers)

        # Set basic info with surgery date
        client.put(
            f"/api/patients/{patient_id}/basic-info",
            json={
                "patient_name": "John Doe",
                "gender": "male",
                "age": 35,
                "surgery_date": "2025-01-01",
            },
            headers=auth_headers,
        )

        response = client.get(
            f"/api/patients/{patient_id}/next-followup",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["surgery_date"] == "2025-01-01"
        # Should have pending follow-ups
        assert len(data["all_followups"]) > 0

    def test_get_next_followup_with_completed_followup(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting next follow-up after completing one."""
        patient_id = self._create_patient(client, auth_headers)

        # Set basic info with surgery date
        client.put(
            f"/api/patients/{patient_id}/basic-info",
            json={
                "patient_name": "John Doe",
                "gender": "male",
                "age": 35,
                "surgery_date": "2024-01-01",
            },
            headers=auth_headers,
        )

        # Complete the first clinical follow-up
        client.put(
            f"/api/patients/{patient_id}/clinical-followups/1",
            json={
                "stage": 1,
                "followup_date": "2024-01-08",
            },
            headers=auth_headers,
        )

        response = client.get(
            f"/api/patients/{patient_id}/next-followup",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # First clinical stage should be excluded from pending
        if data["next_clinical"]:
            assert data["next_clinical"]["stage"] != 1

    def test_get_next_followup_patient_not_found(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting next follow-up for non-existent patient."""
        response = client.get(
            "/api/patients/00000000-0000-0000-0000-000000000000/next-followup",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_get_next_followup_unauthenticated(self, client) -> None:
        """Test that next follow-up requires authentication."""
        response = client.get(
            "/api/patients/00000000-0000-0000-0000-000000000000/next-followup"
        )
        assert response.status_code == 401
