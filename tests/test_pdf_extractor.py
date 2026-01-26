"""Tests for PDFExtractorService."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from src.services.extraction.pdf_extractor import (
    PDFExtractionResult,
    PDFExtractorError,
    PDFExtractorService,
    get_pdf_extractor_service,
)


class TestPDFExtractorServiceSingleton:
    """Tests for the singleton factory function."""

    def test_get_pdf_extractor_service_returns_instance(self):
        """Test that get_pdf_extractor_service returns a PDFExtractorService instance."""
        service = get_pdf_extractor_service()
        assert isinstance(service, PDFExtractorService)

    def test_get_pdf_extractor_service_returns_same_instance(self):
        """Test that get_pdf_extractor_service returns the same singleton instance."""
        service1 = get_pdf_extractor_service()
        service2 = get_pdf_extractor_service()
        assert service1 is service2


class TestPDFExtractionResult:
    """Tests for the PDFExtractionResult dataclass."""

    def test_result_with_defaults(self):
        """Test creating a result with default metadata."""
        result = PDFExtractionResult(
            is_text_based=True,
            text_content="Sample text",
            pages=["Sample text"],
            tables=[],
            page_count=1,
            has_images=False,
            confidence=0.9,
        )
        assert result.metadata == {}
        assert result.is_text_based is True
        assert result.confidence == 0.9

    def test_result_with_metadata(self):
        """Test creating a result with custom metadata."""
        result = PDFExtractionResult(
            is_text_based=True,
            text_content="Sample text",
            pages=["Sample text"],
            tables=[],
            page_count=1,
            has_images=False,
            confidence=0.9,
            metadata={"title": "Test Document", "author": "Test Author"},
        )
        assert result.metadata["title"] == "Test Document"
        assert result.metadata["author"] == "Test Author"


class TestPDFExtraction:
    """Tests for PDF extraction functionality."""

    @pytest.fixture
    def mock_pdf(self):
        """Create a mock PDF with text content."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This is sample text content that is long enough to pass the threshold."
        mock_page.extract_tables.return_value = []
        mock_page.images = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {"Title": "Test PDF", "Author": "Test Author"}

        return mock_pdf

    @pytest.fixture
    def mock_pdf_with_tables(self):
        """Create a mock PDF with table content."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Lab Results Report with sufficient text content for detection."
        mock_page.extract_tables.return_value = [
            [
                ["Test Name", "Value", "Unit", "Reference Range"],
                ["Hemoglobin", "14.5", "g/dL", "12.0-16.0"],
                ["WBC", "7.2", "10^3/uL", "4.5-11.0"],
            ]
        ]
        mock_page.images = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}

        return mock_pdf

    @pytest.fixture
    def mock_image_pdf(self):
        """Create a mock PDF that appears to be image-based (scanned)."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""  # No text extracted
        mock_page.extract_tables.return_value = []
        mock_page.images = [{"name": "image1.png"}]

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}

        return mock_pdf

    def test_extract_text_based_pdf(self, mock_pdf: MagicMock):
        """Test extracting from a text-based PDF."""
        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            assert result.is_text_based is True
            assert "sample text content" in result.text_content.lower()
            assert result.page_count == 1
            assert len(result.pages) == 1
            assert result.confidence > 0

    def test_extract_image_based_pdf(self, mock_image_pdf: MagicMock):
        """Test extracting from an image-based (scanned) PDF."""
        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_image_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            assert result.is_text_based is False
            assert result.has_images is True
            assert result.confidence == 0.0

    def test_extract_pdf_with_tables(self, mock_pdf_with_tables: MagicMock):
        """Test extracting tables from a PDF."""
        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf_with_tables

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            assert len(result.tables) == 1
            assert len(result.tables[0]) == 3  # 3 rows (header + 2 data rows)
            assert result.tables[0][0][0] == "Test Name"  # First cell
            assert result.tables[0][1][1] == "14.5"  # Hemoglobin value

    def test_extract_metadata(self, mock_pdf: MagicMock):
        """Test extracting PDF metadata."""
        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            assert "title" in result.metadata
            assert result.metadata["title"] == "Test PDF"
            assert result.metadata["author"] == "Test Author"

    def test_extract_from_file(self, mock_pdf: MagicMock):
        """Test extracting from a file path."""
        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_file("/path/to/test.pdf")

            assert result.is_text_based is True
            mock_open.assert_called_once_with("/path/to/test.pdf")

    def test_extract_from_bytesio(self, mock_pdf: MagicMock):
        """Test extracting from BytesIO object."""
        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            content = BytesIO(b"fake pdf content")
            result = service.extract_from_bytes(content)

            assert result.is_text_based is True


class TestPDFTypeDetection:
    """Tests for PDF type detection (text vs image)."""

    def test_detect_text_based_pdf(self):
        """Test detecting a text-based PDF."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This is enough text to be considered text-based."

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.detect_pdf_type(b"fake pdf content")

            assert result is True

    def test_detect_image_based_pdf(self):
        """Test detecting an image-based PDF."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""  # No text

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.detect_pdf_type(b"fake pdf content")

            assert result is False

    def test_detect_checks_first_pages_only(self):
        """Test that detection only checks the first few pages for efficiency."""
        mock_pages = []
        for i in range(10):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Text content" if i < 3 else ""
            mock_pages.append(mock_page)

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.detect_pdf_type(b"fake pdf content")

            # Should only check first 3 pages
            assert result is True
            # Only first 3 pages should have extract_text called
            for i, page in enumerate(mock_pages):
                if i < 3:
                    page.extract_text.assert_called_once()
                else:
                    page.extract_text.assert_not_called()


class TestFormatForLLM:
    """Tests for LLM formatting functionality."""

    def test_format_basic_result(self):
        """Test formatting a basic extraction result for LLM."""
        result = PDFExtractionResult(
            is_text_based=True,
            text_content="Sample lab results content",
            pages=["Sample lab results content"],
            tables=[],
            page_count=1,
            has_images=False,
            confidence=0.85,
        )

        service = PDFExtractorService()
        formatted = service.format_for_llm(result)

        assert "## Document Info" in formatted
        assert "Pages: 1" in formatted
        assert "Text-based: True" in formatted
        assert "Extraction confidence: 0.85" in formatted
        assert "## Text Content" in formatted
        assert "Sample lab results content" in formatted

    def test_format_result_with_tables(self):
        """Test formatting a result with tables."""
        result = PDFExtractionResult(
            is_text_based=True,
            text_content="Lab report",
            pages=["Lab report"],
            tables=[
                [
                    ["Test", "Value"],
                    ["Hemoglobin", "14.5"],
                ]
            ],
            page_count=1,
            has_images=False,
            confidence=0.9,
        )

        service = PDFExtractorService()
        formatted = service.format_for_llm(result)

        assert "## Tables" in formatted
        assert "### Table 1" in formatted
        assert "Test | Value" in formatted
        assert "Hemoglobin | 14.5" in formatted

    def test_format_result_with_metadata(self):
        """Test formatting a result with metadata."""
        result = PDFExtractionResult(
            is_text_based=True,
            text_content="Content",
            pages=["Content"],
            tables=[],
            page_count=1,
            has_images=False,
            confidence=0.8,
            metadata={"title": "Lab Report", "author": "Dr. Smith"},
        )

        service = PDFExtractorService()
        formatted = service.format_for_llm(result)

        assert "## Document Metadata" in formatted
        assert "title: Lab Report" in formatted
        assert "author: Dr. Smith" in formatted


class TestErrorHandling:
    """Tests for error handling."""

    def test_extract_from_file_invalid_path(self):
        """Test that extraction fails gracefully for invalid file path."""
        service = PDFExtractorService()

        with pytest.raises(PDFExtractorError) as exc_info:
            service.extract_from_file("/nonexistent/path/to/file.pdf")

        assert "Failed to extract from file" in str(exc_info.value)

    def test_extract_from_bytes_invalid_content(self):
        """Test that extraction fails gracefully for invalid content."""
        service = PDFExtractorService()

        with pytest.raises(PDFExtractorError) as exc_info:
            service.extract_from_bytes(b"not a valid pdf")

        assert "Failed to extract from bytes" in str(exc_info.value)

    def test_detect_pdf_type_invalid_content(self):
        """Test that type detection fails gracefully for invalid content."""
        service = PDFExtractorService()

        with pytest.raises(PDFExtractorError) as exc_info:
            service.detect_pdf_type(b"not a valid pdf")

        assert "Failed to detect PDF type" in str(exc_info.value)

    def test_table_extraction_error_handled_gracefully(self):
        """Test that table extraction errors don't crash the service."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Some text content that passes the threshold for detection."
        mock_page.extract_tables.side_effect = Exception("Table extraction failed")
        mock_page.images = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            # Should still succeed, just with no tables
            assert result.is_text_based is True
            assert result.tables == []


class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    def test_high_confidence_for_text_dense_pdf(self):
        """Test that PDFs with lots of text get high confidence."""
        mock_page = MagicMock()
        # ~600 chars, should give high confidence (normalized to 500 chars/page)
        mock_page.extract_text.return_value = "x" * 600
        mock_page.extract_tables.return_value = []
        mock_page.images = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            assert result.confidence == 1.0  # Capped at 1.0

    def test_low_confidence_for_sparse_text(self):
        """Test that PDFs with little text get low confidence."""
        mock_page = MagicMock()
        # ~50 chars, should give low confidence
        mock_page.extract_text.return_value = "x" * 50
        mock_page.extract_tables.return_value = []
        mock_page.images = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            assert result.is_text_based is True  # 50 chars > 10 min threshold
            assert result.confidence == pytest.approx(0.1, rel=0.1)

    def test_zero_confidence_for_image_pdf(self):
        """Test that image-based PDFs get zero confidence."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_page.extract_tables.return_value = []
        mock_page.images = [{"name": "scan.png"}]

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            assert result.is_text_based is False
            assert result.confidence == 0.0


class TestMultiPagePDF:
    """Tests for multi-page PDF handling."""

    def test_multiple_pages_combined(self):
        """Test that text from multiple pages is combined correctly."""
        mock_pages = []
        for i in range(3):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = f"Page {i + 1} content with enough text to pass threshold."
            mock_page.extract_tables.return_value = []
            mock_page.images = []
            mock_pages.append(mock_page)

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdf.metadata = {}

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            assert result.page_count == 3
            assert len(result.pages) == 3
            assert "Page 1 content" in result.text_content
            assert "Page 2 content" in result.text_content
            assert "Page 3 content" in result.text_content

    def test_mixed_pages_text_ratio(self):
        """Test text ratio calculation with mixed text/empty pages."""
        mock_pages = []
        # 2 pages with text, 2 pages without
        for i in range(4):
            mock_page = MagicMock()
            if i < 2:
                mock_page.extract_text.return_value = "Sufficient text content here."
            else:
                mock_page.extract_text.return_value = ""
            mock_page.extract_tables.return_value = []
            mock_page.images = []
            mock_pages.append(mock_page)

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdf.metadata = {}

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            # 2/4 = 50% which equals MIN_TEXT_PAGES_RATIO, so it should be text-based
            assert result.is_text_based is True
            assert result.page_count == 4

    def test_below_text_ratio_threshold(self):
        """Test that PDF with few text pages is classified as image-based."""
        mock_pages = []
        # 1 page with text, 3 pages without
        for i in range(4):
            mock_page = MagicMock()
            if i == 0:
                mock_page.extract_text.return_value = "Some text."
            else:
                mock_page.extract_text.return_value = ""
            mock_page.extract_tables.return_value = []
            mock_page.images = []
            mock_pages.append(mock_page)

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdf.metadata = {}

        with patch("pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_pdf

            service = PDFExtractorService()
            result = service.extract_from_bytes(b"fake pdf content")

            # 1/4 = 25% which is below MIN_TEXT_PAGES_RATIO (50%)
            assert result.is_text_based is False
