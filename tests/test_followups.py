"""Tests for follow-up API endpoints (clinical and nursing)."""


class TestClinicalFollowups:
    """Tests for clinical follow-up endpoints."""

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

    def test_list_clinical_followups_empty(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing clinical follow-ups when none exist."""
        patient_id = self._create_patient(client, auth_headers)

        response = client.get(
            f"/api/patients/{patient_id}/clinical-followups",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["followups"] == []
        assert data["total_stages"] == 5

    def test_create_clinical_followup(self, client, auth_headers: dict[str, str]) -> None:
        """Test creating a clinical follow-up."""
        patient_id = self._create_patient(client, auth_headers)

        response = client.put(
            f"/api/patients/{patient_id}/clinical-followups/1",
            json={
                "stage": 1,
                "followup_date": "2025-01-20",
                "followup_recurrence": "无复发",
                "followup_imaging": "CT检查结果正常",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == 1
        assert data["followup_date"] == "2025-01-20"
        assert data["followup_recurrence"] == "无复发"

    def test_get_clinical_followup_by_stage(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting a clinical follow-up by stage."""
        patient_id = self._create_patient(client, auth_headers)

        # Create a follow-up first
        client.put(
            f"/api/patients/{patient_id}/clinical-followups/2",
            json={
                "stage": 2,
                "followup_date": "2025-02-15",
                "followup_recurrence": "有复发迹象",
            },
            headers=auth_headers,
        )

        # Get the follow-up
        response = client.get(
            f"/api/patients/{patient_id}/clinical-followups/2",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == 2
        assert data["followup_recurrence"] == "有复发迹象"

    def test_get_clinical_followup_not_found(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting a non-existent clinical follow-up returns null."""
        patient_id = self._create_patient(client, auth_headers)

        response = client.get(
            f"/api/patients/{patient_id}/clinical-followups/1",
            headers=auth_headers,
        )
        # API returns 200 with null for non-existent followup
        assert response.status_code == 200
        assert response.json() is None

    def test_update_clinical_followup(self, client, auth_headers: dict[str, str]) -> None:
        """Test updating an existing clinical follow-up."""
        patient_id = self._create_patient(client, auth_headers)

        # Create a follow-up
        client.put(
            f"/api/patients/{patient_id}/clinical-followups/1",
            json={
                "stage": 1,
                "followup_date": "2025-01-20",
            },
            headers=auth_headers,
        )

        # Update it
        response = client.put(
            f"/api/patients/{patient_id}/clinical-followups/1",
            json={
                "stage": 1,
                "followup_date": "2025-01-21",
                "followup_medication": "抗生素",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["followup_date"] == "2025-01-21"
        assert data["followup_medication"] == "抗生素"

    def test_delete_clinical_followup(self, client, auth_headers: dict[str, str]) -> None:
        """Test deleting a clinical follow-up."""
        patient_id = self._create_patient(client, auth_headers)

        # Create a follow-up
        client.put(
            f"/api/patients/{patient_id}/clinical-followups/1",
            json={
                "stage": 1,
                "followup_date": "2025-01-20",
            },
            headers=auth_headers,
        )

        # Delete it
        response = client.delete(
            f"/api/patients/{patient_id}/clinical-followups/1",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify it's gone (API returns null for non-existent)
        response = client.get(
            f"/api/patients/{patient_id}/clinical-followups/1",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() is None

    def test_invalid_stage(self, client, auth_headers: dict[str, str]) -> None:
        """Test creating follow-up with invalid stage."""
        patient_id = self._create_patient(client, auth_headers)

        # Clinical follow-up only has 5 stages (1-5)
        # Pydantic validation returns 422, not 400
        response = client.put(
            f"/api/patients/{patient_id}/clinical-followups/6",
            json={
                "stage": 6,
                "followup_date": "2025-01-20",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestNursingFollowups:
    """Tests for nursing follow-up endpoints."""

    def _create_patient(self, client, auth_headers: dict[str, str]) -> str:
        """Helper to create a patient and return its ID."""
        response = client.post(
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
        return response.json()["id"]

    def test_list_nursing_followups_empty(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing nursing follow-ups when none exist."""
        patient_id = self._create_patient(client, auth_headers)

        response = client.get(
            f"/api/patients/{patient_id}/nursing-followups",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["followups"] == []
        assert data["total_stages"] == 6

    def test_create_nursing_followup(self, client, auth_headers: dict[str, str]) -> None:
        """Test creating a nursing follow-up."""
        patient_id = self._create_patient(client, auth_headers)

        response = client.put(
            f"/api/patients/{patient_id}/nursing-followups/1",
            json={
                "stage": 1,
                "followup_date": "2025-01-20",
                "nursing_mode": "电话",
                "nursing_diet": "清淡饮食指导",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == 1
        assert data["nursing_mode"] == "电话"

    def test_get_nursing_followup_by_stage(self, client, auth_headers: dict[str, str]) -> None:
        """Test getting a nursing follow-up by stage."""
        patient_id = self._create_patient(client, auth_headers)

        # Create a follow-up first
        client.put(
            f"/api/patients/{patient_id}/nursing-followups/3",
            json={
                "stage": 3,
                "followup_date": "2025-04-15",
                "nursing_mode": "视频",
                "nursing_support": "提供心理支持",
            },
            headers=auth_headers,
        )

        # Get the follow-up
        response = client.get(
            f"/api/patients/{patient_id}/nursing-followups/3",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == 3
        assert data["nursing_support"] == "提供心理支持"

    def test_nursing_followup_six_stages(self, client, auth_headers: dict[str, str]) -> None:
        """Test that nursing follow-ups support 6 stages."""
        patient_id = self._create_patient(client, auth_headers)

        # Nursing follow-up has 6 stages (1-6)
        response = client.put(
            f"/api/patients/{patient_id}/nursing-followups/6",
            json={
                "stage": 6,
                "followup_date": "2026-01-15",
                "nursing_mode": "入户",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["stage"] == 6

    def test_nursing_followup_invalid_stage(self, client, auth_headers: dict[str, str]) -> None:
        """Test that nursing follow-up rejects stage 7."""
        patient_id = self._create_patient(client, auth_headers)

        # Pydantic validation returns 422, not 400
        response = client.put(
            f"/api/patients/{patient_id}/nursing-followups/7",
            json={
                "stage": 7,
                "followup_date": "2026-01-15",
                "nursing_mode": "电话",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_delete_nursing_followup(self, client, auth_headers: dict[str, str]) -> None:
        """Test deleting a nursing follow-up."""
        patient_id = self._create_patient(client, auth_headers)

        # Create a follow-up
        client.put(
            f"/api/patients/{patient_id}/nursing-followups/1",
            json={
                "stage": 1,
                "followup_date": "2025-01-20",
                "nursing_mode": "电话",
            },
            headers=auth_headers,
        )

        # Delete it
        response = client.delete(
            f"/api/patients/{patient_id}/nursing-followups/1",
            headers=auth_headers,
        )
        assert response.status_code == 204


class TestPatientNotFound:
    """Tests for follow-up operations on non-existent patients."""

    def test_clinical_followup_patient_not_found(self, client, auth_headers: dict[str, str]) -> None:
        """Test clinical follow-up on non-existent patient."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/patients/{fake_id}/clinical-followups",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_nursing_followup_patient_not_found(self, client, auth_headers: dict[str, str]) -> None:
        """Test nursing follow-up on non-existent patient."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/patients/{fake_id}/nursing-followups",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_unauthenticated(self, client) -> None:
        """Test follow-up endpoints require authentication."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/patients/{fake_id}/clinical-followups")
        assert response.status_code == 401
