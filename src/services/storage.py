"""File storage service using MinIO.

This service provides file storage operations using MinIO (S3-compatible storage).
It supports uploading, downloading, and deleting files for lab results and other
clinical documents.
"""

import logging
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

logger = logging.getLogger(__name__)

from minio import Minio
from minio.error import S3Error

from src.core.config import Settings, get_settings


class StorageError(Exception):
    """Raised when storage operations fail."""

    pass


class StorageService:
    """Service for file storage using MinIO.

    This service handles:
    - File uploads with automatic content type detection
    - File downloads
    - File deletion
    - Generating presigned URLs for direct access
    """

    # Supported file types and their MIME types
    CONTENT_TYPES = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }

    def __init__(
        self,
        settings: Settings | None = None,
        client: Minio | None = None,
    ):
        """Initialize the storage service.

        Args:
            settings: Application settings. Defaults to global settings.
            client: Optional Minio client for testing. If not provided,
                   creates a client from settings.
        """
        self.settings = settings or get_settings()
        self._client = client
        self._bucket_ensured = False

    @property
    def client(self) -> Minio:
        """Get or create the MinIO client."""
        if self._client is None:
            self._client = Minio(
                self.settings.minio_endpoint,
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key,
                secure=self.settings.minio_secure,
            )
        return self._client

    @property
    def bucket_name(self) -> str:
        """Get the bucket name from settings."""
        return self.settings.minio_bucket

    def ensure_bucket(self) -> None:
        """Ensure the storage bucket exists, creating it if necessary."""
        if self._bucket_ensured:
            return

        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
            self._bucket_ensured = True
        except S3Error as e:
            raise StorageError(f"Failed to ensure bucket exists: {e}") from e

    def upload_file(
        self,
        file_content: bytes | BytesIO | BinaryIO,
        original_filename: str,
        folder: str = "lab-results",
    ) -> str:
        """Upload a file to storage.

        Args:
            file_content: File content as bytes or file-like object
            original_filename: Original filename (used for extension detection)
            folder: Folder/prefix in the bucket (default: "lab-results")

        Returns:
            Object key (path) of the uploaded file

        Raises:
            StorageError: If upload fails
        """
        self.ensure_bucket()

        # Generate unique object key
        ext = Path(original_filename).suffix.lower()
        object_key = f"{folder}/{uuid4()}{ext}"

        # Determine content type
        content_type = self.CONTENT_TYPES.get(ext, "application/octet-stream")

        # Convert bytes to BytesIO if needed
        if isinstance(file_content, bytes):
            file_content = BytesIO(file_content)

        # Get file size
        file_content.seek(0, 2)  # Seek to end
        file_size = file_content.tell()
        file_content.seek(0)  # Reset to beginning

        try:
            self.client.put_object(
                self.bucket_name,
                object_key,
                file_content,
                length=file_size,
                content_type=content_type,
            )
            return object_key
        except S3Error as e:
            raise StorageError(f"Failed to upload file: {e}") from e

    def download_file(self, object_key: str) -> bytes:
        """Download a file from storage.

        Args:
            object_key: Object key (path) of the file

        Returns:
            File content as bytes

        Raises:
            StorageError: If download fails or file not found
        """
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise StorageError(f"File not found: {object_key}") from e
            raise StorageError(f"Failed to download file: {e}") from e

    def delete_file(self, object_key: str) -> None:
        """Delete a file from storage.

        Args:
            object_key: Object key (path) of the file

        Raises:
            StorageError: If deletion fails
        """
        try:
            self.client.remove_object(self.bucket_name, object_key)
        except S3Error as e:
            raise StorageError(f"Failed to delete file: {e}") from e

    def get_presigned_url(
        self,
        object_key: str,
        expires_hours: int = 1,
    ) -> str:
        """Get a presigned URL for temporary access to a file.

        Args:
            object_key: Object key (path) of the file
            expires_hours: Hours until the URL expires (default: 1)

        Returns:
            Presigned URL string

        Raises:
            StorageError: If URL generation fails
        """
        from datetime import timedelta

        try:
            return self.client.presigned_get_object(
                self.bucket_name,
                object_key,
                expires=timedelta(hours=expires_hours),
            )
        except S3Error as e:
            raise StorageError(f"Failed to generate presigned URL: {e}") from e

    def file_exists(self, object_key: str) -> bool:
        """Check if a file exists in storage.

        Args:
            object_key: Object key (path) of the file

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(self.bucket_name, object_key)
            return True
        except S3Error:
            return False

    def get_file_info(self, object_key: str) -> dict:
        """Get metadata about a file.

        Args:
            object_key: Object key (path) of the file

        Returns:
            Dictionary with file metadata (size, content_type, last_modified)

        Raises:
            StorageError: If file not found or operation fails
        """
        try:
            stat = self.client.stat_object(self.bucket_name, object_key)
            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
            }
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise StorageError(f"File not found: {object_key}") from e
            raise StorageError(f"Failed to get file info: {e}") from e

    def detect_file_type(self, filename: str) -> str:
        """Detect file type category from filename.

        Args:
            filename: Filename with extension

        Returns:
            File type category: "pdf", "image", "docx", or "unknown"
        """
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            return "pdf"
        elif ext in (".docx", ".doc"):
            return "docx"
        elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif"):
            return "image"
        else:
            return "unknown"


# Singleton instance
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get the storage service singleton.

    Returns:
        StorageService instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
