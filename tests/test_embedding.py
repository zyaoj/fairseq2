"""Tests for embedding service."""

from unittest.mock import MagicMock, patch

import pytest

from src.services.embedding import (
    COLLECTION_NAME,
    EMBEDDING_DIMENSION,
    VOYAGE_EMBEDDING_DIMENSION,
    EmbeddingProvider,
    EmbeddingRecord,
    MilvusService,
    OpenAIEmbeddingProvider,
    SearchResult,
    VoyageMedicalEmbeddingProvider,
    _validate_uuid,
    get_milvus_service,
    reset_milvus_service,
)


class TestValidateUUID:
    """Tests for UUID validation function."""

    def test_valid_uuid(self):
        """Test that valid UUIDs are accepted."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = _validate_uuid(valid_uuid, "test_field")
        assert result == valid_uuid

    def test_valid_uuid_uppercase(self):
        """Test that uppercase UUIDs are accepted."""
        valid_uuid = "550E8400-E29B-41D4-A716-446655440000"
        result = _validate_uuid(valid_uuid, "test_field")
        assert result == valid_uuid

    def test_invalid_uuid_empty(self):
        """Test that empty string is rejected."""
        with pytest.raises(ValueError, match="Invalid UUID format for test_field"):
            _validate_uuid("", "test_field")

    def test_invalid_uuid_wrong_format(self):
        """Test that wrong format is rejected."""
        with pytest.raises(ValueError, match="Invalid UUID format for test_field"):
            _validate_uuid("not-a-uuid", "test_field")

    def test_invalid_uuid_too_short(self):
        """Test that short strings are rejected."""
        with pytest.raises(ValueError, match="Invalid UUID format for test_field"):
            _validate_uuid("550e8400-e29b-41d4", "test_field")

    def test_invalid_uuid_sql_injection(self):
        """Test that SQL injection attempts are rejected."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            _validate_uuid("'; DROP TABLE users; --", "patient_id")

    def test_invalid_uuid_with_quotes(self):
        """Test that UUIDs with quotes are rejected."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            _validate_uuid('"550e8400-e29b-41d4-a716-446655440000"', "field")


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating a SearchResult."""
        result = SearchResult(
            lab_result_id="550e8400-e29b-41d4-a716-446655440000",
            patient_id="660e8400-e29b-41d4-a716-446655440001",
            score=0.95,
            content_preview="Test content",
        )
        assert result.lab_result_id == "550e8400-e29b-41d4-a716-446655440000"
        assert result.patient_id == "660e8400-e29b-41d4-a716-446655440001"
        assert result.score == 0.95
        assert result.content_preview == "Test content"


class TestEmbeddingRecord:
    """Tests for EmbeddingRecord dataclass."""

    def test_create_embedding_record(self):
        """Test creating an EmbeddingRecord."""
        embedding = [0.1] * 1536
        record = EmbeddingRecord(
            id="550e8400-e29b-41d4-a716-446655440000",
            patient_id="660e8400-e29b-41d4-a716-446655440001",
            embedding=embedding,
            content="Test lab result content",
        )
        assert record.id == "550e8400-e29b-41d4-a716-446655440000"
        assert record.patient_id == "660e8400-e29b-41d4-a716-446655440001"
        assert len(record.embedding) == 1536
        assert record.content == "Test lab result content"


class TestOpenAIEmbeddingProvider:
    """Tests for OpenAI embedding provider."""

    @patch("openai.OpenAI")
    def test_init_default_model(self, mock_openai_class):
        """Test initialization with default model."""
        provider = OpenAIEmbeddingProvider()
        assert provider.model == "text-embedding-3-small"
        mock_openai_class.assert_called_once_with(api_key=None)

    @patch("openai.OpenAI")
    def test_init_custom_model(self, mock_openai_class):
        """Test initialization with custom model."""
        provider = OpenAIEmbeddingProvider(model="text-embedding-3-large")
        assert provider.model == "text-embedding-3-large"

    @patch("openai.OpenAI")
    def test_init_with_api_key(self, mock_openai_class):
        """Test initialization with API key."""
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        mock_openai_class.assert_called_once_with(api_key="test-key")

    @patch("openai.OpenAI")
    def test_generate_embedding(self, mock_openai_class):
        """Test generating a single embedding."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider()
        result = provider.generate_embedding("test text")

        assert len(result) == 1536
        mock_client.embeddings.create.assert_called_once_with(
            input="test text", model="text-embedding-3-small"
        )

    @patch("openai.OpenAI")
    def test_generate_embeddings_batch(self, mock_openai_class):
        """Test generating embeddings for multiple texts."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider()
        result = provider.generate_embeddings(["text1", "text2"])

        assert len(result) == 2
        mock_client.embeddings.create.assert_called_once()


class TestVoyageMedicalEmbeddingProvider:
    """Tests for Voyage AI medical embedding provider."""

    @patch.dict("sys.modules", {"voyageai": MagicMock()})
    def test_init_default_model(self):
        """Test initialization with default model."""
        import sys
        mock_voyageai = sys.modules["voyageai"]
        mock_client = MagicMock()
        mock_voyageai.Client.return_value = mock_client

        provider = VoyageMedicalEmbeddingProvider()
        assert provider.model == "voyage-3"
        assert provider.dimension == 1024

    @patch.dict("sys.modules", {"voyageai": MagicMock()})
    def test_init_lite_model(self):
        """Test initialization with lite model."""
        provider = VoyageMedicalEmbeddingProvider(model="voyage-3-lite")
        assert provider.model == "voyage-3-lite"
        assert provider.dimension == 512

    @patch.dict("sys.modules", {"voyageai": MagicMock()})
    def test_generate_embedding(self):
        """Test generating a single embedding."""
        import sys
        mock_voyageai = sys.modules["voyageai"]
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_client.embed.return_value = mock_result
        mock_voyageai.Client.return_value = mock_client

        provider = VoyageMedicalEmbeddingProvider()
        result = provider.generate_embedding("test medical text")

        assert len(result) == 1024
        mock_client.embed.assert_called_once_with(
            texts=["test medical text"],
            model="voyage-3",
            input_type="document",
        )

    @patch.dict("sys.modules", {"voyageai": MagicMock()})
    def test_generate_embeddings_batch(self):
        """Test generating embeddings for multiple texts."""
        import sys
        mock_voyageai = sys.modules["voyageai"]
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024, [0.2] * 1024]
        mock_client.embed.return_value = mock_result
        mock_voyageai.Client.return_value = mock_client

        provider = VoyageMedicalEmbeddingProvider()
        result = provider.generate_embeddings(["text1", "text2"])

        assert len(result) == 2

    @patch.dict("sys.modules", {"voyageai": MagicMock()})
    def test_generate_embeddings_empty_list(self):
        """Test generating embeddings for empty list returns empty."""
        provider = VoyageMedicalEmbeddingProvider()
        result = provider.generate_embeddings([])
        assert result == []

    @patch.dict("sys.modules", {"voyageai": MagicMock()})
    def test_generate_query_embedding(self):
        """Test generating query-optimized embedding."""
        import sys
        mock_voyageai = sys.modules["voyageai"]
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_client.embed.return_value = mock_result
        mock_voyageai.Client.return_value = mock_client

        provider = VoyageMedicalEmbeddingProvider()
        result = provider.generate_query_embedding("search query")

        assert len(result) == 1024
        mock_client.embed.assert_called_once_with(
            texts=["search query"],
            model="voyage-3",
            input_type="query",
        )


class TestMilvusService:
    """Tests for MilvusService."""

    def test_init_default_dimension(self):
        """Test initialization with default embedding dimension."""
        service = MilvusService()
        assert service.embedding_dimension == EMBEDDING_DIMENSION

    def test_init_custom_dimension(self):
        """Test initialization with custom embedding dimension."""
        service = MilvusService(embedding_dimension=768)
        assert service.embedding_dimension == 768

    @patch.dict("sys.modules", {"voyageai": MagicMock()})
    def test_init_auto_detect_voyage_dimension(self):
        """Test auto-detection of embedding dimension from Voyage provider."""
        provider = VoyageMedicalEmbeddingProvider()
        service = MilvusService(embedding_provider=provider)
        assert service.embedding_dimension == 1024

    def test_init_custom_host_port(self):
        """Test initialization with custom host and port."""
        service = MilvusService(host="custom-host", port=12345)
        assert service.host == "custom-host"
        assert service.port == 12345

    @patch("src.services.embedding.connections")
    def test_connect(self, mock_connections):
        """Test connecting to Milvus."""
        service = MilvusService()
        service.connect()

        mock_connections.connect.assert_called_once_with(
            alias="default",
            host="localhost",
            port=19530,
        )
        assert service._connected is True

    @patch("src.services.embedding.connections")
    def test_connect_already_connected(self, mock_connections):
        """Test connecting when already connected does nothing."""
        service = MilvusService()
        service._connected = True
        service.connect()

        mock_connections.connect.assert_not_called()

    @patch("src.services.embedding.connections")
    def test_disconnect(self, mock_connections):
        """Test disconnecting from Milvus."""
        service = MilvusService()
        service._connected = True
        service.disconnect()

        mock_connections.disconnect.assert_called_once_with("default")
        assert service._connected is False

    @patch("src.services.embedding.connections")
    def test_disconnect_when_not_connected(self, mock_connections):
        """Test disconnecting when not connected does nothing."""
        service = MilvusService()
        service._connected = False
        service.disconnect()

        mock_connections.disconnect.assert_not_called()

    @patch("src.services.embedding.Collection")
    @patch("src.services.embedding.utility")
    @patch("src.services.embedding.connections")
    def test_ensure_collection_existing(self, mock_connections, mock_utility, mock_collection):
        """Test ensure_collection with existing collection."""
        mock_utility.has_collection.return_value = True
        mock_coll_instance = MagicMock()
        mock_collection.return_value = mock_coll_instance

        service = MilvusService()
        result = service.ensure_collection()

        mock_utility.has_collection.assert_called_once_with(COLLECTION_NAME)
        mock_collection.assert_called_once_with(COLLECTION_NAME)
        mock_coll_instance.load.assert_called_once()
        assert result == mock_coll_instance

    @patch("src.services.embedding.Collection")
    @patch("src.services.embedding.CollectionSchema")
    @patch("src.services.embedding.FieldSchema")
    @patch("src.services.embedding.utility")
    @patch("src.services.embedding.connections")
    def test_ensure_collection_creates_new(
        self, mock_connections, mock_utility, mock_field_schema, mock_coll_schema, mock_collection
    ):
        """Test ensure_collection creates new collection when it doesn't exist."""
        mock_utility.has_collection.return_value = False
        mock_coll_instance = MagicMock()
        mock_collection.return_value = mock_coll_instance

        service = MilvusService()
        result = service.ensure_collection()

        mock_utility.has_collection.assert_called_once_with(COLLECTION_NAME)
        # Should call Collection with name and schema
        assert mock_collection.call_count >= 1
        mock_coll_instance.load.assert_called_once()

    def test_search_without_provider_raises(self):
        """Test that search without embedding provider raises error."""
        service = MilvusService()

        with pytest.raises(ValueError, match="Embedding provider required"):
            service.search("test query")

    @patch("src.services.embedding.Collection")
    @patch("src.services.embedding.utility")
    @patch("src.services.embedding.connections")
    def test_search_by_vector_with_valid_patient_id(
        self, mock_connections, mock_utility, mock_collection
    ):
        """Test search_by_vector with valid patient_id filter."""
        mock_utility.has_collection.return_value = True
        mock_coll_instance = MagicMock()
        mock_collection.return_value = mock_coll_instance

        # Mock search results
        mock_hit = MagicMock()
        mock_hit.entity.get.side_effect = lambda key, default=None: {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "patient_id": "660e8400-e29b-41d4-a716-446655440001",
            "content": "Test content",
        }.get(key, default)
        mock_hit.score = 0.95
        mock_coll_instance.search.return_value = [[mock_hit]]

        service = MilvusService()
        query_vector = [0.1] * 1536
        results = service.search_by_vector(
            query_vector,
            patient_id="660e8400-e29b-41d4-a716-446655440001",
        )

        assert len(results) == 1
        assert results[0].score == 0.95
        # Verify the filter expression uses the validated UUID
        call_args = mock_coll_instance.search.call_args
        assert 'patient_id == "660e8400-e29b-41d4-a716-446655440001"' in str(call_args)

    @patch("src.services.embedding.Collection")
    @patch("src.services.embedding.utility")
    @patch("src.services.embedding.connections")
    def test_search_by_vector_with_invalid_patient_id_raises(
        self, mock_connections, mock_utility, mock_collection
    ):
        """Test search_by_vector with invalid patient_id raises error."""
        mock_utility.has_collection.return_value = True
        mock_coll_instance = MagicMock()
        mock_collection.return_value = mock_coll_instance

        service = MilvusService()
        query_vector = [0.1] * 1536

        with pytest.raises(ValueError, match="Invalid UUID format for patient_id"):
            service.search_by_vector(query_vector, patient_id="invalid-id")

    @patch("src.services.embedding.Collection")
    @patch("src.services.embedding.utility")
    @patch("src.services.embedding.connections")
    def test_delete_embedding_with_invalid_id_raises(
        self, mock_connections, mock_utility, mock_collection
    ):
        """Test delete_embedding with invalid lab_result_id raises error."""
        mock_utility.has_collection.return_value = True
        mock_coll_instance = MagicMock()
        mock_collection.return_value = mock_coll_instance

        service = MilvusService()

        with pytest.raises(ValueError, match="Invalid UUID format for lab_result_id"):
            service.delete_embedding("'; DROP TABLE embeddings; --")

    @patch("src.services.embedding.Collection")
    @patch("src.services.embedding.utility")
    @patch("src.services.embedding.connections")
    def test_delete_embedding_with_valid_id(
        self, mock_connections, mock_utility, mock_collection
    ):
        """Test delete_embedding with valid lab_result_id succeeds."""
        mock_utility.has_collection.return_value = True
        mock_coll_instance = MagicMock()
        mock_collection.return_value = mock_coll_instance

        service = MilvusService()
        result = service.delete_embedding("550e8400-e29b-41d4-a716-446655440000")

        assert result is True
        mock_coll_instance.delete.assert_called_once()


class TestMilvusServiceSingleton:
    """Tests for MilvusService singleton pattern."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_milvus_service()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_milvus_service()

    def test_get_milvus_service_creates_singleton(self):
        """Test that get_milvus_service creates a singleton instance."""
        service1 = get_milvus_service()
        service2 = get_milvus_service()
        assert service1 is service2

    def test_get_milvus_service_with_provider(self):
        """Test that get_milvus_service accepts embedding provider."""
        mock_provider = MagicMock(spec=EmbeddingProvider)
        service = get_milvus_service(embedding_provider=mock_provider)
        assert service.embedding_provider is mock_provider

    def test_get_milvus_service_updates_provider(self):
        """Test that provider can be set on existing singleton."""
        # First call without provider
        service1 = get_milvus_service()
        assert service1.embedding_provider is None

        # Second call with provider
        mock_provider = MagicMock(spec=EmbeddingProvider)
        service2 = get_milvus_service(embedding_provider=mock_provider)

        assert service1 is service2
        assert service2.embedding_provider is mock_provider

    def test_reset_milvus_service(self):
        """Test that reset creates fresh instance."""
        service1 = get_milvus_service()
        reset_milvus_service()
        service2 = get_milvus_service()

        assert service1 is not service2


class TestConstants:
    """Tests for module constants."""

    def test_collection_name(self):
        """Test collection name constant."""
        assert COLLECTION_NAME == "lab_result_embeddings"

    def test_embedding_dimension(self):
        """Test default embedding dimension (OpenAI)."""
        assert EMBEDDING_DIMENSION == 1536

    def test_voyage_embedding_dimension(self):
        """Test Voyage embedding dimension."""
        assert VOYAGE_EMBEDDING_DIMENSION == 1024
