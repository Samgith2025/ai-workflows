from abc import ABC, abstractmethod

from app.core.services.storage.schemas import StorageFile, UploadRequest


class StorageServiceInterface(ABC):
    """Interface for storage services."""

    @abstractmethod
    async def upload(self, request: UploadRequest) -> StorageFile:
        """Upload a file to storage.

        Args:
            request: Upload request with source data and destination info

        Returns:
            StorageFile with the uploaded file's URL and metadata
        """
        raise NotImplementedError

    @abstractmethod
    async def upload_from_url(self, url: str, key: str | None = None) -> StorageFile:
        """Download a file from a URL and upload it to storage.

        Args:
            url: Source URL to download from
            key: Destination key (auto-generated if not provided)

        Returns:
            StorageFile with the uploaded file's URL and metadata
        """
        raise NotImplementedError

    @abstractmethod
    async def get_url(self, key: str, expires_in_seconds: int | None = None) -> str:
        """Get the URL for a file.

        Args:
            key: File key in storage
            expires_in_seconds: Generate a signed URL with this expiration

        Returns:
            Public or signed URL to the file
        """
        raise NotImplementedError
