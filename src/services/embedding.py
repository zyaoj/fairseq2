"""Embedding and vector search service using Milvus."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
    connections,
    utility,
)

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Collection configuration
COLLECTION_NAME = "lab_result_embeddings"
EMBEDDING_DIMENSION = 1536  # Default: OpenAI text-embedding-3-small dimension
VOYAGE_EMBEDDING_DIMENSION = 1024  # Voyage AI voyage-3 dimension
INDEX_TYPE = "IVF_FLAT"
METRIC_TYPE = "COSINE"
NLIST = 128  # Number of cluster units for IVF index

# UUID validation pattern (RFC 4122)
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _validate_uuid(value: str, field_name: str) -> str:
    """Validate that a string is a valid UUID.

    Args:
        value: The string to validate
        field_name: Name of the field for error messages

    Returns:
        The validated UUID string

    Raises:
        ValueError: If the value is not a valid UUID
    """
    if not value or not UUID_PATTERN.match(value):
        raise ValueError(f"Invalid UUID format for {field_name}: {value!r}")
    return value


@dataclass
class SearchResult:
    """Result from vector similarity search."""

    lab_result_id: str
    patient_id: str
    score: float
    content_preview: str


@dataclass
class EmbeddingRecord:
    """Record to be stored in Milvus."""

    id: str  # lab_result_id
    patient_id: str
    embedding: list[float]
    content: str  # Text content for preview


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        pass

    @abstractmethod
    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider using text-embedding-3-small."""

    def __init__(self, api_key: str | None = None, model: str = "text-embedding-3-small"):
        """Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name to use
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            ) from e

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = self.client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]


class VoyageMedicalEmbeddingProvider(EmbeddingProvider):
    """Voyage AI embedding provider optimized for medical/healthcare content.

    Voyage AI provides high-quality embeddings with strong performance on
    domain-specific content. The voyage-3 model offers excellent quality
    for medical terminology and clinical text.

    Note: For production use with sensitive medical data, ensure compliance
    with your organization's data handling policies.
    """

    # Voyage AI embedding dimensions by model
    MODEL_DIMENSIONS = {
        "voyage-3": 1024,
        "voyage-3-lite": 512,
        "voyage-3-large": 1024,
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "voyage-3",
    ):
        """Initialize Voyage AI embedding provider.

        Args:
            api_key: Voyage API key (defaults to VOYAGE_API_KEY env var)
            model: Model name to use. Options:
                - "voyage-3": Best quality, 1024 dimensions
                - "voyage-3-lite": Faster, 512 dimensions
                - "voyage-3-large": Same as voyage-3
        """
        try:
            import voyageai
        except ImportError as e:
            raise ImportError(
                "Voyage AI package not installed. Install with: pip install voyageai"
            ) from e

        self.client = voyageai.Client(api_key=api_key)
        self.model = model
        self.dimension = self.MODEL_DIMENSIONS.get(model, 1024)

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        result = self.client.embed(
            texts=[text],
            model=self.model,
            input_type="document",
        )
        return result.embeddings[0]

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        result = self.client.embed(
            texts=texts,
            model=self.model,
            input_type="document",
        )
        return result.embeddings

    def generate_query_embedding(self, query: str) -> list[float]:
        """Generate embedding optimized for search queries.

        Voyage AI supports different input types for documents vs queries,
        which can improve retrieval quality.

        Args:
            query: Search query text

        Returns:
            Embedding vector optimized for query matching
        """
        result = self.client.embed(
            texts=[query],
            model=self.model,
            input_type="query",
        )
        return result.embeddings[0]


class MilvusService:
    """Service for vector operations with Milvus."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        embedding_dimension: int | None = None,
    ):
        """Initialize Milvus service.

        Args:
            host: Milvus host (defaults to config)
            port: Milvus port (defaults to config)
            embedding_provider: Provider for generating embeddings
            embedding_dimension: Dimension of embedding vectors. If not specified,
                auto-detects from provider (if VoyageMedicalEmbeddingProvider) or
                uses default (1536 for OpenAI).
        """
        settings = get_settings()
        self.host = host or settings.milvus_host
        self.port = port or settings.milvus_port
        self.embedding_provider = embedding_provider

        # Auto-detect embedding dimension from provider
        if embedding_dimension is not None:
            self.embedding_dimension = embedding_dimension
        elif embedding_provider and hasattr(embedding_provider, "dimension"):
            self.embedding_dimension = embedding_provider.dimension
        else:
            self.embedding_dimension = EMBEDDING_DIMENSION

        self._connected = False
        self._collection: Collection | None = None

    def connect(self) -> None:
        """Connect to Milvus server."""
        if self._connected:
            return

        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
            )
            self._connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from Milvus server."""
        if self._connected:
            connections.disconnect("default")
            self._connected = False
            logger.info("Disconnected from Milvus")

    def ensure_collection(self) -> Collection:
        """Ensure the collection exists with proper schema.

        Returns:
            The Milvus Collection object
        """
        self.connect()

        if utility.has_collection(COLLECTION_NAME):
            self._collection = Collection(COLLECTION_NAME)
            logger.info(f"Using existing collection: {COLLECTION_NAME}")
        else:
            self._collection = self._create_collection()
            logger.info(f"Created new collection: {COLLECTION_NAME}")

        # Load collection into memory for searching
        self._collection.load()
        return self._collection

    def _create_collection(self) -> Collection:
        """Create the lab result embeddings collection.

        Returns:
            The created Collection object
        """
        # Define schema
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                max_length=36,
                is_primary=True,
                description="Lab result UUID",
            ),
            FieldSchema(
                name="patient_id",
                dtype=DataType.VARCHAR,
                max_length=36,
                description="Patient UUID",
            ),
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="Text content for preview",
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.embedding_dimension,
                description="Embedding vector",
            ),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Lab result embeddings for semantic search",
        )

        collection = Collection(
            name=COLLECTION_NAME,
            schema=schema,
        )

        # Create index for vector field
        index_params = {
            "metric_type": METRIC_TYPE,
            "index_type": INDEX_TYPE,
            "params": {"nlist": NLIST},
        }
        collection.create_index(
            field_name="embedding",
            index_params=index_params,
        )
        logger.info(f"Created index on embedding field with {INDEX_TYPE}")

        return collection

    def insert_embedding(self, record: EmbeddingRecord) -> str:
        """Insert a single embedding record.

        Args:
            record: The embedding record to insert

        Returns:
            The inserted ID
        """
        collection = self.ensure_collection()

        data = [
            [record.id],
            [record.patient_id],
            [record.content[:65535]],  # Truncate if needed
            [record.embedding],
        ]

        collection.insert(data)
        collection.flush()
        logger.debug(f"Inserted embedding for lab_result_id: {record.id}")
        return record.id

    def insert_embeddings(self, records: list[EmbeddingRecord]) -> list[str]:
        """Insert multiple embedding records.

        Args:
            records: List of embedding records to insert

        Returns:
            List of inserted IDs
        """
        if not records:
            return []

        collection = self.ensure_collection()

        data = [
            [r.id for r in records],
            [r.patient_id for r in records],
            [r.content[:65535] for r in records],
            [r.embedding for r in records],
        ]

        collection.insert(data)
        collection.flush()
        logger.debug(f"Inserted {len(records)} embeddings")
        return [r.id for r in records]

    def delete_embedding(self, lab_result_id: str) -> bool:
        """Delete an embedding by lab result ID.

        Args:
            lab_result_id: The lab result UUID

        Returns:
            True if deletion was successful

        Raises:
            ValueError: If lab_result_id is not a valid UUID
        """
        # Validate UUID to prevent injection attacks
        validated_id = _validate_uuid(lab_result_id, "lab_result_id")

        collection = self.ensure_collection()
        expr = f'id == "{validated_id}"'
        collection.delete(expr)
        logger.debug(f"Deleted embedding for lab_result_id: {validated_id}")
        return True

    def search(
        self,
        query_text: str,
        limit: int = 10,
        patient_id: str | None = None,
    ) -> list[SearchResult]:
        """Search for similar lab results using text query.

        Args:
            query_text: The search query text
            limit: Maximum number of results
            patient_id: Optional filter by patient ID

        Returns:
            List of search results
        """
        if not self.embedding_provider:
            raise ValueError("Embedding provider required for text search")

        # Generate query embedding
        query_embedding = self.embedding_provider.generate_embedding(query_text)
        return self.search_by_vector(query_embedding, limit, patient_id)

    def search_by_vector(
        self,
        query_vector: list[float],
        limit: int = 10,
        patient_id: str | None = None,
    ) -> list[SearchResult]:
        """Search for similar lab results using embedding vector.

        Args:
            query_vector: The query embedding vector
            limit: Maximum number of results
            patient_id: Optional filter by patient ID

        Returns:
            List of search results

        Raises:
            ValueError: If patient_id is provided but not a valid UUID
        """
        collection = self.ensure_collection()

        search_params = {
            "metric_type": METRIC_TYPE,
            "params": {"nprobe": 10},
        }

        # Build filter expression with UUID validation
        expr = None
        if patient_id:
            validated_patient_id = _validate_uuid(patient_id, "patient_id")
            expr = f'patient_id == "{validated_patient_id}"'

        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=limit,
            expr=expr,
            output_fields=["id", "patient_id", "content"],
        )

        search_results = []
        for hits in results:
            for hit in hits:
                search_results.append(
                    SearchResult(
                        lab_result_id=hit.entity.get("id"),
                        patient_id=hit.entity.get("patient_id"),
                        score=hit.score,
                        content_preview=hit.entity.get("content", "")[:200],
                    )
                )

        return search_results

    def get_collection_stats(self) -> dict[str, Any]:
        """Get collection statistics.

        Returns:
            Dictionary with collection stats
        """
        collection = self.ensure_collection()
        return {
            "name": COLLECTION_NAME,
            "num_entities": collection.num_entities,
            "loaded": True,
        }


# Singleton instance
_milvus_service: MilvusService | None = None


def get_milvus_service(
    embedding_provider: EmbeddingProvider | None = None,
) -> MilvusService:
    """Get or create MilvusService instance.

    Args:
        embedding_provider: Optional embedding provider

    Returns:
        MilvusService instance
    """
    global _milvus_service
    if _milvus_service is None:
        _milvus_service = MilvusService(embedding_provider=embedding_provider)
    elif embedding_provider and _milvus_service.embedding_provider is None:
        _milvus_service.embedding_provider = embedding_provider
    return _milvus_service


def reset_milvus_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _milvus_service
    if _milvus_service:
        try:
            _milvus_service.disconnect()
        except Exception:
            pass
    _milvus_service = None
