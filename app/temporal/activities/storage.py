"""Storage activities for uploading generated content.

Supports both S3 and R2 with auto-detection based on config.
"""

import uuid
from datetime import datetime
from urllib.parse import urlparse

import httpx
from temporalio import activity

from app.core.services.storage.schemas import UploadRequest
from app.core.services.storage.service import get_storage
from app.temporal.schemas import StorageUploadInput, StorageUploadOutput


def generate_key(folder: str, extension: str) -> str:
    """Generate a unique storage key."""
    date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
    unique_id = uuid.uuid4().hex[:12]
    return f'{folder}/{date_prefix}/{unique_id}.{extension}'


def get_extension_from_content_type(content_type: str) -> str:
    """Get file extension from content type."""
    mapping = {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/webp': 'webp',
        'image/gif': 'gif',
        'video/mp4': 'mp4',
        'video/webm': 'webm',
        'video/quicktime': 'mov',
        'audio/mpeg': 'mp3',
        'audio/wav': 'wav',
        'audio/ogg': 'ogg',
    }
    # Handle content types with parameters like 'video/mp4; charset=utf-8'
    base_type = content_type.split(';')[0].strip().lower()
    return mapping.get(base_type, 'bin')


def get_extension_from_url(url: str) -> str | None:
    """Try to get extension from URL path."""
    parsed = urlparse(url)
    path = parsed.path
    if '.' in path:
        ext = path.rsplit('.', 1)[-1].lower()
        if ext in ('mp4', 'webm', 'mov', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'mp3', 'wav', 'ogg'):
            return ext
    return None


@activity.defn
async def upload_to_storage(input: StorageUploadInput) -> StorageUploadOutput:
    """Upload a file from URL to storage (S3 or R2).

    Auto-detects file extension from:
    1. Content-Type header from the source URL
    2. File extension in the URL path
    3. Falls back to 'bin' if unknown
    """
    activity.logger.info(f'Uploading from URL: {input.url[:50]}...')

    # First, try to get extension from URL
    url_extension = get_extension_from_url(input.url)

    # Download the file and get content type
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.get(input.url, follow_redirects=True)
        response.raise_for_status()
        data = response.content
        content_type = response.headers.get('content-type', '')

    # Determine extension: prefer content-type, then URL, then default
    if content_type:
        extension = get_extension_from_content_type(content_type)
        if extension == 'bin' and url_extension:
            extension = url_extension
    elif url_extension:
        extension = url_extension
    else:
        extension = 'bin'

    key = generate_key(input.folder, extension)

    storage = get_storage()
    result = await storage.upload(
        UploadRequest(
            data=data,
            key=key,
            content_type=content_type or 'application/octet-stream',
        )
    )

    activity.logger.info(f'Uploaded to: {result.key}')

    return StorageUploadOutput(url=result.url, key=result.key)


async def upload_bytes_to_storage(
    data: bytes,
    content_type: str,
    folder: str = 'uploads',
    extension: str | None = None,
) -> str:
    """Upload raw bytes to storage.

    This is a helper function called directly from other activities.
    NOT a Temporal activity - use upload_to_storage for that.
    """
    if extension is None:
        extension = get_extension_from_content_type(content_type)

    key = generate_key(folder, extension)
    storage = get_storage()

    result = await storage.upload(
        UploadRequest(
            data=data,
            key=key,
            content_type=content_type,
        )
    )

    return result.url
