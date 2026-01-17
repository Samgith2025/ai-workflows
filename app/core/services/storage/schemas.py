from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class StorageProvider(str, Enum):
    """Supported storage providers."""

    S3 = 's3'
    R2 = 'r2'


class StorageFile(BaseModel):
    """Represents a file in storage."""

    key: str = Field(description='Unique file key/path in storage')
    url: str = Field(description='Public or signed URL to access the file')

    # File metadata
    content_type: str | None = Field(None, description='MIME type of the file')
    size_bytes: int | None = Field(None, description='File size in bytes')

    # Storage metadata
    bucket: str = Field(description='Bucket/container name')
    provider: StorageProvider = Field(description='Storage provider')

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Custom metadata
    metadata: dict[str, str] | None = Field(None, description='Custom metadata attached to the file')


class UploadRequest(BaseModel):
    """Request to upload a file or data."""

    # Content source (one of these must be provided)
    data: bytes | None = Field(None, description='Raw bytes to upload')
    file_path: str | None = Field(None, description='Local file path to upload')
    url: str | None = Field(None, description='URL to download and re-upload')

    # Destination
    key: str | None = Field(None, description='Destination key/path (auto-generated if not provided)')

    # File metadata
    content_type: str | None = Field(None, description='MIME type (auto-detected if not provided)')
    filename: str | None = Field(None, description='Original filename')

    # Options
    public: bool = Field(True, description='Make the file publicly accessible')
    metadata: dict[str, str] | None = Field(None, description='Custom metadata to attach')
