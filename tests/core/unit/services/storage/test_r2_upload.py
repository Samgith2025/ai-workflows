"""R2 storage upload tests.

These tests upload real files to R2.
Requires R2 credentials to be configured.
"""

import pytest

from app.core.configs import app_config
from app.core.services.storage import get_storage
from app.core.services.storage.providers.r2.service import R2StorageService
from app.core.services.storage.schemas import StorageProvider, UploadRequest

# Skip if R2 is not configured
pytestmark = pytest.mark.skipif(
    app_config.storage_provider != 'r2',
    reason='R2 not configured (requires R2_BUCKET, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY)',
)


class TestR2Upload:
    """Test R2 upload functionality."""

    @pytest.mark.manual
    @pytest.mark.asyncio
    async def test_upload_simple_bytes(self):
        """Upload a simple 1-byte file to R2."""
        # Debug: Print current config values
        print(f'R2_BUCKET: {app_config.R2_BUCKET!r}')
        print(f'R2_ENDPOINT_URL: {app_config.R2_ENDPOINT_URL!r}')
        print(f'R2_ACCESS_KEY_ID set: {bool(app_config.R2_ACCESS_KEY_ID)}')
        print(f'R2_SECRET_ACCESS_KEY set: {bool(app_config.R2_SECRET_ACCESS_KEY)}')
        print(f'storage_provider: {app_config.storage_provider}')

        service = R2StorageService()

        # Debug: Check service properties
        print(f'service.bucket: {service.bucket!r}')
        print(f'service.public_url_base: {service.public_url_base!r}')

        # Create minimal test data - 1 byte
        data = b'X'

        request = UploadRequest(
            data=data,
            content_type='application/octet-stream',
            filename='test.bin',
        )

        result = await service.upload(request)

        assert result.key is not None
        assert result.url is not None
        assert result.size_bytes == 1
        assert result.provider == StorageProvider.R2
        assert result.bucket == service.bucket

        print(f'Uploaded successfully to: {result.url}')

    @pytest.mark.manual
    @pytest.mark.asyncio
    async def test_upload_image_bytes(self):
        """Upload a minimal PNG image to R2."""
        service = R2StorageService()

        # Minimal valid 1x1 transparent PNG (67 bytes)
        png_data = bytes(
            [
                0x89,
                0x50,
                0x4E,
                0x47,
                0x0D,
                0x0A,
                0x1A,
                0x0A,  # PNG signature
                0x00,
                0x00,
                0x00,
                0x0D,
                0x49,
                0x48,
                0x44,
                0x52,  # IHDR chunk
                0x00,
                0x00,
                0x00,
                0x01,
                0x00,
                0x00,
                0x00,
                0x01,  # 1x1
                0x08,
                0x06,
                0x00,
                0x00,
                0x00,
                0x1F,
                0x15,
                0xC4,
                0x89,
                0x00,
                0x00,
                0x00,
                0x0A,
                0x49,
                0x44,
                0x41,  # IDAT chunk
                0x54,
                0x78,
                0x9C,
                0x63,
                0x00,
                0x01,
                0x00,
                0x00,
                0x05,
                0x00,
                0x01,
                0x0D,
                0x0A,
                0x2D,
                0xB4,
                0x00,
                0x00,
                0x00,
                0x00,
                0x49,
                0x45,
                0x4E,
                0x44,
                0xAE,  # IEND chunk
                0x42,
                0x60,
                0x82,
            ]
        )

        request = UploadRequest(
            data=png_data,
            content_type='image/png',
            filename='test.png',
        )

        result = await service.upload(request)

        assert result.key is not None
        assert result.url is not None
        assert result.content_type == 'image/png'
        assert result.provider == StorageProvider.R2
        assert 'test.png' in result.key or result.key.endswith('.png')

        print(f'Uploaded PNG to: {result.url}')

    @pytest.mark.manual
    @pytest.mark.asyncio
    async def test_upload_with_custom_key(self):
        """Upload with a custom key."""
        service = R2StorageService()

        data = b'test content'
        custom_key = 'test-uploads/custom-key-test.txt'

        request = UploadRequest(
            data=data,
            key=custom_key,
            content_type='text/plain',
        )

        result = await service.upload(request)

        assert result.key == custom_key
        assert result.url is not None
        assert custom_key in result.url

        print(f'Uploaded with custom key to: {result.url}')

    @pytest.mark.manual
    @pytest.mark.asyncio
    async def test_upload_via_get_storage_singleton(self):
        """Test upload using get_storage() singleton (like activities do)."""
        # This mirrors how the storage activity calls the service
        storage = get_storage()

        print(f'Storage service type: {type(storage).__name__}')
        print(f'Storage bucket: {storage.bucket!r}')

        data = b'singleton test'
        request = UploadRequest(
            data=data,
            key='test-uploads/singleton-test.txt',
            content_type='text/plain',
        )

        result = await storage.upload(request)

        assert result.key is not None
        assert result.url is not None
        print(f'Uploaded via singleton to: {result.url}')

    @pytest.mark.manual
    @pytest.mark.asyncio
    async def test_upload_to_storage_activity_directly(self):
        """Test the upload_to_storage activity function directly.

        This calls the same code path as the Temporal workflow but without Temporal.
        """
        # Import the activity and schema
        from app.temporal.activities.storage import upload_to_storage
        from app.temporal.schemas import StorageUploadInput

        # Use a known working image URL (a small test image)
        test_url = 'https://httpbin.org/image/png'

        input_data = StorageUploadInput(
            url=test_url,
            folder='test-activity',
        )

        # Call the activity function directly (not through Temporal)
        # We need to mock the activity context since we're not in Temporal
        from unittest.mock import MagicMock, patch

        mock_logger = MagicMock()
        with patch('temporalio.activity.logger', mock_logger):
            result = await upload_to_storage(input_data)

        assert result.url is not None
        assert result.key is not None
        print(f'Activity uploaded to: {result.url}')
