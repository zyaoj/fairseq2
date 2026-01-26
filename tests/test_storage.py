"""Tests for StorageService."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from src.services.storage import StorageError, StorageService, get_storage_service


class MockS3Error(Exception):
    """Mock S3 error for testing."""

    def __init__(self, code: str = "Unknown", message: str = "Error"):
        self.code = code
        self.message = message
        super().__init__(message)


class TestStorageService:
    """Tests for StorageService initialization."""

    def test_get_storage_service_returns_instance(self):
        """Test that get_storage_service returns a StorageService instance."""
        service = get_storage_service()
        assert isinstance(service, StorageService)

    def test_init_with_custom_settings(self):
        """Test initialization with custom settings."""
        mock_settings = MagicMock()
        mock_settings.minio_endpoint = "test:9000"
        mock_settings.minio_access_key = "test_key"
        mock_settings.minio_secret_key = "test_secret"
        mock_settings.minio_bucket = "test-bucket"
        mock_settings.minio_secure = False

        service = StorageService(settings=mock_settings)
        assert service.bucket_name == "test-bucket"

    def test_init_with_custom_client(self):
        """Test initialization with custom MinIO client."""
        mock_client = MagicMock()
        service = StorageService(client=mock_client)
        assert service.client == mock_client


class TestFileTypeDetection:
    """Tests for file type detection."""

    def test_detect_pdf(self):
        """Test detecting PDF files."""
        service = get_storage_service()
        assert service.detect_file_type("report.pdf") == "pdf"
        assert service.detect_file_type("REPORT.PDF") == "pdf"

    def test_detect_docx(self):
        """Test detecting Word document files."""
        service = get_storage_service()
        assert service.detect_file_type("document.docx") == "docx"
        assert service.detect_file_type("document.doc") == "docx"

    def test_detect_image(self):
        """Test detecting image files."""
        service = get_storage_service()
        assert service.detect_file_type("scan.png") == "image"
        assert service.detect_file_type("photo.jpg") == "image"
        assert service.detect_file_type("photo.jpeg") == "image"
        assert service.detect_file_type("image.gif") == "image"
        assert service.detect_file_type("image.bmp") == "image"
        assert service.detect_file_type("scan.tiff") == "image"
        assert service.detect_file_type("scan.tif") == "image"

    def test_detect_unknown(self):
        """Test detecting unknown file types."""
        service = get_storage_service()
        assert service.detect_file_type("file.xyz") == "unknown"
        assert service.detect_file_type("noextension") == "unknown"


class TestFileUpload:
    """Tests for file upload functionality."""

    @pytest.fixture
    def mock_minio_client(self):
        """Create a mock MinIO client."""
        client = MagicMock()
        client.bucket_exists.return_value = True
        client.put_object.return_value = None
        return client

    def test_upload_file_bytes(self, mock_minio_client: MagicMock):
        """Test uploading file from bytes."""
        service = StorageService(client=mock_minio_client)

        content = b"test file content"
        result = service.upload_file(content, "test.pdf")

        assert result.startswith("lab-results/")
        assert result.endswith(".pdf")
        mock_minio_client.put_object.assert_called_once()

    def test_upload_file_bytesio(self, mock_minio_client: MagicMock):
        """Test uploading file from BytesIO."""
        service = StorageService(client=mock_minio_client)

        content = BytesIO(b"test file content")
        result = service.upload_file(content, "test.png")

        assert result.startswith("lab-results/")
        assert result.endswith(".png")

    def test_upload_file_custom_folder(self, mock_minio_client: MagicMock):
        """Test uploading file to custom folder."""
        service = StorageService(client=mock_minio_client)

        content = b"test"
        result = service.upload_file(content, "test.pdf", folder="documents")

        assert result.startswith("documents/")

    def test_upload_creates_bucket_if_not_exists(self, mock_minio_client: MagicMock):
        """Test that upload creates bucket if it doesn't exist."""
        mock_minio_client.bucket_exists.return_value = False
        service = StorageService(client=mock_minio_client)

        service.upload_file(b"test", "test.pdf")

        mock_minio_client.make_bucket.assert_called_once()

    def test_upload_file_correct_content_type(self, mock_minio_client: MagicMock):
        """Test that upload sets correct content type."""
        service = StorageService(client=mock_minio_client)

        service.upload_file(b"test", "test.pdf")

        call_args = mock_minio_client.put_object.call_args
        assert call_args[1]["content_type"] == "application/pdf"


class TestFileDownload:
    """Tests for file download functionality."""

    @pytest.fixture
    def mock_minio_client(self):
        """Create a mock MinIO client with download support."""
        client = MagicMock()

        # Mock response object
        response = MagicMock()
        response.read.return_value = b"file content"
        client.get_object.return_value = response

        return client

    def test_download_file(self, mock_minio_client: MagicMock):
        """Test downloading a file."""
        service = StorageService(client=mock_minio_client)

        result = service.download_file("lab-results/test.pdf")

        assert result == b"file content"
        mock_minio_client.get_object.assert_called_once()


class TestFileOperations:
    """Tests for miscellaneous file operations."""

    @pytest.fixture
    def mock_minio_client(self):
        """Create a mock MinIO client."""
        return MagicMock()

    def test_delete_file(self, mock_minio_client: MagicMock):
        """Test deleting a file."""
        service = StorageService(client=mock_minio_client)

        service.delete_file("lab-results/test.pdf")

        mock_minio_client.remove_object.assert_called_once()

    def test_file_exists_true(self, mock_minio_client: MagicMock):
        """Test file_exists returns True when file exists."""
        mock_minio_client.stat_object.return_value = MagicMock()
        service = StorageService(client=mock_minio_client)

        assert service.file_exists("lab-results/test.pdf") is True

    def test_file_exists_false(self, mock_minio_client: MagicMock):
        """Test file_exists returns False when file doesn't exist."""
        from minio.error import S3Error

        mock_minio_client.stat_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Not found",
            resource="/test",
            request_id="123",
            host_id="host",
            response=None,
        )
        service = StorageService(client=mock_minio_client)

        assert service.file_exists("lab-results/nonexistent.pdf") is False

    def test_get_file_info(self, mock_minio_client: MagicMock):
        """Test getting file info."""
        mock_stat = MagicMock()
        mock_stat.size = 1024
        mock_stat.content_type = "application/pdf"
        mock_stat.last_modified = "2024-01-01T00:00:00Z"
        mock_stat.etag = "abc123"
        mock_minio_client.stat_object.return_value = mock_stat

        service = StorageService(client=mock_minio_client)
        info = service.get_file_info("lab-results/test.pdf")

        assert info["size"] == 1024
        assert info["content_type"] == "application/pdf"
        assert info["etag"] == "abc123"

    def test_get_presigned_url(self, mock_minio_client: MagicMock):
        """Test generating presigned URL."""
        mock_minio_client.presigned_get_object.return_value = "https://minio/presigned-url"
        service = StorageService(client=mock_minio_client)

        url = service.get_presigned_url("lab-results/test.pdf")

        assert url == "https://minio/presigned-url"
        mock_minio_client.presigned_get_object.assert_called_once()

    def test_get_presigned_url_custom_expiry(self, mock_minio_client: MagicMock):
        """Test generating presigned URL with custom expiry."""
        from datetime import timedelta

        mock_minio_client.presigned_get_object.return_value = "https://minio/url"
        service = StorageService(client=mock_minio_client)

        service.get_presigned_url("lab-results/test.pdf", expires_hours=24)

        call_args = mock_minio_client.presigned_get_object.call_args
        assert call_args[1]["expires"] == timedelta(hours=24)


class TestContentTypes:
    """Tests for content type mapping."""

    def test_content_types_are_valid(self):
        """Test that all content types are valid MIME types."""
        for ext, content_type in StorageService.CONTENT_TYPES.items():
            assert ext.startswith(".")
            assert "/" in content_type
