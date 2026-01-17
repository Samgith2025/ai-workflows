"""AWS S3 storage service."""

import mimetypes
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from aiobotocore.session import get_session

from app.core.configs import app_config
from app.core.services.storage.base_service import StorageServiceInterface
from app.core.services.storage.schemas import StorageFile, StorageProvider, UploadRequest


class S3StorageService(StorageServiceInterface):
    """S3 storage service implementation."""

    def __init__(self):
        if not app_config.S3_BUCKET:
            raise ValueError('S3_BUCKET is not set. Please set it in your environment or .env file.')
        if not app_config.S3_ACCESS_KEY or not app_config.S3_SECRET_KEY:
            raise ValueError('S3_ACCESS_KEY and S3_SECRET_KEY are required.')
        self._client = None

    async def _get_client(self):
        """Get or create the S3 client."""
        if self._client is None:
            session = get_session()
            config = {
                'region_name': app_config.S3_REGION,
                'aws_access_key_id': app_config.S3_ACCESS_KEY,
                'aws_secret_access_key': app_config.S3_SECRET_KEY,
            }
            if app_config.S3_ENDPOINT_URL:
                config['endpoint_url'] = app_config.S3_ENDPOINT_URL

            self._client = session.create_client('s3', **config)
        return self._client

    @property
    def bucket(self) -> str:
        return app_config.storage_bucket or ''

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

    async def upload(self, request: UploadRequest) -> StorageFile:
        """Upload a file to S3."""
        client = await self._get_client()

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

        upload_params: dict[str, Any] = {
            'Bucket': self.bucket,
            'Key': key,
            'Body': data,
            'ContentType': content_type,
        }

        if request.public:
            upload_params['ACL'] = 'public-read'

        if request.metadata:
            upload_params['Metadata'] = request.metadata

        async with client as s3:
            await s3.put_object(**upload_params)

        url = await self.get_url(key)

        return StorageFile(
            key=key,
            url=url,
            content_type=content_type,
            size_bytes=len(data),
            bucket=self.bucket,
            provider=StorageProvider.S3,
            metadata=request.metadata,
        )

    async def upload_from_url(self, url: str, key: str | None = None) -> StorageFile:
        """Download from URL and upload to S3."""
        async with httpx.AsyncClient(timeout=300.0) as http_client:
            response = await http_client.get(url)
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
        if app_config.S3_PUBLIC_URL_BASE and not expires_in_seconds:
            return f'{app_config.S3_PUBLIC_URL_BASE.rstrip("/")}/{key}'

        if expires_in_seconds:
            client = await self._get_client()
            async with client as s3:
                return await s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': key},
                    ExpiresIn=expires_in_seconds,
                )

        if app_config.S3_ENDPOINT_URL:
            return f'{app_config.S3_ENDPOINT_URL}/{self.bucket}/{key}'
        return f'https://{self.bucket}.s3.{app_config.S3_REGION}.amazonaws.com/{key}'
