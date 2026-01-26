"""VLM (Vision Language Model) extraction service for images using Claude API.

This service handles image-based lab results by:
1. Encoding images to base64 for Claude's vision API
2. Sending images to Claude for structured data extraction
3. Parsing and validating extraction results
4. Returning structured extraction results for further processing
"""

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from src.services.schema_service import SchemaService, get_schema_service


class VLMExtractorError(Exception):
    """Raised when VLM extraction fails."""

    pass


@dataclass
class VLMExtractionResult:
    """Result of VLM extraction.

    Attributes:
        extracted_data: Structured data extracted from the image
        raw_response: Raw LLM response text
        confidence: Confidence score for extraction (0.0-1.0)
        image_description: LLM's description of the image content
        metadata: Additional metadata about the extraction
    """

    extracted_data: dict[str, Any]
    raw_response: str
    confidence: float
    image_description: str
    metadata: dict[str, Any] = field(default_factory=dict)


# Supported image MIME types
SUPPORTED_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


class VLMExtractorService:
    """Service for extracting structured data from images using Claude's vision API.

    This service uses Claude's multimodal capabilities to:
    - Analyze lab result images (photos, scans)
    - Extract structured data following entity schemas
    - Handle various image formats (JPEG, PNG, etc.)

    Extraction flow:
    1. Load and encode image to base64
    2. Build extraction prompt from entity schemas
    3. Send image + prompt to Claude vision API
    4. Parse structured JSON response
    5. Return extraction results
    """

    # Default model for vision extraction
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    # Maximum tokens for extraction response
    MAX_TOKENS = 4096

    # Default entity types to extract for lab results
    DEFAULT_LAB_RESULT_ENTITIES = [
        "lab_result_values",
    ]

    def __init__(
        self,
        anthropic_client: Any,
        schema_service: SchemaService | None = None,
        hospital_id: str | None = None,
        model: str | None = None,
    ):
        """Initialize the VLM extractor service.

        Args:
            anthropic_client: Anthropic client for API calls (required).
            schema_service: Schema service for entity schemas.
            hospital_id: Hospital ID for hospital-specific rules.
            model: Model to use for extraction (default: claude-sonnet-4-20250514).

        Raises:
            VLMExtractorError: If anthropic_client is None.
        """
        if anthropic_client is None:
            raise VLMExtractorError("Anthropic client is required for VLM extraction")

        self.anthropic_client = anthropic_client
        self.schema_service = schema_service or get_schema_service()
        self.hospital_id = hospital_id
        self.model = model or self.DEFAULT_MODEL

    def extract_from_file(
        self,
        file_path: str | Path,
        extraction_type: str = "lab_result",
    ) -> VLMExtractionResult:
        """Extract structured data from an image file.

        Args:
            file_path: Path to the image file
            extraction_type: Type of extraction to perform (default: lab_result)

        Returns:
            VLMExtractionResult with extraction data

        Raises:
            VLMExtractorError: If extraction fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise VLMExtractorError(f"File not found: {file_path}")

        # Get MIME type from extension
        extension = file_path.suffix.lower()
        if extension not in SUPPORTED_IMAGE_TYPES:
            raise VLMExtractorError(
                f"Unsupported image type: {extension}. "
                f"Supported: {', '.join(SUPPORTED_IMAGE_TYPES.keys())}"
            )

        mime_type = SUPPORTED_IMAGE_TYPES[extension]

        try:
            with open(file_path, "rb") as f:
                image_data = f.read()
            return self._extract_from_image_data(
                image_data,
                mime_type,
                extraction_type,
            )
        except VLMExtractorError:
            raise
        except Exception as e:
            raise VLMExtractorError(f"Failed to extract from file: {e}") from e

    def extract_from_bytes(
        self,
        content: bytes | BytesIO,
        mime_type: str = "image/jpeg",
        extraction_type: str = "lab_result",
    ) -> VLMExtractionResult:
        """Extract structured data from image bytes.

        Args:
            content: Image content as bytes or BytesIO
            mime_type: MIME type of the image (default: image/jpeg)
            extraction_type: Type of extraction to perform (default: lab_result)

        Returns:
            VLMExtractionResult with extraction data

        Raises:
            VLMExtractorError: If extraction fails
        """
        try:
            if isinstance(content, BytesIO):
                image_data = content.read()
            else:
                image_data = content

            return self._extract_from_image_data(
                image_data,
                mime_type,
                extraction_type,
            )
        except VLMExtractorError:
            raise
        except Exception as e:
            raise VLMExtractorError(f"Failed to extract from bytes: {e}") from e

    def _extract_from_image_data(
        self,
        image_data: bytes,
        mime_type: str,
        extraction_type: str,
    ) -> VLMExtractionResult:
        """Extract structured data from image bytes.

        Args:
            image_data: Raw image bytes
            mime_type: MIME type of the image
            extraction_type: Type of extraction to perform

        Returns:
            VLMExtractionResult with extraction data
        """
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Build the extraction prompt
        prompt = self._build_extraction_prompt(extraction_type)

        # Call Claude vision API
        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=self.MAX_TOKENS,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": base64_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            # Extract response text
            raw_response = response.content[0].text

            # Parse the response
            return self._parse_extraction_response(raw_response, extraction_type)

        except VLMExtractorError:
            raise
        except Exception as e:
            raise VLMExtractorError(f"Claude API call failed: {e}") from e

    def _build_extraction_prompt(self, extraction_type: str) -> str:
        """Build the extraction prompt for the given type.

        Args:
            extraction_type: Type of extraction (e.g., lab_result)

        Returns:
            Prompt string for Claude
        """
        if extraction_type == "lab_result":
            return self._build_lab_result_prompt()
        else:
            raise VLMExtractorError(f"Unknown extraction type: {extraction_type}")

    def _build_lab_result_prompt(self) -> str:
        """Build the prompt for lab result extraction.

        Returns:
            Prompt string for lab result extraction
        """
        return """You are a medical laboratory result extraction assistant. Analyze this lab result image and extract structured data.

## Instructions

1. First, describe what you see in the image (type of lab result, overall quality, any issues)
2. Extract all lab test values you can identify
3. For each test, extract:
   - Test name (in both Chinese and English if available)
   - Value (numeric)
   - Unit of measurement
   - Reference range (if shown)
   - Flag (High/Low/Normal/Critical if indicated)
4. Extract patient information if visible (name, age, date, etc.)
5. Extract collection date and report date if visible

## Output Format

Return a JSON object with this EXACT structure:

```json
{
  "image_description": "Brief description of the image content and quality",
  "confidence": 0.95,
  "patient_info": {
    "name": "Patient name if visible",
    "age": "Age if visible",
    "gender": "Gender if visible",
    "patient_id": "ID if visible"
  },
  "collection_date": "YYYY-MM-DD if visible",
  "report_date": "YYYY-MM-DD if visible",
  "lab_name": "Laboratory name if visible",
  "lab_values": [
    {
      "test_name": "Test name",
      "test_name_en": "English name if available",
      "value": 123.45,
      "value_text": "Original value as shown (for non-numeric)",
      "unit": "mg/dL",
      "reference_range": "70-100",
      "reference_low": 70,
      "reference_high": 100,
      "flag": "Normal",
      "category": "Category if grouped (e.g., 'Blood Routine', 'Liver Function')"
    }
  ],
  "notes": "Any additional notes or observations"
}
```

Important guidelines:
- Set confidence between 0.0 and 1.0 based on image clarity and extraction certainty
- Use null for fields that are not visible or cannot be extracted
- For lab_values, include ALL tests visible in the image
- If the image is not a lab result, set confidence to 0.0 and explain in image_description

Return ONLY the JSON object, no additional text."""

    def _parse_extraction_response(
        self,
        response_text: str,
        extraction_type: str,
    ) -> VLMExtractionResult:
        """Parse the Claude response into a VLMExtractionResult.

        Args:
            response_text: Raw response from Claude
            extraction_type: Type of extraction performed

        Returns:
            VLMExtractionResult with parsed data
        """
        # Try to extract JSON from the response
        json_data = self._extract_json_from_response(response_text)

        # Extract key fields
        image_description = json_data.get("image_description", "")
        confidence = float(json_data.get("confidence", 0.5))

        # Clamp confidence to valid range
        confidence = max(0.0, min(1.0, confidence))

        # Build extracted_data without the metadata fields
        extracted_data = {
            k: v
            for k, v in json_data.items()
            if k not in ("image_description", "confidence")
        }

        return VLMExtractionResult(
            extracted_data=extracted_data,
            raw_response=response_text,
            confidence=confidence,
            image_description=image_description,
            metadata={
                "extraction_type": extraction_type,
                "model": self.model,
            },
        )

    def _extract_json_from_response(self, response_text: str) -> dict[str, Any]:
        """Extract JSON object from Claude's response.

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON dictionary

        Raises:
            VLMExtractorError: If JSON cannot be extracted
        """
        # Try to find JSON block markers first
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON object
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise VLMExtractorError("No JSON found in response")

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise VLMExtractorError(f"Failed to parse JSON: {e}") from e

    def format_for_storage(self, result: VLMExtractionResult) -> dict[str, Any]:
        """Format extraction result for database storage.

        Creates a dictionary suitable for storing in the LabResult.extracted_data field.

        Args:
            result: VLM extraction result

        Returns:
            Dictionary for storage
        """
        return {
            "source": "vlm",
            "model": result.metadata.get("model", self.model),
            "confidence": result.confidence,
            "image_description": result.image_description,
            "data": result.extracted_data,
        }


# Module-level factory function
_vlm_extractor_service: VLMExtractorService | None = None


def get_vlm_extractor_service(
    anthropic_client: Any,
    hospital_id: str | None = None,
    model: str | None = None,
) -> VLMExtractorService:
    """Get a VLM extractor service instance.

    Note: Unlike other services, this does NOT use a singleton pattern because
    the anthropic_client must be provided. Each call creates a new instance.

    Args:
        anthropic_client: Anthropic client for API calls (required)
        hospital_id: Optional hospital ID for hospital-specific rules
        model: Optional model to use for extraction

    Returns:
        VLMExtractorService instance
    """
    return VLMExtractorService(
        anthropic_client=anthropic_client,
        hospital_id=hospital_id,
        model=model,
    )
