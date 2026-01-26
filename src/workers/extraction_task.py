"""Background task for lab result extraction.

This module provides background task processing for extracting data
from uploaded lab results (PDFs and images) using the extraction router.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.core.database import SessionLocal
from src.models.clinical_event import ExtractionStatus, LabResult
from src.services.extraction import (
    ExtractionRouterError,
    ExtractionRouterService,
    ExtractionRouteResult,
    get_extraction_router_service,
)
from src.services.storage import StorageService, get_storage_service
from src.services.embedding import (
    EmbeddingRecord,
    MilvusService,
    OpenAIEmbeddingProvider,
    get_milvus_service,
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractionTask:
    """Data class for extraction task parameters.

    Attributes:
        lab_result_id: The UUID of the LabResult to process
        hospital_id: Optional hospital ID for hospital-specific extraction
    """

    lab_result_id: str
    hospital_id: str | None = None


def process_extraction_task(
    lab_result_id: str,
    hospital_id: str | None = None,
    anthropic_client: Any | None = None,
    db: Session | None = None,
    storage_service: StorageService | None = None,
    extraction_router: ExtractionRouterService | None = None,
) -> bool:
    """Process extraction for a lab result in the background.

    This function:
    1. Updates status to PROCESSING
    2. Downloads file from storage
    3. Routes to appropriate extractor (PDF or VLM)
    4. Stores extraction result in database
    5. Updates status to COMPLETED or FAILED

    Args:
        lab_result_id: UUID of the LabResult to process
        hospital_id: Optional hospital ID for hospital-specific extraction
        anthropic_client: Optional Anthropic client for VLM extraction
        db: Optional database session (creates new one if not provided)
        storage_service: Optional storage service (uses singleton if not provided)
        extraction_router: Optional extraction router (creates new one if not provided)

    Returns:
        True if extraction succeeded, False otherwise
    """
    # Create database session if not provided
    should_close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        # Get lab result
        lab_result = db.query(LabResult).filter(LabResult.id == lab_result_id).first()
        if not lab_result:
            logger.error(f"Lab result not found: {lab_result_id}")
            return False

        # Update status to PROCESSING
        lab_result.extraction_status = ExtractionStatus.PROCESSING
        db.commit()

        logger.info(f"Starting extraction for lab result {lab_result_id}")

        # Get storage service
        if storage_service is None:
            storage_service = get_storage_service()

        # Get extraction router
        if extraction_router is None:
            extraction_router = get_extraction_router_service(
                anthropic_client=anthropic_client,
                hospital_id=hospital_id,
            )

        # Download file from storage
        try:
            file_content = storage_service.download_file(lab_result.original_file_path)
        except Exception as e:
            logger.error(f"Failed to download file for {lab_result_id}: {e}")
            _mark_failed(db, lab_result, str(e))
            return False

        # Get original filename from path
        # Path format: folder/uuid_filename.ext
        original_filename = lab_result.original_file_path.split("_", 1)[-1]
        if "/" in original_filename:
            original_filename = original_filename.split("/")[-1]

        # Extract data
        try:
            result: ExtractionRouteResult = extraction_router.extract_from_bytes(
                content=file_content,
                filename=original_filename,
                extraction_type="lab_result",
            )
        except ExtractionRouterError as e:
            logger.error(f"Extraction failed for {lab_result_id}: {e}")
            _mark_failed(db, lab_result, str(e))
            return False

        # Store extraction result
        storage_data = extraction_router.format_for_storage(result)

        lab_result.extracted_data = storage_data
        lab_result.extraction_confidence = result.confidence
        lab_result.extraction_status = ExtractionStatus.COMPLETED
        db.commit()

        # Generate embedding for vector search
        try:
            _generate_embedding(lab_result, storage_data)
        except Exception as e:
            # Embedding failure is non-critical, log but don't fail extraction
            logger.warning(f"Failed to generate embedding for {lab_result_id}: {e}")

        logger.info(
            f"Extraction completed for lab result {lab_result_id} "
            f"with confidence {result.confidence:.2f}"
        )
        return True

    except Exception as e:
        logger.exception(f"Unexpected error processing extraction for {lab_result_id}: {e}")
        try:
            lab_result = db.query(LabResult).filter(LabResult.id == lab_result_id).first()
            if lab_result:
                _mark_failed(db, lab_result, str(e))
        except Exception:
            pass
        return False

    finally:
        if should_close_db:
            db.close()


def _mark_failed(db: Session, lab_result: LabResult, error_message: str) -> None:
    """Mark a lab result extraction as failed.

    Args:
        db: Database session
        lab_result: LabResult model instance
        error_message: Error message to store
    """
    lab_result.extraction_status = ExtractionStatus.FAILED
    lab_result.extracted_data = {
        "error": error_message,
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }
    db.commit()


def _generate_embedding(lab_result: LabResult, extracted_data: dict) -> None:
    """Generate embedding for a lab result and store in Milvus.

    Args:
        lab_result: LabResult model instance
        extracted_data: Extracted data dictionary
    """
    # Build content string from extracted data for embedding
    content_parts = []
    if lab_result.title:
        content_parts.append(f"Title: {lab_result.title}")
    if lab_result.description:
        content_parts.append(f"Description: {lab_result.description}")

    # Add extracted test results
    if "tests" in extracted_data:
        for test in extracted_data["tests"]:
            test_str = f"{test.get('name', '')}: {test.get('value', '')} {test.get('unit', '')}"
            if test.get("is_abnormal"):
                test_str += " (abnormal)"
            content_parts.append(test_str)

    if not content_parts:
        logger.debug(f"No content to embed for lab result {lab_result.id}")
        return

    content = "\n".join(content_parts)

    # Initialize embedding provider and Milvus service
    try:
        embedding_provider = OpenAIEmbeddingProvider()
        milvus_service = get_milvus_service(embedding_provider=embedding_provider)

        # Generate embedding
        embedding = embedding_provider.generate_embedding(content)

        # Create record and insert
        record = EmbeddingRecord(
            id=str(lab_result.id),
            patient_id=str(lab_result.patient_id),
            embedding=embedding,
            content=content[:65535],  # Truncate if needed
        )
        milvus_service.insert_embedding(record)

        logger.info(f"Generated and stored embedding for lab result {lab_result.id}")
    except ImportError as e:
        logger.warning(f"OpenAI not available for embedding generation: {e}")
    except Exception as e:
        logger.warning(f"Failed to generate/store embedding: {e}")


def create_extraction_background_task(
    lab_result_id: str,
    hospital_id: str | None = None,
    anthropic_client: Any | None = None,
) -> callable:
    """Create a callable for FastAPI BackgroundTasks.

    This returns a callable that can be added to FastAPI's BackgroundTasks.

    Args:
        lab_result_id: UUID of the LabResult to process
        hospital_id: Optional hospital ID for hospital-specific extraction
        anthropic_client: Optional Anthropic client for VLM extraction

    Returns:
        Callable that processes the extraction

    Example:
        from fastapi import BackgroundTasks

        @router.post("/upload/lab-result")
        async def upload(background_tasks: BackgroundTasks):
            # ... create lab_result ...
            task = create_extraction_background_task(
                lab_result_id=str(lab_result.id),
                hospital_id=current_user.hospital_id,
            )
            background_tasks.add_task(task)
    """

    def task() -> bool:
        return process_extraction_task(
            lab_result_id=lab_result_id,
            hospital_id=hospital_id,
            anthropic_client=anthropic_client,
        )

    return task
