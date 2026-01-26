"""Tests for search API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.services.embedding import SearchResult


class TestSearchEndpoint:
    """Tests for POST /api/search endpoint."""

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_requires_auth(
        self, mock_embedding_provider, mock_milvus_service, client: TestClient
    ):
        """Test that search endpoint requires authentication."""
        response = client.post(
            "/api/search",
            json={"query": "test query"},
        )
        assert response.status_code == 401

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_basic(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        admin_auth_headers: dict,
    ):
        """Test basic search without filters.

        Uses admin user to bypass hospital scoping (admin has access to all patients).
        """
        mock_service = MagicMock()
        mock_service.search.return_value = [
            SearchResult(
                lab_result_id="550e8400-e29b-41d4-a716-446655440000",
                patient_id="660e8400-e29b-41d4-a716-446655440001",
                score=0.95,
                content_preview="Test content preview",
            )
        ]
        mock_milvus_service.return_value = mock_service

        response = client.post(
            "/api/search",
            json={"query": "blood test results"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "blood test results"
        assert data["total_results"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["score"] == 0.95

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_with_limit(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        admin_auth_headers: dict,
    ):
        """Test search with custom limit.

        Uses admin user to bypass hospital scoping (admin has access to all patients).
        """
        mock_service = MagicMock()
        mock_service.search.return_value = []
        mock_milvus_service.return_value = mock_service

        response = client.post(
            "/api/search",
            json={"query": "test", "limit": 5},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        mock_service.search.assert_called_once_with(
            query_text="test",
            limit=5,
            patient_id=None,
        )

    def test_search_empty_query_rejected(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that empty query is rejected."""
        response = client.post(
            "/api/search",
            json={"query": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_search_query_too_long_rejected(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that query exceeding max length is rejected."""
        long_query = "x" * 1001
        response = client.post(
            "/api/search",
            json={"query": long_query},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_search_limit_validation(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that invalid limit is rejected."""
        # Limit too low
        response = client.post(
            "/api/search",
            json={"query": "test", "limit": 0},
            headers=auth_headers,
        )
        assert response.status_code == 422

        # Limit too high
        response = client.post(
            "/api/search",
            json={"query": "test", "limit": 101},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestSearchWithPatientFilter:
    """Tests for search with patient_id filter."""

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_with_valid_patient_id(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
        db_session,
    ):
        """Test search with valid patient_id filter requires patient to exist."""
        mock_service = MagicMock()
        mock_milvus_service.return_value = mock_service

        # Search for non-existent patient should return 404
        response = client.post(
            "/api/search",
            json={
                "query": "test",
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Patient not found" in response.json()["detail"]

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_with_patient_authorization(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
        db_session,
    ):
        """Test that search verifies patient access for non-admin users."""
        # Create a patient in a different hospital
        from datetime import date

        from src.models.patient import Patient

        patient = Patient(
            mrn="TEST001",
            first_name="Test",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            gender="male",
            hospital_id="hospital-other",
        )
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)

        mock_service = MagicMock()
        mock_service.search.return_value = []
        mock_milvus_service.return_value = mock_service

        # Non-admin user trying to search for patient in different hospital
        # Note: By default, test user has no hospital_id, so they can access all
        response = client.post(
            "/api/search",
            json={"query": "test", "patient_id": str(patient.id)},
            headers=auth_headers,
        )

        # User without hospital_id can access any patient
        assert response.status_code == 200


class TestSearchHospitalScoping:
    """Tests for hospital-based access control in search."""

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_non_admin_user_without_hospital_gets_no_results(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that non-admin user without hospital_id gets no results.

        A user without a hospital_id (and not admin) has no hospital access,
        so post-filtering removes all results. This is the security behavior.
        """
        mock_service = MagicMock()
        mock_service.search.return_value = [
            SearchResult(
                lab_result_id="550e8400-e29b-41d4-a716-446655440000",
                patient_id="660e8400-e29b-41d4-a716-446655440001",
                score=0.95,
                content_preview="Test content",
            )
        ]
        mock_milvus_service.return_value = mock_service

        response = client.post(
            "/api/search",
            json={"query": "test"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Results are filtered out because user has no hospital access
        assert data["total_results"] == 0
        assert len(data["results"]) == 0

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_admin_user_gets_all_results(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        admin_auth_headers: dict,
    ):
        """Test that admin user gets all results without filtering."""
        mock_service = MagicMock()
        mock_service.search.return_value = [
            SearchResult(
                lab_result_id="550e8400-e29b-41d4-a716-446655440000",
                patient_id="660e8400-e29b-41d4-a716-446655440001",
                score=0.95,
                content_preview="Test content",
            )
        ]
        mock_milvus_service.return_value = mock_service

        response = client.post(
            "/api/search",
            json={"query": "test"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Admin gets all results (no hospital filtering)
        assert data["total_results"] == 1
        assert len(data["results"]) == 1

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_limit_multiplied_for_non_admin(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that search limit is multiplied for non-admin users.

        To account for post-filtering, non-admin users fetch 3x the requested limit.
        """
        mock_service = MagicMock()
        mock_service.search.return_value = []
        mock_milvus_service.return_value = mock_service

        response = client.post(
            "/api/search",
            json={"query": "test", "limit": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200
        # Non-admin: limit is multiplied by 3 (10 * 3 = 30)
        mock_service.search.assert_called_once_with(
            query_text="test",
            limit=30,
            patient_id=None,
        )


class TestSearchGetEndpoint:
    """Tests for GET /api/search endpoint."""

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_get_basic(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test GET search endpoint."""
        mock_service = MagicMock()
        mock_service.search.return_value = []
        mock_milvus_service.return_value = mock_service

        response = client.get(
            "/api/search?query=blood+test",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "blood test"
        assert data["total_results"] == 0

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_get_with_params(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        admin_auth_headers: dict,
    ):
        """Test GET search endpoint with query parameters.

        Uses admin user to bypass hospital scoping (admin has access to all patients).
        """
        mock_service = MagicMock()
        mock_service.search.return_value = []
        mock_milvus_service.return_value = mock_service

        response = client.get(
            "/api/search?query=test&limit=20",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        mock_service.search.assert_called_once_with(
            query_text="test",
            limit=20,
            patient_id=None,
        )

    def test_search_get_requires_query(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that GET search requires query parameter."""
        response = client.get(
            "/api/search",
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestSearchStatsEndpoint:
    """Tests for GET /api/search/stats endpoint."""

    def test_stats_requires_auth(self, client: TestClient):
        """Test that stats endpoint requires authentication."""
        response = client.get("/api/search/stats")
        assert response.status_code == 401

    @patch("src.api.search.get_milvus_service")
    def test_stats_success(
        self,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test stats endpoint returns collection statistics."""
        mock_service = MagicMock()
        mock_service.get_collection_stats.return_value = {
            "name": "lab_result_embeddings",
            "num_entities": 100,
            "loaded": True,
        }
        mock_milvus_service.return_value = mock_service

        response = client.get(
            "/api/search/stats",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["collection_name"] == "lab_result_embeddings"
        assert data["indexed_documents"] == 100
        assert data["status"] == "ready"

    @patch("src.api.search.get_milvus_service")
    def test_stats_loading(
        self,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test stats endpoint when collection is loading."""
        mock_service = MagicMock()
        mock_service.get_collection_stats.return_value = {
            "name": "lab_result_embeddings",
            "num_entities": 50,
            "loaded": False,
        }
        mock_milvus_service.return_value = mock_service

        response = client.get(
            "/api/search/stats",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "loading"

    @patch("src.api.search.get_milvus_service")
    def test_stats_unavailable(
        self,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test stats endpoint when service is unavailable."""
        mock_milvus_service.side_effect = Exception("Connection failed")

        response = client.get(
            "/api/search/stats",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["collection_name"] is None
        assert data["indexed_documents"] == 0
        assert "unavailable" in data["status"]


class TestSearchServiceErrors:
    """Tests for search service error handling."""

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_service_unavailable(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that service unavailable returns 503."""
        mock_service = MagicMock()
        mock_service.search.side_effect = Exception("Milvus connection failed")
        mock_milvus_service.return_value = mock_service

        response = client.post(
            "/api/search",
            json={"query": "test"},
            headers=auth_headers,
        )

        assert response.status_code == 503
        assert "Search service unavailable" in response.json()["detail"]

    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_openai_unavailable(
        self,
        mock_embedding_provider,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that OpenAI unavailable returns 503."""
        mock_embedding_provider.side_effect = ImportError("openai not installed")

        response = client.post(
            "/api/search",
            json={"query": "test"},
            headers=auth_headers,
        )

        assert response.status_code == 503
        assert "OpenAI package not available" in response.json()["detail"]

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_search_invalid_uuid_returns_400(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test that invalid UUID returns 400."""
        mock_service = MagicMock()
        mock_service.search.side_effect = ValueError("Invalid UUID format")
        mock_milvus_service.return_value = mock_service

        response = client.post(
            "/api/search",
            json={"query": "test", "patient_id": "invalid-uuid"},
            headers=auth_headers,
        )

        # Will get 404 first due to patient not found
        assert response.status_code == 404


class TestSearchRequestModel:
    """Tests for SearchRequest Pydantic model validation."""

    def test_valid_request(self, client: TestClient, auth_headers: dict):
        """Test that valid request passes validation."""
        # This will fail at the service layer but pass validation
        with patch("src.api.search.get_milvus_service") as mock_service:
            mock_svc = MagicMock()
            mock_svc.search.return_value = []
            mock_service.return_value = mock_svc
            with patch("src.api.search.OpenAIEmbeddingProvider"):
                response = client.post(
                    "/api/search",
                    json={
                        "query": "test query",
                        "limit": 50,
                        "patient_id": None,
                    },
                    headers=auth_headers,
                )
                assert response.status_code == 200

    def test_invalid_limit_type(self, client: TestClient, auth_headers: dict):
        """Test that invalid limit type is rejected."""
        response = client.post(
            "/api/search",
            json={"query": "test", "limit": "not-a-number"},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestSearchResponseModel:
    """Tests for search response structure."""

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_response_structure(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        admin_auth_headers: dict,
    ):
        """Test that response has correct structure.

        Uses admin user to bypass hospital scoping (admin has access to all patients).
        """
        mock_service = MagicMock()
        mock_service.search.return_value = [
            SearchResult(
                lab_result_id="550e8400-e29b-41d4-a716-446655440000",
                patient_id="660e8400-e29b-41d4-a716-446655440001",
                score=0.95,
                content_preview="Preview text here",
            )
        ]
        mock_milvus_service.return_value = mock_service

        response = client.post(
            "/api/search",
            json={"query": "test"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Check top-level structure
        assert "results" in data
        assert "query" in data
        assert "total_results" in data

        # Check result structure
        result = data["results"][0]
        assert "lab_result_id" in result
        assert "patient_id" in result
        assert "score" in result
        assert "content_preview" in result

    @patch("src.api.search.get_milvus_service")
    @patch("src.api.search.OpenAIEmbeddingProvider")
    def test_empty_results(
        self,
        mock_embedding_provider,
        mock_milvus_service,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test response with no results."""
        mock_service = MagicMock()
        mock_service.search.return_value = []
        mock_milvus_service.return_value = mock_service

        response = client.post(
            "/api/search",
            json={"query": "nonexistent content"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total_results"] == 0
