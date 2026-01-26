"""Tests for upload API endpoints."""

from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.storage import StorageService, get_storage_service


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service."""
    service = MagicMock(spec=StorageService)
    service.upload_file.return_value = "lab-results/test-uuid.pdf"
    service.detect_file_type.return_value = "pdf"
    service.get_presigned_url.return_value = "https://minio/presigned-url"
    service.delete_file.return_value = None
    return service


@pytest.fixture
def client_with_mock_storage(mock_storage_service: MagicMock, client: TestClient):
    """Create a test client with mocked storage service."""
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_service
    yield client
    # Only remove the storage service override, not all overrides (db override is set in conftest.py)
    del app.dependency_overrides[get_storage_service]


@pytest.fixture
def sample_patient(client: TestClient, auth_headers: dict[str, str]) -> dict:
    """Create a sample patient for testing."""
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
    return response.json()


class TestUploadLabResult:
    """Tests for uploading lab results."""

    def test_upload_lab_result_pdf(
        self,
        client_with_mock_storage: TestClient,
        auth_headers: dict[str, str],
        sample_patient: dict,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test uploading a PDF lab result successfully."""
        # Create a test file
        file_content = b"%PDF-1.4 test content"
        files = {"file": ("test_lab.pdf", BytesIO(file_content), "application/pdf")}
        data = {
            "patient_id": sample_patient["id"],
            "title": "Blood Test Results",
            "phase": "post_surgery",
        }

        response = client_with_mock_storage.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["title"] == "Blood Test Results"
        assert result["phase"] == "post_surgery"
        assert result["extraction_status"] == "pending"
        assert result["file_type"] == "pdf"
        assert "id" in result

    def test_upload_lab_result_image(
        self,
        client_with_mock_storage: TestClient,
        auth_headers: dict[str, str],
        sample_patient: dict,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test uploading an image lab result."""
        mock_storage_service.detect_file_type.return_value = "image"
        mock_storage_service.upload_file.return_value = "lab-results/test-uuid.png"

        file_content = b"\x89PNG\r\n\x1a\n test image"
        files = {"file": ("test_scan.png", BytesIO(file_content), "image/png")}
        data = {
            "patient_id": sample_patient["id"],
            "title": "Lab Scan",
            "phase": "pre_surgery",
        }

        response = client_with_mock_storage.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["file_type"] == "image"

    def test_upload_lab_result_with_description(
        self,
        client_with_mock_storage: TestClient,
        auth_headers: dict[str, str],
        sample_patient: dict,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test uploading with optional description."""
        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
        data = {
            "patient_id": sample_patient["id"],
            "title": "Blood Test",
            "phase": "follow_up",
            "description": "Annual checkup results",
        }

        response = client_with_mock_storage.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["description"] == "Annual checkup results"

    def test_upload_lab_result_invalid_file_type(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        sample_patient: dict,
    ) -> None:
        """Test uploading an unsupported file type."""
        files = {"file": ("test.txt", BytesIO(b"text content"), "text/plain")}
        data = {
            "patient_id": sample_patient["id"],
            "title": "Test",
            "phase": "post_surgery",
        }

        response = client.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    def test_upload_lab_result_patient_not_found(
        self,
        client_with_mock_storage: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test uploading for a non-existent patient."""
        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
        data = {
            "patient_id": "00000000-0000-0000-0000-000000000000",
            "title": "Test",
            "phase": "post_surgery",
        }

        response = client_with_mock_storage.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Patient not found" in response.json()["detail"]

    def test_upload_lab_result_unauthenticated(
        self,
        client: TestClient,
    ) -> None:
        """Test uploading without authentication."""
        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
        data = {
            "patient_id": "00000000-0000-0000-0000-000000000000",
            "title": "Test",
            "phase": "post_surgery",
        }

        response = client.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
        )

        assert response.status_code == 401


class TestGetLabResult:
    """Tests for getting lab results."""

    def test_get_lab_result(
        self,
        client_with_mock_storage: TestClient,
        auth_headers: dict[str, str],
        sample_patient: dict,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test getting a lab result by ID."""
        # Upload first
        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
        data = {
            "patient_id": sample_patient["id"],
            "title": "Blood Test",
            "phase": "post_surgery",
        }
        upload_response = client_with_mock_storage.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
            headers=auth_headers,
        )
        lab_result_id = upload_response.json()["id"]

        # Get the lab result
        response = client_with_mock_storage.get(
            f"/api/upload/lab-result/{lab_result_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["id"] == lab_result_id

    def test_get_lab_result_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting a non-existent lab result."""
        response = client.get(
            "/api/upload/lab-result/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestGetDownloadUrl:
    """Tests for getting presigned download URLs."""

    def test_get_download_url(
        self,
        client_with_mock_storage: TestClient,
        auth_headers: dict[str, str],
        sample_patient: dict,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test getting a presigned download URL."""
        # Upload first
        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
        data = {
            "patient_id": sample_patient["id"],
            "title": "Blood Test",
            "phase": "post_surgery",
        }
        upload_response = client_with_mock_storage.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
            headers=auth_headers,
        )
        lab_result_id = upload_response.json()["id"]

        # Get download URL
        response = client_with_mock_storage.get(
            f"/api/upload/lab-result/{lab_result_id}/download-url",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "download_url" in response.json()
        assert response.json()["download_url"] == "https://minio/presigned-url"


class TestReprocessLabResult:
    """Tests for reprocessing lab results."""

    def test_reprocess_lab_result(
        self,
        client_with_mock_storage: TestClient,
        auth_headers: dict[str, str],
        sample_patient: dict,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test triggering reprocessing of a lab result."""
        # Upload first
        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
        data = {
            "patient_id": sample_patient["id"],
            "title": "Blood Test",
            "phase": "post_surgery",
        }
        upload_response = client_with_mock_storage.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
            headers=auth_headers,
        )
        lab_result_id = upload_response.json()["id"]

        # Reprocess
        response = client_with_mock_storage.post(
            f"/api/upload/lab-result/{lab_result_id}/reprocess",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["extraction_status"] == "pending"

    def test_reprocess_lab_result_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test reprocessing a non-existent lab result."""
        response = client.post(
            "/api/upload/lab-result/00000000-0000-0000-0000-000000000000/reprocess",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestDeleteLabResult:
    """Tests for deleting lab results."""

    def test_delete_lab_result(
        self,
        client_with_mock_storage: TestClient,
        auth_headers: dict[str, str],
        sample_patient: dict,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test deleting a lab result."""
        # Upload first
        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
        data = {
            "patient_id": sample_patient["id"],
            "title": "Blood Test",
            "phase": "post_surgery",
        }
        upload_response = client_with_mock_storage.post(
            "/api/upload/lab-result",
            files=files,
            data=data,
            headers=auth_headers,
        )
        lab_result_id = upload_response.json()["id"]

        # Delete
        response = client_with_mock_storage.delete(
            f"/api/upload/lab-result/{lab_result_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify deletion
        get_response = client_with_mock_storage.get(
            f"/api/upload/lab-result/{lab_result_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_lab_result_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test deleting a non-existent lab result."""
        response = client.delete(
            "/api/upload/lab-result/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        assert response.status_code == 404
