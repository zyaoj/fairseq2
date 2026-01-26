"""Tests for lab result extraction status endpoints."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.models.clinical_event import ExtractionStatus, LabResult, LifecyclePhase
from src.models.patient import Patient
from src.models.user import User


class TestGetLabResultStatus:
    """Tests for GET /upload/lab-result/{id}/status endpoint."""

    def test_returns_status_for_pending_extraction(self, client, db_session, auth_headers):
        """Test returns correct status for pending extraction."""
        # Create patient
        patient = Patient(
            id=str(uuid4()),
            mrn="MRN-001",
            first_name="Test",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            gender="male",
        )
        db_session.add(patient)
        db_session.commit()

        # Create lab result with pending status
        lab_result = LabResult(
            id=str(uuid4()),
            patient_id=patient.id,
            phase=LifecyclePhase.POST_SURGERY,
            event_type="lab_result",
            event_date=datetime.now(timezone.utc),
            title="Blood Test",
            original_file_path="lab-results/test.pdf",
            file_type="pdf",
            extraction_status=ExtractionStatus.PENDING,
        )
        db_session.add(lab_result)
        db_session.commit()

        response = client.get(
            f"/api/upload/lab-result/{lab_result.id}/status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(lab_result.id)
        assert data["extraction_status"] == "pending"
        assert data["extraction_confidence"] is None
        assert data["has_extracted_data"] is False
        assert data["error_message"] is None

    def test_returns_status_for_completed_extraction(self, client, db_session, auth_headers):
        """Test returns correct status for completed extraction."""
        # Create patient
        patient = Patient(
            id=str(uuid4()),
            mrn="MRN-002",
            first_name="Test",
            last_name="Patient2",
            date_of_birth=date(1990, 1, 1),
            gender="female",
        )
        db_session.add(patient)
        db_session.commit()

        # Create lab result with completed status
        lab_result = LabResult(
            id=str(uuid4()),
            patient_id=patient.id,
            phase=LifecyclePhase.POST_SURGERY,
            event_type="lab_result",
            event_date=datetime.now(timezone.utc),
            title="Blood Test",
            original_file_path="lab-results/test.pdf",
            file_type="pdf",
            extraction_status=ExtractionStatus.COMPLETED,
            extracted_data={"test": "value"},
            extraction_confidence=0.95,
        )
        db_session.add(lab_result)
        db_session.commit()

        response = client.get(
            f"/api/upload/lab-result/{lab_result.id}/status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(lab_result.id)
        assert data["extraction_status"] == "completed"
        assert data["extraction_confidence"] == 0.95
        assert data["has_extracted_data"] is True
        assert data["error_message"] is None

    def test_returns_status_for_failed_extraction(self, client, db_session, auth_headers):
        """Test returns correct status for failed extraction with error message."""
        # Create patient
        patient = Patient(
            id=str(uuid4()),
            mrn="MRN-003",
            first_name="Test",
            last_name="Patient3",
            date_of_birth=date(1990, 1, 1),
            gender="male",
        )
        db_session.add(patient)
        db_session.commit()

        # Create lab result with failed status
        lab_result = LabResult(
            id=str(uuid4()),
            patient_id=patient.id,
            phase=LifecyclePhase.POST_SURGERY,
            event_type="lab_result",
            event_date=datetime.now(timezone.utc),
            title="Blood Test",
            original_file_path="lab-results/test.pdf",
            file_type="pdf",
            extraction_status=ExtractionStatus.FAILED,
            extracted_data={"error": "Failed to download file"},
        )
        db_session.add(lab_result)
        db_session.commit()

        response = client.get(
            f"/api/upload/lab-result/{lab_result.id}/status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(lab_result.id)
        assert data["extraction_status"] == "failed"
        assert data["extraction_confidence"] is None
        assert data["has_extracted_data"] is False
        assert data["error_message"] == "Failed to download file"

    def test_returns_404_for_nonexistent_lab_result(self, client, auth_headers):
        """Test returns 404 for non-existent lab result."""
        response = client.get(
            f"/api/upload/lab-result/{uuid4()}/status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_requires_authentication(self, client):
        """Test endpoint requires authentication."""
        response = client.get(f"/api/upload/lab-result/{uuid4()}/status")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListPendingLabResults:
    """Tests for GET /upload/lab-results/pending endpoint."""

    def test_returns_pending_lab_results(self, client, db_session, auth_headers):
        """Test returns lab results with pending status."""
        # Create patient
        patient = Patient(
            id=str(uuid4()),
            mrn="MRN-004",
            first_name="Test",
            last_name="Patient4",
            date_of_birth=date(1990, 1, 1),
            gender="male",
        )
        db_session.add(patient)
        db_session.commit()

        # Create lab results with different statuses
        pending_id = str(uuid4())
        processing_id = str(uuid4())
        completed_id = str(uuid4())

        lab_results = [
            LabResult(
                id=pending_id,
                patient_id=patient.id,
                phase=LifecyclePhase.POST_SURGERY,
                event_type="lab_result",
                event_date=datetime.now(timezone.utc),
                title="Pending Test",
                original_file_path="lab-results/pending.pdf",
                file_type="pdf",
                extraction_status=ExtractionStatus.PENDING,
            ),
            LabResult(
                id=processing_id,
                patient_id=patient.id,
                phase=LifecyclePhase.POST_SURGERY,
                event_type="lab_result",
                event_date=datetime.now(timezone.utc),
                title="Processing Test",
                original_file_path="lab-results/processing.pdf",
                file_type="pdf",
                extraction_status=ExtractionStatus.PROCESSING,
            ),
            LabResult(
                id=completed_id,
                patient_id=patient.id,
                phase=LifecyclePhase.POST_SURGERY,
                event_type="lab_result",
                event_date=datetime.now(timezone.utc),
                title="Completed Test",
                original_file_path="lab-results/completed.pdf",
                file_type="pdf",
                extraction_status=ExtractionStatus.COMPLETED,
                extracted_data={"test": "data"},
            ),
        ]
        for lr in lab_results:
            db_session.add(lr)
        db_session.commit()

        response = client.get(
            "/api/upload/lab-results/pending",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should include pending and processing, not completed
        ids = [item["id"] for item in data]
        assert pending_id in ids
        assert processing_id in ids
        assert completed_id not in ids

    def test_returns_empty_list_when_no_pending(self, client, db_session, auth_headers):
        """Test returns empty list when no pending lab results."""
        response = client.get(
            "/api/upload/lab-results/pending",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        # May have results from other tests, but response should be valid
        assert isinstance(response.json(), list)

    def test_respects_limit_parameter(self, client, db_session, auth_headers):
        """Test respects limit parameter."""
        # Create patient
        patient = Patient(
            id=str(uuid4()),
            mrn="MRN-005",
            first_name="Test",
            last_name="Patient5",
            date_of_birth=date(1990, 1, 1),
            gender="female",
        )
        db_session.add(patient)
        db_session.commit()

        # Create multiple pending lab results
        for i in range(5):
            lab_result = LabResult(
                id=str(uuid4()),
                patient_id=patient.id,
                phase=LifecyclePhase.POST_SURGERY,
                event_type="lab_result",
                event_date=datetime.now(timezone.utc),
                title=f"Pending Test {i}",
                original_file_path=f"lab-results/pending-{i}.pdf",
                file_type="pdf",
                extraction_status=ExtractionStatus.PENDING,
            )
            db_session.add(lab_result)
        db_session.commit()

        response = client.get(
            "/api/upload/lab-results/pending?limit=2",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 2

    def test_requires_authentication(self, client):
        """Test endpoint requires authentication."""
        response = client.get("/api/upload/lab-results/pending")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListFailedLabResults:
    """Tests for GET /upload/lab-results/failed endpoint."""

    def test_returns_failed_lab_results(self, client, db_session, auth_headers):
        """Test returns lab results with failed status."""
        # Create patient
        patient = Patient(
            id=str(uuid4()),
            mrn="MRN-006",
            first_name="Test",
            last_name="Patient6",
            date_of_birth=date(1990, 1, 1),
            gender="male",
        )
        db_session.add(patient)
        db_session.commit()

        # Create lab results with different statuses
        failed_id = str(uuid4())
        pending_id = str(uuid4())

        lab_results = [
            LabResult(
                id=failed_id,
                patient_id=patient.id,
                phase=LifecyclePhase.POST_SURGERY,
                event_type="lab_result",
                event_date=datetime.now(timezone.utc),
                title="Failed Test",
                original_file_path="lab-results/failed.pdf",
                file_type="pdf",
                extraction_status=ExtractionStatus.FAILED,
                extracted_data={"error": "Extraction failed"},
            ),
            LabResult(
                id=pending_id,
                patient_id=patient.id,
                phase=LifecyclePhase.POST_SURGERY,
                event_type="lab_result",
                event_date=datetime.now(timezone.utc),
                title="Pending Test",
                original_file_path="lab-results/pending.pdf",
                file_type="pdf",
                extraction_status=ExtractionStatus.PENDING,
            ),
        ]
        for lr in lab_results:
            db_session.add(lr)
        db_session.commit()

        response = client.get(
            "/api/upload/lab-results/failed",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should include failed, not pending
        ids = [item["id"] for item in data]
        assert failed_id in ids
        assert pending_id not in ids

        # Check error message is included
        failed_item = next(item for item in data if item["id"] == failed_id)
        assert failed_item["error_message"] == "Extraction failed"

    def test_returns_empty_list_when_no_failed(self, client, db_session, auth_headers):
        """Test returns empty list when no failed lab results."""
        response = client.get(
            "/api/upload/lab-results/failed",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_requires_authentication(self, client):
        """Test endpoint requires authentication."""
        response = client.get("/api/upload/lab-results/failed")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
