"""Tests for extraction task background worker."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.clinical_event import ExtractionStatus, LabResult
from src.services.extraction import ExtractionRouterError, ExtractionRouteResult
from src.workers.extraction_task import (
    ExtractionTask,
    _mark_failed,
    create_extraction_background_task,
    process_extraction_task,
)


class TestExtractionTask:
    """Tests for the ExtractionTask dataclass."""

    def test_dataclass_creation(self):
        """Test creating an ExtractionTask."""
        task = ExtractionTask(
            lab_result_id="test-uuid",
            hospital_id="hospital-001",
        )

        assert task.lab_result_id == "test-uuid"
        assert task.hospital_id == "hospital-001"

    def test_dataclass_default_hospital_id(self):
        """Test default hospital_id is None."""
        task = ExtractionTask(lab_result_id="test-uuid")

        assert task.lab_result_id == "test-uuid"
        assert task.hospital_id is None


class TestProcessExtractionTask:
    """Tests for process_extraction_task function."""

    def test_returns_false_when_lab_result_not_found(self):
        """Test returns False when lab result doesn't exist."""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = process_extraction_task(
            lab_result_id="nonexistent-uuid",
            db=mock_db,
        )

        assert result is False

    def test_updates_status_to_processing(self):
        """Test updates status to PROCESSING at start."""
        mock_lab_result = MagicMock(spec=LabResult)
        mock_lab_result.id = uuid4()
        mock_lab_result.original_file_path = "lab-results/uuid_test.pdf"
        mock_lab_result.extraction_status = ExtractionStatus.PENDING

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lab_result

        mock_storage = MagicMock()
        mock_storage.download_file.return_value = b"PDF content"

        mock_router = MagicMock()
        mock_router.extract_from_bytes.return_value = ExtractionRouteResult(
            file_type="pdf",
            extractor_used="pdf",
            extracted_data={"text": "test"},
            raw_content="test content",
            confidence=0.95,
        )
        mock_router.format_for_storage.return_value = {"source": "pdf", "data": {}}

        process_extraction_task(
            lab_result_id=str(mock_lab_result.id),
            db=mock_db,
            storage_service=mock_storage,
            extraction_router=mock_router,
        )

        # Verify status was set to PROCESSING
        assert mock_lab_result.extraction_status == ExtractionStatus.COMPLETED

    def test_successful_extraction_updates_lab_result(self):
        """Test successful extraction updates lab result correctly."""
        mock_lab_result = MagicMock(spec=LabResult)
        mock_lab_result.id = uuid4()
        mock_lab_result.original_file_path = "lab-results/uuid_test.pdf"
        mock_lab_result.extraction_status = ExtractionStatus.PENDING

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lab_result

        mock_storage = MagicMock()
        mock_storage.download_file.return_value = b"PDF content"

        extraction_result = ExtractionRouteResult(
            file_type="pdf",
            extractor_used="pdf",
            extracted_data={"text_content": "test data"},
            raw_content="test content",
            confidence=0.92,
        )
        storage_data = {"source": "pdf", "data": {"text_content": "test data"}}

        mock_router = MagicMock()
        mock_router.extract_from_bytes.return_value = extraction_result
        mock_router.format_for_storage.return_value = storage_data

        result = process_extraction_task(
            lab_result_id=str(mock_lab_result.id),
            db=mock_db,
            storage_service=mock_storage,
            extraction_router=mock_router,
        )

        assert result is True
        assert mock_lab_result.extraction_status == ExtractionStatus.COMPLETED
        assert mock_lab_result.extracted_data == storage_data
        assert mock_lab_result.extraction_confidence == 0.92
        mock_db.commit.assert_called()

    def test_download_failure_marks_as_failed(self):
        """Test download failure marks lab result as FAILED."""
        mock_lab_result = MagicMock(spec=LabResult)
        mock_lab_result.id = uuid4()
        mock_lab_result.original_file_path = "lab-results/uuid_test.pdf"
        mock_lab_result.extraction_status = ExtractionStatus.PENDING

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lab_result

        mock_storage = MagicMock()
        mock_storage.download_file.side_effect = Exception("Download failed")

        result = process_extraction_task(
            lab_result_id=str(mock_lab_result.id),
            db=mock_db,
            storage_service=mock_storage,
        )

        assert result is False
        assert mock_lab_result.extraction_status == ExtractionStatus.FAILED
        assert "Download failed" in mock_lab_result.extracted_data["error"]

    def test_extraction_failure_marks_as_failed(self):
        """Test extraction failure marks lab result as FAILED."""
        mock_lab_result = MagicMock(spec=LabResult)
        mock_lab_result.id = uuid4()
        mock_lab_result.original_file_path = "lab-results/uuid_test.pdf"
        mock_lab_result.extraction_status = ExtractionStatus.PENDING

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lab_result

        mock_storage = MagicMock()
        mock_storage.download_file.return_value = b"PDF content"

        mock_router = MagicMock()
        mock_router.extract_from_bytes.side_effect = ExtractionRouterError("Extraction failed")

        result = process_extraction_task(
            lab_result_id=str(mock_lab_result.id),
            db=mock_db,
            storage_service=mock_storage,
            extraction_router=mock_router,
        )

        assert result is False
        assert mock_lab_result.extraction_status == ExtractionStatus.FAILED
        assert "Extraction failed" in mock_lab_result.extracted_data["error"]

    def test_extracts_filename_from_path_with_uuid_prefix(self):
        """Test correct filename extraction from storage path."""
        mock_lab_result = MagicMock(spec=LabResult)
        mock_lab_result.id = uuid4()
        mock_lab_result.original_file_path = "lab-results/abc123_test_file.pdf"
        mock_lab_result.extraction_status = ExtractionStatus.PENDING

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lab_result

        mock_storage = MagicMock()
        mock_storage.download_file.return_value = b"PDF content"

        mock_router = MagicMock()
        mock_router.extract_from_bytes.return_value = ExtractionRouteResult(
            file_type="pdf",
            extractor_used="pdf",
            extracted_data={},
            raw_content="",
            confidence=0.9,
        )
        mock_router.format_for_storage.return_value = {}

        process_extraction_task(
            lab_result_id=str(mock_lab_result.id),
            db=mock_db,
            storage_service=mock_storage,
            extraction_router=mock_router,
        )

        # Verify extract_from_bytes was called with correct filename
        mock_router.extract_from_bytes.assert_called_once()
        call_args = mock_router.extract_from_bytes.call_args
        assert call_args.kwargs["filename"] == "test_file.pdf"

    def test_creates_db_session_when_not_provided(self):
        """Test creates database session when not provided."""
        with patch("src.workers.extraction_task.SessionLocal") as mock_session_local:
            mock_db = MagicMock(spec=Session)
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_session_local.return_value = mock_db

            process_extraction_task(lab_result_id="test-uuid")

            mock_session_local.assert_called_once()
            mock_db.close.assert_called_once()

    def test_closes_db_session_only_when_created(self):
        """Test doesn't close session when provided externally."""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        process_extraction_task(
            lab_result_id="test-uuid",
            db=mock_db,
        )

        mock_db.close.assert_not_called()

    def test_passes_hospital_id_to_extraction_router(self):
        """Test hospital_id is passed to extraction router factory."""
        mock_lab_result = MagicMock(spec=LabResult)
        mock_lab_result.id = uuid4()
        mock_lab_result.original_file_path = "lab-results/uuid_test.pdf"

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lab_result

        mock_storage = MagicMock()
        mock_storage.download_file.return_value = b"content"

        with patch("src.workers.extraction_task.get_extraction_router_service") as mock_get_router:
            mock_router = MagicMock()
            mock_router.extract_from_bytes.return_value = ExtractionRouteResult(
                file_type="pdf",
                extractor_used="pdf",
                extracted_data={},
                raw_content="",
                confidence=0.9,
            )
            mock_router.format_for_storage.return_value = {}
            mock_get_router.return_value = mock_router

            process_extraction_task(
                lab_result_id=str(mock_lab_result.id),
                hospital_id="hospital-001",
                db=mock_db,
                storage_service=mock_storage,
            )

            mock_get_router.assert_called_once_with(
                anthropic_client=None,
                hospital_id="hospital-001",
            )


class TestMarkFailed:
    """Tests for _mark_failed helper function."""

    def test_sets_failed_status(self):
        """Test sets extraction status to FAILED."""
        mock_lab_result = MagicMock(spec=LabResult)
        mock_db = MagicMock(spec=Session)

        _mark_failed(mock_db, mock_lab_result, "Test error")

        assert mock_lab_result.extraction_status == ExtractionStatus.FAILED

    def test_stores_error_message(self):
        """Test stores error message in extracted_data."""
        mock_lab_result = MagicMock(spec=LabResult)
        mock_db = MagicMock(spec=Session)

        _mark_failed(mock_db, mock_lab_result, "Download failed: connection error")

        assert mock_lab_result.extracted_data["error"] == "Download failed: connection error"
        assert "failed_at" in mock_lab_result.extracted_data

    def test_commits_changes(self):
        """Test commits database changes."""
        mock_lab_result = MagicMock(spec=LabResult)
        mock_db = MagicMock(spec=Session)

        _mark_failed(mock_db, mock_lab_result, "Error")

        mock_db.commit.assert_called_once()


class TestCreateExtractionBackgroundTask:
    """Tests for create_extraction_background_task factory function."""

    def test_returns_callable(self):
        """Test returns a callable."""
        task = create_extraction_background_task(lab_result_id="test-uuid")

        assert callable(task)

    def test_callable_calls_process_extraction_task(self):
        """Test callable invokes process_extraction_task with correct args."""
        with patch("src.workers.extraction_task.process_extraction_task") as mock_process:
            mock_process.return_value = True

            task = create_extraction_background_task(
                lab_result_id="test-uuid",
                hospital_id="hospital-001",
            )
            result = task()

            assert result is True
            mock_process.assert_called_once_with(
                lab_result_id="test-uuid",
                hospital_id="hospital-001",
                anthropic_client=None,
            )

    def test_passes_anthropic_client(self):
        """Test anthropic_client is passed through."""
        mock_client = MagicMock()

        with patch("src.workers.extraction_task.process_extraction_task") as mock_process:
            mock_process.return_value = True

            task = create_extraction_background_task(
                lab_result_id="test-uuid",
                anthropic_client=mock_client,
            )
            task()

            mock_process.assert_called_once_with(
                lab_result_id="test-uuid",
                hospital_id=None,
                anthropic_client=mock_client,
            )


class TestIntegrationWithFastAPIBackgroundTasks:
    """Integration tests for FastAPI BackgroundTasks compatibility."""

    def test_task_can_be_added_to_background_tasks(self):
        """Test task can be added to FastAPI BackgroundTasks."""
        from fastapi import BackgroundTasks

        background_tasks = BackgroundTasks()
        task = create_extraction_background_task(lab_result_id="test-uuid")

        # This should not raise
        background_tasks.add_task(task)

        # Verify task was added
        assert len(background_tasks.tasks) == 1

    def test_multiple_tasks_can_be_added(self):
        """Test multiple tasks can be added to BackgroundTasks."""
        from fastapi import BackgroundTasks

        background_tasks = BackgroundTasks()

        task1 = create_extraction_background_task(lab_result_id="uuid-1")
        task2 = create_extraction_background_task(lab_result_id="uuid-2")

        background_tasks.add_task(task1)
        background_tasks.add_task(task2)

        assert len(background_tasks.tasks) == 2
