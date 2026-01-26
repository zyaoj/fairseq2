"""PDF text detection and extraction service using pdfplumber.

This service handles PDF lab results by:
1. Detecting if a PDF is text-based or scanned (image-based)
2. Extracting text content from text-based PDFs using pdfplumber
3. Extracting table data from PDFs
4. Returning structured extraction results for further processing by LLM
"""

import logging
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

import pdfplumber
from pdfplumber.page import Page


class PDFExtractorError(Exception):
    """Raised when PDF extraction fails."""

    pass


@dataclass
class PDFExtractionResult:
    """Result of PDF extraction.

    Attributes:
        is_text_based: True if PDF contains extractable text, False if scanned/image
        text_content: Full text extracted from the PDF
        pages: List of page contents (text per page)
        tables: List of extracted tables (each table is a 2D list)
        page_count: Total number of pages
        has_images: True if PDF contains embedded images
        confidence: Confidence score for text extraction (0.0-1.0)
        metadata: PDF metadata (title, author, etc.)
    """

    is_text_based: bool
    text_content: str
    pages: list[str]
    tables: list[list[list[str]]]
    page_count: int
    has_images: bool
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class PDFExtractorService:
    """Service for detecting PDF type and extracting text content.

    This service determines whether a PDF is:
    - Text-based: Contains selectable/extractable text
    - Image-based: Scanned document or image-only PDF

    For text-based PDFs, it extracts text and tables using pdfplumber.
    For image-based PDFs, it returns metadata indicating VLM extraction is needed.
    """

    # Minimum character count to consider a page as having text
    MIN_CHARS_PER_PAGE = 10

    # Minimum percentage of pages with text to consider PDF as text-based
    MIN_TEXT_PAGES_RATIO = 0.5

    def __init__(self):
        """Initialize the PDF extractor service."""
        pass

    def extract_from_file(self, file_path: str | Path) -> PDFExtractionResult:
        """Extract text and detect type from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            PDFExtractionResult with extraction data

        Raises:
            PDFExtractorError: If extraction fails
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                return self._extract_from_pdf(pdf)
        except Exception as e:
            raise PDFExtractorError(f"Failed to extract from file: {e}") from e

    def extract_from_bytes(self, content: bytes | BytesIO) -> PDFExtractionResult:
        """Extract text and detect type from PDF bytes.

        Args:
            content: PDF content as bytes or BytesIO

        Returns:
            PDFExtractionResult with extraction data

        Raises:
            PDFExtractorError: If extraction fails
        """
        try:
            if isinstance(content, bytes):
                content = BytesIO(content)
            with pdfplumber.open(content) as pdf:
                return self._extract_from_pdf(pdf)
        except Exception as e:
            raise PDFExtractorError(f"Failed to extract from bytes: {e}") from e

    def _extract_from_pdf(self, pdf: pdfplumber.PDF) -> PDFExtractionResult:
        """Extract content from an opened PDF.

        Args:
            pdf: Opened pdfplumber PDF object

        Returns:
            PDFExtractionResult with extraction data
        """
        page_count = len(pdf.pages)
        pages_text: list[str] = []
        all_tables: list[list[list[str]]] = []
        pages_with_text = 0
        pages_with_images = 0
        total_chars = 0

        for page in pdf.pages:
            # Extract text from page
            page_text = self._extract_page_text(page)
            pages_text.append(page_text)

            char_count = len(page_text.strip())
            total_chars += char_count

            if char_count >= self.MIN_CHARS_PER_PAGE:
                pages_with_text += 1

            # Check for images
            if self._page_has_images(page):
                pages_with_images += 1

            # Extract tables from page
            page_tables = self._extract_page_tables(page)
            all_tables.extend(page_tables)

        # Determine if PDF is text-based
        text_ratio = pages_with_text / page_count if page_count > 0 else 0
        is_text_based = text_ratio >= self.MIN_TEXT_PAGES_RATIO

        # Calculate confidence based on text density
        avg_chars_per_page = total_chars / page_count if page_count > 0 else 0
        # Normalize: ~500 chars/page = high confidence
        confidence = min(1.0, avg_chars_per_page / 500.0) if is_text_based else 0.0

        # Combine all text
        full_text = "\n\n".join(pages_text)

        # Extract metadata
        metadata = self._extract_metadata(pdf)

        return PDFExtractionResult(
            is_text_based=is_text_based,
            text_content=full_text,
            pages=pages_text,
            tables=all_tables,
            page_count=page_count,
            has_images=pages_with_images > 0,
            confidence=confidence,
            metadata=metadata,
        )

    def _extract_page_text(self, page: Page) -> str:
        """Extract text content from a single page.

        Args:
            page: pdfplumber page object

        Returns:
            Text content of the page
        """
        text = page.extract_text() or ""
        return text.strip()

    def _extract_page_tables(self, page: Page) -> list[list[list[str]]]:
        """Extract tables from a single page.

        Args:
            page: pdfplumber page object

        Returns:
            List of tables (each table is a 2D list of cell strings)
        """
        tables = []
        try:
            extracted_tables = page.extract_tables()
            for table in extracted_tables:
                if table:
                    # Clean up table cells
                    cleaned_table = []
                    for row in table:
                        if row:
                            cleaned_row = [
                                str(cell).strip() if cell is not None else ""
                                for cell in row
                            ]
                            if any(cleaned_row):  # Only add non-empty rows
                                cleaned_table.append(cleaned_row)
                    if cleaned_table:
                        tables.append(cleaned_table)
        except Exception:
            # Table extraction can fail for complex layouts
            pass
        return tables

    def _page_has_images(self, page: Page) -> bool:
        """Check if a page contains embedded images.

        Args:
            page: pdfplumber page object

        Returns:
            True if page has images
        """
        try:
            return len(page.images) > 0
        except Exception:
            return False

    def _extract_metadata(self, pdf: pdfplumber.PDF) -> dict[str, Any]:
        """Extract PDF metadata.

        Args:
            pdf: pdfplumber PDF object

        Returns:
            Dictionary of metadata
        """
        metadata: dict[str, Any] = {}
        try:
            if pdf.metadata:
                # Extract common metadata fields
                for key in ["Title", "Author", "Subject", "Creator", "Producer", "CreationDate"]:
                    if key in pdf.metadata:
                        metadata[key.lower()] = pdf.metadata[key]
        except Exception:
            pass
        return metadata

    def detect_pdf_type(self, content: bytes | BytesIO) -> bool:
        """Quick check to determine if PDF is text-based.

        This is a faster check than full extraction, useful for routing decisions.

        Args:
            content: PDF content as bytes or BytesIO

        Returns:
            True if PDF is text-based, False if image-based

        Raises:
            PDFExtractorError: If detection fails
        """
        try:
            if isinstance(content, bytes):
                content = BytesIO(content)

            with pdfplumber.open(content) as pdf:
                # Check first few pages
                pages_to_check = min(3, len(pdf.pages))
                pages_with_text = 0

                for i in range(pages_to_check):
                    page = pdf.pages[i]
                    text = page.extract_text() or ""
                    if len(text.strip()) >= self.MIN_CHARS_PER_PAGE:
                        pages_with_text += 1

                text_ratio = pages_with_text / pages_to_check if pages_to_check > 0 else 0
                return text_ratio >= self.MIN_TEXT_PAGES_RATIO

        except Exception as e:
            raise PDFExtractorError(f"Failed to detect PDF type: {e}") from e

    def format_for_llm(self, result: PDFExtractionResult) -> str:
        """Format extraction result for LLM processing.

        Creates a structured text representation suitable for LLM extraction.

        Args:
            result: PDF extraction result

        Returns:
            Formatted text string
        """
        parts = []

        # Add metadata if available
        if result.metadata:
            parts.append("## Document Metadata")
            for key, value in result.metadata.items():
                parts.append(f"- {key}: {value}")
            parts.append("")

        # Add page count
        parts.append(f"## Document Info")
        parts.append(f"- Pages: {result.page_count}")
        parts.append(f"- Text-based: {result.is_text_based}")
        parts.append(f"- Has images: {result.has_images}")
        parts.append(f"- Extraction confidence: {result.confidence:.2f}")
        parts.append("")

        # Add text content
        parts.append("## Text Content")
        parts.append(result.text_content)
        parts.append("")

        # Add tables
        if result.tables:
            parts.append("## Tables")
            for i, table in enumerate(result.tables):
                parts.append(f"\n### Table {i + 1}")
                for row in table:
                    parts.append(" | ".join(row))
            parts.append("")

        return "\n".join(parts)


# Module-level singleton
_pdf_extractor_service: PDFExtractorService | None = None


def get_pdf_extractor_service() -> PDFExtractorService:
    """Get the PDF extractor service singleton.

    Returns:
        PDFExtractorService instance
    """
    global _pdf_extractor_service
    if _pdf_extractor_service is None:
        _pdf_extractor_service = PDFExtractorService()
    return _pdf_extractor_service
