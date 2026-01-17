"""Cloudflare R2 storage service."""

import logging
import mimetypes
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from aiobotocore.session import get_session

from app.core.configs import app_config
from app.core.services.storage.base_service import StorageServiceInterface
from app.core.services.storage.schemas import StorageFile, StorageProvider, UploadRequest

logger = logging.getLogger(__name__)


class R2StorageService(StorageServiceInterface):
    """Cloudflare R2 storage service implementation."""

    def __init__(self) -> None:
        if not app_config.R2_BUCKET:
            raise ValueError('R2_BUCKET is not set.')
        if not app_config.R2_ACCESS_KEY_ID or not app_config.R2_SECRET_ACCESS_KEY:
            raise ValueError('R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY are required.')
        if not app_config.R2_ENDPOINT_URL:
            raise ValueError('R2_ENDPOINT_URL is required for Cloudflare R2.')
        self._session = get_session()

    @asynccontextmanager
    async def _get_client(self):
        """Create a fresh S3-compatible client for R2."""
        async with self._session.create_client(
            's3',
            endpoint_url=app_config.R2_ENDPOINT_URL,
            aws_access_key_id=app_config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=app_config.R2_SECRET_ACCESS_KEY,
            region_name='auto',
        ) as client:
            yield client

    @property
    def bucket(self) -> str:
        return app_config.R2_BUCKET or ''

    @property
    def public_url_base(self) -> str | None:
        return app_config.R2_PUBLIC_BASE_URL

    def _generate_key(self, filename: str | None = None, content_type: str | None = None) -> str:
        """Generate a unique key for a file."""
        unique_id = uuid.uuid4().hex[:12]
        timestamp = datetime.utcnow().strftime('%Y/%m/%d')

        if filename:
            safe_name = ''.join(c for c in filename if c.isalnum() or c in '.-_')
            return f'{timestamp}/{unique_id}_{safe_name}'

        ext = ''
        if content_type:
            ext = mimetypes.guess_extension(content_type) or ''

        return f'{timestamp}/{unique_id}{ext}'

    def _get_public_url(self, key: str) -> str:
        """Get the public URL for a file."""
        if self.public_url_base:
            return f'{self.public_url_base.rstrip("/")}/{key}'
        return f'{app_config.R2_ENDPOINT_URL}/{self.bucket}/{key}'

    async def upload(self, request: UploadRequest) -> StorageFile:
        """Upload a file to R2."""
        data: bytes
        if request.data:
            data = request.data
        elif request.file_path:
            with open(request.file_path, 'rb') as f:
                data = f.read()
        elif request.url:
            return await self.upload_from_url(request.url, request.key)
        else:
            raise ValueError('No data source provided in upload request')

        key = request.key or self._generate_key(request.filename, request.content_type)

        content_type = request.content_type
        if not content_type and request.filename:
            content_type, _ = mimetypes.guess_type(request.filename)
        if not content_type:
            content_type = 'application/octet-stream'

        # Debug: log bucket value before upload
        bucket_value = self.bucket
        logger.info(f'R2 upload: bucket={bucket_value!r}, key={key}, R2_BUCKET={app_config.R2_BUCKET!r}')

        if not bucket_value:
            raise ValueError(f'R2 bucket is empty! R2_BUCKET={app_config.R2_BUCKET!r}')

        upload_params: dict[str, Any] = {
            'Bucket': bucket_value,
            'Key': key,
            'Body': data,
            'ContentType': content_type,
        }

        if request.metadata:
            upload_params['Metadata'] = request.metadata

        async with self._get_client() as s3:
            await s3.put_object(**upload_params)

        url = self._get_public_url(key)

        return StorageFile(
            key=key,
            url=url,
            content_type=content_type,
            size_bytes=len(data),
            bucket=self.bucket,
            provider=StorageProvider.R2,
            metadata=request.metadata,
        )

    async def upload_from_url(self, url: str, key: str | None = None) -> StorageFile:
        """Download from URL and upload to R2."""
        async with httpx.AsyncClient(timeout=300.0) as http_client:
            response = await http_client.get(url, follow_redirects=True)
            response.raise_for_status()

            content_type = response.headers.get('content-type', 'application/octet-stream')
            data = response.content

        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1] if parsed_url.path else None

        request = UploadRequest(
            data=data,
            key=key,
            content_type=content_type,
            filename=filename,
        )

        return await self.upload(request)

    async def get_url(self, key: str, expires_in_seconds: int | None = None) -> str:
        """Get the URL for a file."""
        if self.public_url_base and not expires_in_seconds:
            return self._get_public_url(key)

        if expires_in_seconds:
            async with self._get_client() as s3:
                return await s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': key},
                    ExpiresIn=expires_in_seconds,
                )

        return self._get_public_url(key)
