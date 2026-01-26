"""Tests for VLMExtractorService."""

import base64
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from src.services.extraction.vlm_extractor import (
    SUPPORTED_IMAGE_TYPES,
    VLMExtractionResult,
    VLMExtractorError,
    VLMExtractorService,
    get_vlm_extractor_service,
)


class TestVLMExtractionResult:
    """Tests for VLMExtractionResult dataclass."""

    def test_vlm_extraction_result_creation(self):
        """Test creating a VLMExtractionResult."""
        result = VLMExtractionResult(
            extracted_data={"lab_values": []},
            raw_response="test response",
            confidence=0.95,
            image_description="Lab result image",
            metadata={"model": "claude-sonnet-4-20250514"},
        )

        assert result.extracted_data == {"lab_values": []}
        assert result.raw_response == "test response"
        assert result.confidence == 0.95
        assert result.image_description == "Lab result image"
        assert result.metadata == {"model": "claude-sonnet-4-20250514"}

    def test_vlm_extraction_result_default_metadata(self):
        """Test VLMExtractionResult with default metadata."""
        result = VLMExtractionResult(
            extracted_data={},
            raw_response="",
            confidence=0.5,
            image_description="",
        )

        assert result.metadata == {}


class TestVLMExtractorServiceInit:
    """Tests for VLMExtractorService initialization."""

    def test_init_with_anthropic_client(self):
        """Test initialization with anthropic client."""
        mock_client = MagicMock()
        service = VLMExtractorService(anthropic_client=mock_client)

        assert service.anthropic_client is mock_client
        assert service.model == "claude-sonnet-4-20250514"
        assert service.hospital_id is None

    def test_init_without_anthropic_client_raises_error(self):
        """Test initialization without anthropic client raises error."""
        with pytest.raises(VLMExtractorError) as exc_info:
            VLMExtractorService(anthropic_client=None)

        assert "Anthropic client is required" in str(exc_info.value)

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        mock_client = MagicMock()
        service = VLMExtractorService(
            anthropic_client=mock_client,
            model="custom-model",
        )

        assert service.model == "custom-model"

    def test_init_with_hospital_id(self):
        """Test initialization with hospital ID."""
        mock_client = MagicMock()
        service = VLMExtractorService(
            anthropic_client=mock_client,
            hospital_id="hospital_001",
        )

        assert service.hospital_id == "hospital_001"


class TestVLMExtractorServiceExtraction:
    """Tests for VLMExtractorService extraction methods."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock anthropic client."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""{
                    "image_description": "Blood test results from lab",
                    "confidence": 0.92,
                    "patient_info": {"name": "John Doe"},
                    "lab_values": [
                        {
                            "test_name": "Hemoglobin",
                            "value": 14.5,
                            "unit": "g/dL",
                            "reference_range": "13.5-17.5",
                            "flag": "Normal"
                        }
                    ]
                }"""
            )
        ]
        mock_client.messages.create.return_value = mock_response
        return mock_client

    @pytest.fixture
    def service(self, mock_anthropic_client):
        """Create a VLMExtractorService with mock client."""
        return VLMExtractorService(anthropic_client=mock_anthropic_client)

    def test_extract_from_bytes_jpeg(self, service, mock_anthropic_client):
        """Test extracting from JPEG image bytes."""
        image_data = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # JPEG magic bytes

        result = service.extract_from_bytes(image_data, mime_type="image/jpeg")

        assert isinstance(result, VLMExtractionResult)
        assert result.confidence == 0.92
        assert result.image_description == "Blood test results from lab"
        assert "lab_values" in result.extracted_data
        assert len(result.extracted_data["lab_values"]) == 1

        # Verify API was called correctly
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_args.kwargs["max_tokens"] == 4096

    def test_extract_from_bytes_png(self, service, mock_anthropic_client):
        """Test extracting from PNG image bytes."""
        image_data = b"\x89PNG\r\n\x1a\n"  # PNG magic bytes

        result = service.extract_from_bytes(image_data, mime_type="image/png")

        assert isinstance(result, VLMExtractionResult)
        assert result.confidence == 0.92

    def test_extract_from_bytes_with_bytesio(self, service, mock_anthropic_client):
        """Test extracting from BytesIO."""
        image_data = BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF")

        result = service.extract_from_bytes(image_data, mime_type="image/jpeg")

        assert isinstance(result, VLMExtractionResult)

    def test_extract_from_file_not_found(self, service):
        """Test extracting from non-existent file."""
        with pytest.raises(VLMExtractorError) as exc_info:
            service.extract_from_file("/nonexistent/file.jpg")

        assert "File not found" in str(exc_info.value)

    def test_extract_from_file_unsupported_type(self, service, tmp_path):
        """Test extracting from unsupported file type."""
        # Create a temp file with unsupported extension
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"text content")

        with pytest.raises(VLMExtractorError) as exc_info:
            service.extract_from_file(test_file)

        assert "Unsupported image type" in str(exc_info.value)

    def test_extract_from_file_success(self, service, mock_anthropic_client, tmp_path):
        """Test successful extraction from file."""
        # Create a temp image file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF test image content")

        result = service.extract_from_file(test_file)

        assert isinstance(result, VLMExtractionResult)
        assert result.confidence == 0.92

    def test_extract_metadata_contains_model(self, service, mock_anthropic_client):
        """Test that metadata contains model info."""
        image_data = b"\xff\xd8\xff\xe0"

        result = service.extract_from_bytes(image_data, mime_type="image/jpeg")

        assert result.metadata["extraction_type"] == "lab_result"
        assert result.metadata["model"] == "claude-sonnet-4-20250514"


class TestVLMExtractorServiceJsonParsing:
    """Tests for JSON parsing in VLM extraction."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock anthropic client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create a VLMExtractorService."""
        return VLMExtractorService(anthropic_client=mock_client)

    def test_parse_json_with_markdown_block(self, service, mock_client):
        """Test parsing JSON wrapped in markdown code block."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""Here is the extracted data:

```json
{
    "image_description": "Lab results",
    "confidence": 0.85,
    "lab_values": []
}
```

Let me know if you need more details."""
            )
        ]
        mock_client.messages.create.return_value = mock_response

        result = service.extract_from_bytes(b"test", mime_type="image/jpeg")

        assert result.confidence == 0.85
        assert result.image_description == "Lab results"

    def test_parse_json_without_markdown_block(self, service, mock_client):
        """Test parsing raw JSON without markdown block."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""{
                    "image_description": "Test",
                    "confidence": 0.75,
                    "lab_values": []
                }"""
            )
        ]
        mock_client.messages.create.return_value = mock_response

        result = service.extract_from_bytes(b"test", mime_type="image/jpeg")

        assert result.confidence == 0.75

    def test_parse_json_failure(self, service, mock_client):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="This is not JSON at all")
        ]
        mock_client.messages.create.return_value = mock_response

        with pytest.raises(VLMExtractorError) as exc_info:
            service.extract_from_bytes(b"test", mime_type="image/jpeg")

        assert "No JSON found" in str(exc_info.value)

    def test_parse_invalid_json_syntax(self, service, mock_client):
        """Test handling of malformed JSON."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"image_description": "test", "confidence": }')
        ]
        mock_client.messages.create.return_value = mock_response

        with pytest.raises(VLMExtractorError) as exc_info:
            service.extract_from_bytes(b"test", mime_type="image/jpeg")

        assert "Failed to parse JSON" in str(exc_info.value)


class TestVLMExtractorServiceConfidence:
    """Tests for confidence score handling."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock anthropic client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create a VLMExtractorService."""
        return VLMExtractorService(anthropic_client=mock_client)

    def test_confidence_clamped_to_max(self, service, mock_client):
        """Test that confidence is clamped to maximum 1.0."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"image_description": "test", "confidence": 1.5, "lab_values": []}'
            )
        ]
        mock_client.messages.create.return_value = mock_response

        result = service.extract_from_bytes(b"test", mime_type="image/jpeg")

        assert result.confidence == 1.0

    def test_confidence_clamped_to_min(self, service, mock_client):
        """Test that confidence is clamped to minimum 0.0."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"image_description": "test", "confidence": -0.5, "lab_values": []}'
            )
        ]
        mock_client.messages.create.return_value = mock_response

        result = service.extract_from_bytes(b"test", mime_type="image/jpeg")

        assert result.confidence == 0.0

    def test_default_confidence(self, service, mock_client):
        """Test default confidence when not provided."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"image_description": "test", "lab_values": []}'
            )
        ]
        mock_client.messages.create.return_value = mock_response

        result = service.extract_from_bytes(b"test", mime_type="image/jpeg")

        assert result.confidence == 0.5


class TestVLMExtractorServiceErrorHandling:
    """Tests for error handling in VLM extraction."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock anthropic client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create a VLMExtractorService."""
        return VLMExtractorService(anthropic_client=mock_client)

    def test_api_error_handling(self, service, mock_client):
        """Test handling of API errors."""
        mock_client.messages.create.side_effect = Exception("API rate limit exceeded")

        with pytest.raises(VLMExtractorError) as exc_info:
            service.extract_from_bytes(b"test", mime_type="image/jpeg")

        assert "Claude API call failed" in str(exc_info.value)
        assert "API rate limit exceeded" in str(exc_info.value)

    def test_unknown_extraction_type(self, service):
        """Test handling of unknown extraction type."""
        with pytest.raises(VLMExtractorError) as exc_info:
            service.extract_from_bytes(
                b"test",
                mime_type="image/jpeg",
                extraction_type="unknown_type",
            )

        assert "Unknown extraction type" in str(exc_info.value)


class TestVLMExtractorServiceFormatForStorage:
    """Tests for format_for_storage method."""

    @pytest.fixture
    def service(self):
        """Create a VLMExtractorService."""
        mock_client = MagicMock()
        return VLMExtractorService(anthropic_client=mock_client)

    def test_format_for_storage(self, service):
        """Test formatting extraction result for database storage."""
        result = VLMExtractionResult(
            extracted_data={
                "lab_values": [
                    {"test_name": "Hemoglobin", "value": 14.5}
                ],
                "patient_info": {"name": "John Doe"},
            },
            raw_response="raw response text",
            confidence=0.92,
            image_description="Blood test results",
            metadata={"model": "claude-sonnet-4-20250514", "extraction_type": "lab_result"},
        )

        storage_format = service.format_for_storage(result)

        assert storage_format["source"] == "vlm"
        assert storage_format["model"] == "claude-sonnet-4-20250514"
        assert storage_format["confidence"] == 0.92
        assert storage_format["image_description"] == "Blood test results"
        assert storage_format["data"]["lab_values"][0]["test_name"] == "Hemoglobin"


class TestSupportedImageTypes:
    """Tests for supported image type constants."""

    def test_jpeg_types(self):
        """Test JPEG MIME type mappings."""
        assert SUPPORTED_IMAGE_TYPES[".jpg"] == "image/jpeg"
        assert SUPPORTED_IMAGE_TYPES[".jpeg"] == "image/jpeg"

    def test_png_type(self):
        """Test PNG MIME type mapping."""
        assert SUPPORTED_IMAGE_TYPES[".png"] == "image/png"

    def test_gif_type(self):
        """Test GIF MIME type mapping."""
        assert SUPPORTED_IMAGE_TYPES[".gif"] == "image/gif"

    def test_webp_type(self):
        """Test WebP MIME type mapping."""
        assert SUPPORTED_IMAGE_TYPES[".webp"] == "image/webp"

    def test_tiff_types(self):
        """Test TIFF MIME type mappings."""
        assert SUPPORTED_IMAGE_TYPES[".tiff"] == "image/tiff"
        assert SUPPORTED_IMAGE_TYPES[".tif"] == "image/tiff"


class TestGetVLMExtractorService:
    """Tests for the factory function."""

    def test_get_vlm_extractor_service_creates_instance(self):
        """Test that factory creates new instance."""
        mock_client = MagicMock()

        service = get_vlm_extractor_service(anthropic_client=mock_client)

        assert isinstance(service, VLMExtractorService)

    def test_get_vlm_extractor_service_creates_new_each_time(self):
        """Test that factory creates new instance each time (not singleton)."""
        mock_client = MagicMock()

        service1 = get_vlm_extractor_service(anthropic_client=mock_client)
        service2 = get_vlm_extractor_service(anthropic_client=mock_client)

        # Unlike PDF extractor, VLM extractor is NOT a singleton
        assert service1 is not service2

    def test_get_vlm_extractor_service_with_hospital_id(self):
        """Test factory with hospital ID."""
        mock_client = MagicMock()

        service = get_vlm_extractor_service(
            anthropic_client=mock_client,
            hospital_id="hospital_001",
        )

        assert service.hospital_id == "hospital_001"

    def test_get_vlm_extractor_service_with_custom_model(self):
        """Test factory with custom model."""
        mock_client = MagicMock()

        service = get_vlm_extractor_service(
            anthropic_client=mock_client,
            model="claude-opus-4-20250514",
        )

        assert service.model == "claude-opus-4-20250514"


class TestVLMExtractorServiceImageEncoding:
    """Tests for image encoding."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock anthropic client."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"image_description": "test", "confidence": 0.9, "lab_values": []}'
            )
        ]
        mock_client.messages.create.return_value = mock_response
        return mock_client

    def test_image_encoded_as_base64(self, mock_client):
        """Test that image is properly base64 encoded."""
        service = VLMExtractorService(anthropic_client=mock_client)
        test_image = b"test image data"

        service.extract_from_bytes(test_image, mime_type="image/jpeg")

        # Get the call arguments
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        image_content = messages[0]["content"][0]

        # Verify base64 encoding
        expected_base64 = base64.b64encode(test_image).decode("utf-8")
        assert image_content["source"]["data"] == expected_base64
        assert image_content["source"]["type"] == "base64"
        assert image_content["source"]["media_type"] == "image/jpeg"
