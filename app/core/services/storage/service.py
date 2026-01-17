"""Storage service factory with auto-detection.

Automatically selects R2 or S3 based on configured credentials.
"""

from app.core.configs import app_config
from app.core.services.storage.base_service import StorageServiceInterface
from app.core.services.storage.schemas import StorageProvider


def get_storage_service(provider: StorageProvider | None = None) -> StorageServiceInterface:
    """Get a storage service instance.

    Args:
        provider: Explicit provider to use. If None, auto-detects based on config.

    Returns:
        StorageServiceInterface implementation

    Raises:
        ValueError: If no storage is configured or provider is unsupported
    """
    # Auto-detect if not specified
    if provider is None:
        detected = app_config.storage_provider
        if detected == 'r2':
            provider = StorageProvider.R2
        elif detected == 's3':
            provider = StorageProvider.S3
        else:
            raise ValueError(
                'No storage configured. Set either R2_* or S3_* environment variables. '
                'See .sample.env for required variables.'
            )

    if provider == StorageProvider.R2:
        from app.core.services.storage.providers.r2.service import R2StorageService

        return R2StorageService()

    if provider == StorageProvider.S3:
        from app.core.services.storage.providers.s3.service import S3StorageService

        return S3StorageService()

    raise ValueError(f'Unsupported storage provider: {provider}')


class _StorageServiceHolder:
    """Holder for singleton storage service instance."""

    instance: StorageServiceInterface | None = None


def get_storage() -> StorageServiceInterface:
    """Get the default storage service (singleton).

    Auto-detects the provider based on environment configuration.
    """
    if _StorageServiceHolder.instance is None:
        _StorageServiceHolder.instance = get_storage_service()
    return _StorageServiceHolder.instance
