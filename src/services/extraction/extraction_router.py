"""Extraction router service for dispatching to appropriate extractors.

This service routes lab result files to the appropriate extractor based on file type:
- PDF files: Use PDFExtractorService for text detection/extraction
- Image files: Use VLMExtractorService for vision-based extraction
- Image-only PDFs: Detected by PDF extractor, routed to VLM extractor

The router provides a unified interface for the upload endpoint to call,
handling the complexity of file type detection and extractor selection.
"""

import logging
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

from src.services.extraction.pdf_extractor import (
    PDFExtractionResult,
    PDFExtractorService,
    get_pdf_extractor_service,
)
from src.services.extraction.vlm_extractor import (
    VLMExtractionResult,
    VLMExtractorService,
    get_vlm_extractor_service,
)


class ExtractionRouterError(Exception):
    """Raised when extraction routing fails."""

    pass


# File type categories
FileTypeCategory = Literal["pdf", "image", "docx", "unknown"]

# Supported image extensions for VLM extraction
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}

# PDF extension
PDF_EXTENSIONS = {".pdf"}


@dataclass
class ExtractionRouteResult:
    """Result of extraction routing.

    Attributes:
        file_type: Detected file type category (pdf, image, docx, unknown)
        extractor_used: Which extractor was used (pdf, vlm, none)
        extracted_data: Structured data extracted from the file
        raw_content: Raw text content (for PDFs) or raw response (for VLM)
        confidence: Confidence score for extraction (0.0-1.0)
        is_text_based: For PDFs, whether the PDF contained extractable text
        image_description: For VLM extraction, description of the image
        metadata: Additional metadata about the extraction
    """

    file_type: FileTypeCategory
    extractor_used: Literal["pdf", "vlm", "none"]
    extracted_data: dict[str, Any]
    raw_content: str
    confidence: float
    is_text_based: bool | None = None
    image_description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ExtractionRouterService:
    """Service for routing files to appropriate extractors.

    This service:
    1. Detects file type from extension
    2. Routes to PDF extractor for PDF files
    3. Routes to VLM extractor for image files
    4. For PDFs without extractable text, falls back to VLM extraction

    Extraction flow:
    - PDF (text-based) -> PDFExtractorService -> text + tables
    - PDF (image-based) -> PDFExtractorService -> VLMExtractorService
    - Image -> VLMExtractorService -> structured data

    Note: The anthropic_client is required for VLM extraction. If not provided,
    image files and image-based PDFs cannot be processed.
    """

    def __init__(
        self,
        anthropic_client: Any | None = None,
        pdf_extractor: PDFExtractorService | None = None,
        vlm_extractor: VLMExtractorService | None = None,
        hospital_id: str | None = None,
    ):
        """Initialize the extraction router.

        Args:
            anthropic_client: Anthropic client for VLM extraction (optional).
                             If not provided, image extraction will fail.
            pdf_extractor: PDF extractor service (optional, creates default).
            vlm_extractor: VLM extractor service (optional, creates from client).
            hospital_id: Hospital ID for hospital-specific extraction rules.
        """
        self.anthropic_client = anthropic_client
        self.hospital_id = hospital_id

        # Initialize PDF extractor (doesn't require external client)
        self.pdf_extractor = pdf_extractor or get_pdf_extractor_service()

        # Initialize VLM extractor if client provided
        if vlm_extractor is not None:
            self.vlm_extractor = vlm_extractor
        elif anthropic_client is not None:
            self.vlm_extractor = get_vlm_extractor_service(
                anthropic_client=anthropic_client,
                hospital_id=hospital_id,
            )
        else:
            self.vlm_extractor = None

    def extract_from_file(
        self,
        file_path: str | Path,
        extraction_type: str = "lab_result",
    ) -> ExtractionRouteResult:
        """Extract data from a file, routing to appropriate extractor.

        Args:
            file_path: Path to the file
            extraction_type: Type of extraction (default: lab_result)

        Returns:
            ExtractionRouteResult with extraction data

        Raises:
            ExtractionRouterError: If extraction fails or file type unsupported
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ExtractionRouterError(f"File not found: {file_path}")

        # Detect file type from extension
        file_type = self._detect_file_type(file_path.suffix)

        # Read file content
        with open(file_path, "rb") as f:
            content = f.read()

        return self._route_extraction(
            content=content,
            file_type=file_type,
            extension=file_path.suffix.lower(),
            extraction_type=extraction_type,
        )

    def extract_from_bytes(
        self,
        content: bytes | BytesIO,
        filename: str,
        extraction_type: str = "lab_result",
    ) -> ExtractionRouteResult:
        """Extract data from file bytes, routing to appropriate extractor.

        Args:
            content: File content as bytes or BytesIO
            filename: Original filename (used for extension detection)
            extraction_type: Type of extraction (default: lab_result)

        Returns:
            ExtractionRouteResult with extraction data

        Raises:
            ExtractionRouterError: If extraction fails or file type unsupported
        """
        # Get bytes from BytesIO if needed
        if isinstance(content, BytesIO):
            content = content.read()

        # Detect file type from extension
        extension = Path(filename).suffix.lower()
        file_type = self._detect_file_type(extension)

        return self._route_extraction(
            content=content,
            file_type=file_type,
            extension=extension,
            extraction_type=extraction_type,
        )

    def _detect_file_type(self, extension: str) -> FileTypeCategory:
        """Detect file type category from extension.

        Args:
            extension: File extension (with or without leading dot)

        Returns:
            File type category
        """
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        if ext in PDF_EXTENSIONS:
            return "pdf"
        elif ext in IMAGE_EXTENSIONS:
            return "image"
        elif ext in {".docx", ".doc"}:
            return "docx"
        else:
            return "unknown"

    def _route_extraction(
        self,
        content: bytes,
        file_type: FileTypeCategory,
        extension: str,
        extraction_type: str,
    ) -> ExtractionRouteResult:
        """Route content to appropriate extractor.

        Args:
            content: File content as bytes
            file_type: Detected file type category
            extension: File extension
            extraction_type: Type of extraction to perform

        Returns:
            ExtractionRouteResult with extraction data
        """
        if file_type == "pdf":
            return self._extract_pdf(content, extraction_type)
        elif file_type == "image":
            return self._extract_image(content, extension, extraction_type)
        elif file_type == "docx":
            # Word document extraction not handled by this router
            # (handled by word_extractor.py separately)
            raise ExtractionRouterError(
                "Word document extraction should use WordExtractorService directly"
            )
        else:
            raise ExtractionRouterError(
                f"Unsupported file type: {extension}. "
                f"Supported types: PDF, images (jpg, png, gif, etc.)"
            )

    def _extract_pdf(
        self,
        content: bytes,
        extraction_type: str,
    ) -> ExtractionRouteResult:
        """Extract data from a PDF file.

        For text-based PDFs, returns the extracted text and tables.
        For image-based PDFs, falls back to VLM extraction.

        Args:
            content: PDF file content as bytes
            extraction_type: Type of extraction to perform

        Returns:
            ExtractionRouteResult with extraction data
        """
        try:
            # First, try PDF text extraction
            pdf_result: PDFExtractionResult = self.pdf_extractor.extract_from_bytes(
                content
            )

            if pdf_result.is_text_based:
                # PDF has extractable text - return PDF extraction result
                return ExtractionRouteResult(
                    file_type="pdf",
                    extractor_used="pdf",
                    extracted_data={
                        "text_content": pdf_result.text_content,
                        "pages": pdf_result.pages,
                        "tables": pdf_result.tables,
                        "page_count": pdf_result.page_count,
                        "has_images": pdf_result.has_images,
                    },
                    raw_content=pdf_result.text_content,
                    confidence=pdf_result.confidence,
                    is_text_based=True,
                    metadata={
                        "pdf_metadata": pdf_result.metadata,
                        "extraction_type": extraction_type,
                    },
                )
            else:
                # PDF is image-based - fall back to VLM extraction
                if self.vlm_extractor is None:
                    raise ExtractionRouterError(
                        "PDF contains images only but VLM extractor is not available. "
                        "Provide an Anthropic client for image extraction."
                    )

                # Convert PDF to image for VLM extraction
                # Note: For MVP, we'll raise an error - full PDF-to-image conversion
                # would require pdf2image or similar library
                raise ExtractionRouterError(
                    "Image-only PDF extraction requires PDF-to-image conversion, "
                    "which is not yet implemented. Please upload the lab result as "
                    "an image file (jpg, png) instead."
                )

        except ExtractionRouterError:
            raise
        except Exception as e:
            raise ExtractionRouterError(f"PDF extraction failed: {e}") from e

    def _extract_image(
        self,
        content: bytes,
        extension: str,
        extraction_type: str,
    ) -> ExtractionRouteResult:
        """Extract data from an image file using VLM.

        Args:
            content: Image file content as bytes
            extension: File extension
            extraction_type: Type of extraction to perform

        Returns:
            ExtractionRouteResult with extraction data
        """
        if self.vlm_extractor is None:
            raise ExtractionRouterError(
                "VLM extractor not available. "
                "Provide an Anthropic client for image extraction."
            )

        # Determine MIME type from extension
        from src.services.extraction.vlm_extractor import SUPPORTED_IMAGE_TYPES

        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        mime_type = SUPPORTED_IMAGE_TYPES.get(ext)
        if mime_type is None:
            raise ExtractionRouterError(
                f"Unsupported image type: {extension}. "
                f"Supported: {', '.join(SUPPORTED_IMAGE_TYPES.keys())}"
            )

        try:
            vlm_result: VLMExtractionResult = self.vlm_extractor.extract_from_bytes(
                content=content,
                mime_type=mime_type,
                extraction_type=extraction_type,
            )

            return ExtractionRouteResult(
                file_type="image",
                extractor_used="vlm",
                extracted_data=vlm_result.extracted_data,
                raw_content=vlm_result.raw_response,
                confidence=vlm_result.confidence,
                is_text_based=False,
                image_description=vlm_result.image_description,
                metadata={
                    "vlm_metadata": vlm_result.metadata,
                    "mime_type": mime_type,
                    "extraction_type": extraction_type,
                },
            )

        except ExtractionRouterError:
            raise
        except Exception as e:
            raise ExtractionRouterError(f"Image extraction failed: {e}") from e

    def format_for_storage(self, result: ExtractionRouteResult) -> dict[str, Any]:
        """Format extraction result for database storage.

        Creates a dictionary suitable for storing in the LabResult.extracted_data field.

        Args:
            result: Extraction route result

        Returns:
            Dictionary for storage
        """
        storage_data = {
            "source": result.extractor_used,
            "file_type": result.file_type,
            "confidence": result.confidence,
            "data": result.extracted_data,
        }

        if result.is_text_based is not None:
            storage_data["is_text_based"] = result.is_text_based

        if result.image_description:
            storage_data["image_description"] = result.image_description

        return storage_data


# Factory function
def get_extraction_router_service(
    anthropic_client: Any | None = None,
    hospital_id: str | None = None,
) -> ExtractionRouterService:
    """Get an extraction router service instance.

    Args:
        anthropic_client: Anthropic client for VLM extraction (optional)
        hospital_id: Hospital ID for hospital-specific extraction rules

    Returns:
        ExtractionRouterService instance
    """
    return ExtractionRouterService(
        anthropic_client=anthropic_client,
        hospital_id=hospital_id,
    )
