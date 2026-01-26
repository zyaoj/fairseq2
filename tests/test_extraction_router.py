"""Tests for extraction router service."""

import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.extraction.extraction_router import (
    ExtractionRouterError,
    ExtractionRouterService,
    ExtractionRouteResult,
    get_extraction_router_service,
)
from src.services.extraction.pdf_extractor import PDFExtractionResult
from src.services.extraction.vlm_extractor import VLMExtractionResult


class TestExtractionRouteResult:
    """Tests for the ExtractionRouteResult dataclass."""

    def test_dataclass_creation(self):
        """Test creating an ExtractionRouteResult."""
        result = ExtractionRouteResult(
            file_type="pdf",
            extractor_used="pdf",
            extracted_data={"text": "test"},
            raw_content="raw text",
            confidence=0.95,
            is_text_based=True,
            metadata={"key": "value"},
        )

        assert result.file_type == "pdf"
        assert result.extractor_used == "pdf"
        assert result.extracted_data == {"text": "test"}
        assert result.raw_content == "raw text"
        assert result.confidence == 0.95
        assert result.is_text_based is True
        assert result.image_description is None
        assert result.metadata == {"key": "value"}

    def test_dataclass_with_image_description(self):
        """Test creating result with image description."""
        result = ExtractionRouteResult(
            file_type="image",
            extractor_used="vlm",
            extracted_data={"lab_values": []},
            raw_content="{}",
            confidence=0.8,
            image_description="A lab result image showing blood test values",
        )

        assert result.file_type == "image"
        assert result.extractor_used == "vlm"
        assert result.image_description == "A lab result image showing blood test values"

    def test_default_values(self):
        """Test default values for optional fields."""
        result = ExtractionRouteResult(
            file_type="pdf",
            extractor_used="pdf",
            extracted_data={},
            raw_content="",
            confidence=0.5,
        )

        assert result.is_text_based is None
        assert result.image_description is None
        assert result.metadata == {}


class TestExtractionRouterServiceInit:
    """Tests for ExtractionRouterService initialization."""

    def test_init_without_client(self):
        """Test initialization without Anthropic client."""
        router = ExtractionRouterService()

        assert router.anthropic_client is None
        assert router.vlm_extractor is None
        assert router.pdf_extractor is not None

    def test_init_with_anthropic_client(self):
        """Test initialization with Anthropic client."""
        mock_client = MagicMock()
        router = ExtractionRouterService(anthropic_client=mock_client)

        assert router.anthropic_client == mock_client
        assert router.vlm_extractor is not None

    def test_init_with_custom_extractors(self):
        """Test initialization with custom extractors."""
        mock_pdf_extractor = MagicMock()
        mock_vlm_extractor = MagicMock()

        router = ExtractionRouterService(
            pdf_extractor=mock_pdf_extractor,
            vlm_extractor=mock_vlm_extractor,
        )

        assert router.pdf_extractor == mock_pdf_extractor
        assert router.vlm_extractor == mock_vlm_extractor

    def test_init_with_hospital_id(self):
        """Test initialization with hospital ID."""
        router = ExtractionRouterService(hospital_id="hospital_001")

        assert router.hospital_id == "hospital_001"


class TestFileTypeDetection:
    """Tests for file type detection."""

    def test_detect_pdf(self):
        """Test PDF detection."""
        router = ExtractionRouterService()

        assert router._detect_file_type(".pdf") == "pdf"
        assert router._detect_file_type(".PDF") == "pdf"
        assert router._detect_file_type("pdf") == "pdf"

    def test_detect_images(self):
        """Test image detection."""
        router = ExtractionRouterService()

        for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"]:
            assert router._detect_file_type(ext) == "image"
            assert router._detect_file_type(ext.upper()) == "image"

    def test_detect_docx(self):
        """Test Word document detection."""
        router = ExtractionRouterService()

        assert router._detect_file_type(".docx") == "docx"
        assert router._detect_file_type(".doc") == "docx"

    def test_detect_unknown(self):
        """Test unknown file type detection."""
        router = ExtractionRouterService()

        assert router._detect_file_type(".txt") == "unknown"
        assert router._detect_file_type(".csv") == "unknown"
        assert router._detect_file_type(".xyz") == "unknown"


class TestPDFExtraction:
    """Tests for PDF extraction routing."""

    def test_extract_text_based_pdf(self):
        """Test extraction of text-based PDF."""
        mock_pdf_extractor = MagicMock()
        mock_pdf_result = PDFExtractionResult(
            is_text_based=True,
            text_content="Lab Results\nGlucose: 100 mg/dL",
            pages=["Lab Results\nGlucose: 100 mg/dL"],
            tables=[[["Test", "Value"], ["Glucose", "100"]]],
            page_count=1,
            has_images=False,
            confidence=0.9,
            metadata={"title": "Lab Report"},
        )
        mock_pdf_extractor.extract_from_bytes.return_value = mock_pdf_result

        router = ExtractionRouterService(pdf_extractor=mock_pdf_extractor)

        result = router._extract_pdf(b"pdf content", "lab_result")

        assert result.file_type == "pdf"
        assert result.extractor_used == "pdf"
        assert result.confidence == 0.9
        assert result.is_text_based is True
        assert "text_content" in result.extracted_data
        assert "tables" in result.extracted_data

    def test_extract_image_based_pdf_without_vlm(self):
        """Test extraction of image-based PDF without VLM extractor."""
        mock_pdf_extractor = MagicMock()
        mock_pdf_result = PDFExtractionResult(
            is_text_based=False,
            text_content="",
            pages=[""],
            tables=[],
            page_count=1,
            has_images=True,
            confidence=0.0,
            metadata={},
        )
        mock_pdf_extractor.extract_from_bytes.return_value = mock_pdf_result

        router = ExtractionRouterService(pdf_extractor=mock_pdf_extractor)

        with pytest.raises(ExtractionRouterError) as exc_info:
            router._extract_pdf(b"pdf content", "lab_result")

        assert "PDF contains images only" in str(exc_info.value)

    def test_pdf_extraction_error(self):
        """Test PDF extraction error handling."""
        mock_pdf_extractor = MagicMock()
        mock_pdf_extractor.extract_from_bytes.side_effect = Exception("PDF error")

        router = ExtractionRouterService(pdf_extractor=mock_pdf_extractor)

        with pytest.raises(ExtractionRouterError) as exc_info:
            router._extract_pdf(b"pdf content", "lab_result")

        assert "PDF extraction failed" in str(exc_info.value)


class TestImageExtraction:
    """Tests for image extraction routing."""

    def test_extract_image_success(self):
        """Test successful image extraction."""
        mock_vlm_extractor = MagicMock()
        mock_vlm_result = VLMExtractionResult(
            extracted_data={"lab_values": [{"test": "Glucose", "value": 100}]},
            raw_response='{"lab_values": []}',
            confidence=0.95,
            image_description="A blood test result showing glucose level",
            metadata={"model": "claude-sonnet-4-20250514"},
        )
        mock_vlm_extractor.extract_from_bytes.return_value = mock_vlm_result

        router = ExtractionRouterService(vlm_extractor=mock_vlm_extractor)

        result = router._extract_image(b"image content", ".jpg", "lab_result")

        assert result.file_type == "image"
        assert result.extractor_used == "vlm"
        assert result.confidence == 0.95
        assert result.is_text_based is False
        assert result.image_description == "A blood test result showing glucose level"

    def test_extract_image_without_vlm(self):
        """Test image extraction without VLM extractor."""
        router = ExtractionRouterService()  # No anthropic_client

        with pytest.raises(ExtractionRouterError) as exc_info:
            router._extract_image(b"image content", ".jpg", "lab_result")

        assert "VLM extractor not available" in str(exc_info.value)

    def test_extract_unsupported_image_type(self):
        """Test extraction with unsupported image type."""
        mock_vlm_extractor = MagicMock()
        router = ExtractionRouterService(vlm_extractor=mock_vlm_extractor)

        with pytest.raises(ExtractionRouterError) as exc_info:
            router._extract_image(b"image content", ".xyz", "lab_result")

        assert "Unsupported image type" in str(exc_info.value)

    def test_image_extraction_error(self):
        """Test image extraction error handling."""
        mock_vlm_extractor = MagicMock()
        mock_vlm_extractor.extract_from_bytes.side_effect = Exception("VLM error")

        router = ExtractionRouterService(vlm_extractor=mock_vlm_extractor)

        with pytest.raises(ExtractionRouterError) as exc_info:
            router._extract_image(b"image content", ".jpg", "lab_result")

        assert "Image extraction failed" in str(exc_info.value)


class TestExtractFromBytes:
    """Tests for extract_from_bytes method."""

    def test_extract_pdf_from_bytes(self):
        """Test extracting PDF from bytes."""
        mock_pdf_extractor = MagicMock()
        mock_pdf_result = PDFExtractionResult(
            is_text_based=True,
            text_content="Test content",
            pages=["Test content"],
            tables=[],
            page_count=1,
            has_images=False,
            confidence=0.85,
            metadata={},
        )
        mock_pdf_extractor.extract_from_bytes.return_value = mock_pdf_result

        router = ExtractionRouterService(pdf_extractor=mock_pdf_extractor)

        result = router.extract_from_bytes(b"pdf content", "test.pdf")

        assert result.file_type == "pdf"
        assert result.extractor_used == "pdf"

    def test_extract_image_from_bytes(self):
        """Test extracting image from bytes."""
        mock_vlm_extractor = MagicMock()
        mock_vlm_result = VLMExtractionResult(
            extracted_data={},
            raw_response="{}",
            confidence=0.9,
            image_description="Test image",
            metadata={},
        )
        mock_vlm_extractor.extract_from_bytes.return_value = mock_vlm_result

        router = ExtractionRouterService(vlm_extractor=mock_vlm_extractor)

        result = router.extract_from_bytes(b"image content", "test.jpg")

        assert result.file_type == "image"
        assert result.extractor_used == "vlm"

    def test_extract_from_bytesio(self):
        """Test extracting from BytesIO."""
        mock_pdf_extractor = MagicMock()
        mock_pdf_result = PDFExtractionResult(
            is_text_based=True,
            text_content="Test",
            pages=["Test"],
            tables=[],
            page_count=1,
            has_images=False,
            confidence=0.9,
            metadata={},
        )
        mock_pdf_extractor.extract_from_bytes.return_value = mock_pdf_result

        router = ExtractionRouterService(pdf_extractor=mock_pdf_extractor)

        content = BytesIO(b"pdf content")
        result = router.extract_from_bytes(content, "test.pdf")

        assert result.file_type == "pdf"

    def test_extract_docx_raises_error(self):
        """Test that DOCX extraction raises appropriate error."""
        router = ExtractionRouterService()

        with pytest.raises(ExtractionRouterError) as exc_info:
            router.extract_from_bytes(b"docx content", "test.docx")

        assert "Word document extraction should use WordExtractorService" in str(
            exc_info.value
        )

    def test_extract_unknown_type_raises_error(self):
        """Test that unknown file type raises error."""
        router = ExtractionRouterService()

        with pytest.raises(ExtractionRouterError) as exc_info:
            router.extract_from_bytes(b"content", "test.xyz")

        assert "Unsupported file type" in str(exc_info.value)


class TestExtractFromFile:
    """Tests for extract_from_file method."""

    def test_extract_from_nonexistent_file(self):
        """Test extraction from non-existent file."""
        router = ExtractionRouterService()

        with pytest.raises(ExtractionRouterError) as exc_info:
            router.extract_from_file("/nonexistent/file.pdf")

        assert "File not found" in str(exc_info.value)

    def test_extract_pdf_from_file(self):
        """Test extracting PDF from file."""
        mock_pdf_extractor = MagicMock()
        mock_pdf_result = PDFExtractionResult(
            is_text_based=True,
            text_content="File content",
            pages=["File content"],
            tables=[],
            page_count=1,
            has_images=False,
            confidence=0.88,
            metadata={},
        )
        mock_pdf_extractor.extract_from_bytes.return_value = mock_pdf_result

        router = ExtractionRouterService(pdf_extractor=mock_pdf_extractor)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"PDF content")
            temp_path = f.name

        try:
            result = router.extract_from_file(temp_path)

            assert result.file_type == "pdf"
            assert result.extractor_used == "pdf"
        finally:
            Path(temp_path).unlink()

    def test_extract_image_from_file(self):
        """Test extracting image from file."""
        mock_vlm_extractor = MagicMock()
        mock_vlm_result = VLMExtractionResult(
            extracted_data={"lab_values": []},
            raw_response="{}",
            confidence=0.92,
            image_description="Lab result image",
            metadata={},
        )
        mock_vlm_extractor.extract_from_bytes.return_value = mock_vlm_result

        router = ExtractionRouterService(vlm_extractor=mock_vlm_extractor)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"Image content")
            temp_path = f.name

        try:
            result = router.extract_from_file(temp_path)

            assert result.file_type == "image"
            assert result.extractor_used == "vlm"
        finally:
            Path(temp_path).unlink()


class TestFormatForStorage:
    """Tests for format_for_storage method."""

    def test_format_pdf_result(self):
        """Test formatting PDF extraction result for storage."""
        router = ExtractionRouterService()

        result = ExtractionRouteResult(
            file_type="pdf",
            extractor_used="pdf",
            extracted_data={"text_content": "Test", "tables": []},
            raw_content="Test",
            confidence=0.9,
            is_text_based=True,
            metadata={},
        )

        storage_data = router.format_for_storage(result)

        assert storage_data["source"] == "pdf"
        assert storage_data["file_type"] == "pdf"
        assert storage_data["confidence"] == 0.9
        assert storage_data["is_text_based"] is True
        assert "image_description" not in storage_data

    def test_format_vlm_result(self):
        """Test formatting VLM extraction result for storage."""
        router = ExtractionRouterService()

        result = ExtractionRouteResult(
            file_type="image",
            extractor_used="vlm",
            extracted_data={"lab_values": []},
            raw_content="{}",
            confidence=0.85,
            is_text_based=False,
            image_description="A lab result showing blood test values",
            metadata={},
        )

        storage_data = router.format_for_storage(result)

        assert storage_data["source"] == "vlm"
        assert storage_data["file_type"] == "image"
        assert storage_data["confidence"] == 0.85
        assert storage_data["is_text_based"] is False
        assert storage_data["image_description"] == "A lab result showing blood test values"


class TestFactoryFunction:
    """Tests for the factory function."""

    def test_get_extraction_router_service_default(self):
        """Test factory function with default parameters."""
        router = get_extraction_router_service()

        assert isinstance(router, ExtractionRouterService)
        assert router.anthropic_client is None
        assert router.vlm_extractor is None

    def test_get_extraction_router_service_with_client(self):
        """Test factory function with Anthropic client."""
        mock_client = MagicMock()
        router = get_extraction_router_service(anthropic_client=mock_client)

        assert router.anthropic_client == mock_client
        assert router.vlm_extractor is not None

    def test_get_extraction_router_service_with_hospital_id(self):
        """Test factory function with hospital ID."""
        router = get_extraction_router_service(hospital_id="hospital_002")

        assert router.hospital_id == "hospital_002"


class TestIntegration:
    """Integration tests with mocked extractors."""

    def test_full_pdf_extraction_flow(self):
        """Test complete PDF extraction flow."""
        mock_pdf_extractor = MagicMock()
        mock_pdf_result = PDFExtractionResult(
            is_text_based=True,
            text_content="Patient: John Doe\nGlucose: 105 mg/dL\nHbA1c: 5.7%",
            pages=["Patient: John Doe\nGlucose: 105 mg/dL\nHbA1c: 5.7%"],
            tables=[
                [["Test", "Value", "Unit"], ["Glucose", "105", "mg/dL"], ["HbA1c", "5.7", "%"]]
            ],
            page_count=1,
            has_images=False,
            confidence=0.95,
            metadata={"title": "Lab Report"},
        )
        mock_pdf_extractor.extract_from_bytes.return_value = mock_pdf_result

        router = ExtractionRouterService(pdf_extractor=mock_pdf_extractor)

        result = router.extract_from_bytes(b"PDF content", "lab_report.pdf")

        assert result.file_type == "pdf"
        assert result.extractor_used == "pdf"
        assert result.confidence == 0.95
        assert result.is_text_based is True
        assert len(result.extracted_data["tables"]) == 1

        # Test storage format
        storage = router.format_for_storage(result)
        assert storage["source"] == "pdf"
        assert storage["is_text_based"] is True

    def test_full_image_extraction_flow(self):
        """Test complete image extraction flow."""
        mock_vlm_extractor = MagicMock()
        mock_vlm_result = VLMExtractionResult(
            extracted_data={
                "patient_info": {"name": "John Doe"},
                "lab_values": [
                    {"test_name": "Glucose", "value": 105, "unit": "mg/dL"},
                    {"test_name": "HbA1c", "value": 5.7, "unit": "%"},
                ],
            },
            raw_response='{"patient_info": {}, "lab_values": []}',
            confidence=0.88,
            image_description="A blood test result with glucose and HbA1c values",
            metadata={"model": "claude-sonnet-4-20250514"},
        )
        mock_vlm_extractor.extract_from_bytes.return_value = mock_vlm_result

        router = ExtractionRouterService(vlm_extractor=mock_vlm_extractor)

        result = router.extract_from_bytes(b"Image content", "lab_photo.jpg")

        assert result.file_type == "image"
        assert result.extractor_used == "vlm"
        assert result.confidence == 0.88
        assert result.is_text_based is False
        assert len(result.extracted_data["lab_values"]) == 2

        # Test storage format
        storage = router.format_for_storage(result)
        assert storage["source"] == "vlm"
        assert storage["image_description"] == "A blood test result with glucose and HbA1c values"
