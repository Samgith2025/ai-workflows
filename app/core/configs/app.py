from typing import Annotated, Literal

from pydantic import BeforeValidator, computed_field

from app.core.configs.base_config import BaseConfig


class AppConfig(BaseConfig):
    _default_secrets = [
        'REPLICATE_API_KEY',
        'ELEVENLABS_API_KEY',
        'CARTESIA_API_KEY',
        'OPENAI_API_KEY',
        'GEMINI_API_KEY',
        'S3_ACCESS_KEY',
        'S3_SECRET_KEY',
        'R2_ACCESS_KEY_ID',
        'R2_SECRET_ACCESS_KEY',
        'GPTMARKET_API_KEY',
        'WORKFLOW_SECRET_KEY',
    ]

    ENVIRONMENT: Literal['local', 'staging', 'production', 'testing'] = 'local'
    PROJECT_NAME: str = 'GPTMarket Generator'

    # Logging
    LOG_LEVEL: str = 'DEBUG'
    LOG_HANDLERS: Annotated[list[Literal['stream', 'file']] | str, BeforeValidator(BaseConfig._parse_list)] = ['stream']

    # Generation Services
    REPLICATE_API_KEY: str | None = None
    ELEVENLABS_API_KEY: str | None = None
    CARTESIA_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # LiteLLM Configuration
    LITELLM_PRIMARY_MODEL: str = 'gemini/gemini-2.0-flash'
    LITELLM_FALLBACK_MODEL: str = 'openai/gpt-5-nano'
    LITELLM_FALLBACK_ENABLED: bool = True
    LITELLM_MAX_RETRIES: int = 2
    LITELLM_TIMEOUT: int = 120

    # S3 Storage (AWS S3)
    S3_BUCKET: str | None = None
    S3_REGION: str = 'us-east-1'
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_ENDPOINT_URL: str | None = None
    S3_PUBLIC_URL_BASE: str | None = None

    # R2 Storage (Cloudflare R2)
    R2_BUCKET: str | None = None
    R2_ENDPOINT_URL: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_PUBLIC_BASE_URL: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def storage_provider(self) -> Literal['r2', 's3', 'none']:
        """Auto-detect storage provider based on configured credentials."""
        if self.R2_BUCKET and self.R2_ACCESS_KEY_ID and self.R2_SECRET_ACCESS_KEY:
            return 'r2'
        if self.S3_BUCKET and self.S3_ACCESS_KEY and self.S3_SECRET_KEY:
            return 's3'
        return 'none'

    @computed_field  # type: ignore[misc]
    @property
    def storage_bucket(self) -> str | None:
        """Get the active storage bucket."""
        if self.storage_provider == 'r2':
            return self.R2_BUCKET
        return self.S3_BUCKET

    @computed_field  # type: ignore[misc]
    @property
    def storage_public_url(self) -> str | None:
        """Get the public URL base for the active storage."""
        if self.storage_provider == 'r2':
            return self.R2_PUBLIC_BASE_URL
        return self.S3_PUBLIC_URL_BASE

    # Temporal
    TEMPORAL_HOST: str = 'localhost:7233'
    TEMPORAL_NAMESPACE: str = 'default'
    TEMPORAL_TASK_QUEUE: str = 'generation-queue'

    # Workflow Secret Authentication
    # When enabled, all workflow inputs must include a valid secret_key
    # This provides simple authentication at the workflow level
    # Hack because temporal doesn't support authentication with self hosted servers
    WORKFLOW_SECRET_ENABLED: bool = False
    WORKFLOW_SECRET_KEY: str | None = None  # Required when WORKFLOW_SECRET_ENABLED=True

    # Replicate API Token (alias for REPLICATE_API_KEY)
    REPLICATE_API_TOKEN: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def replicate_token(self) -> str | None:
        return self.REPLICATE_API_TOKEN or self.REPLICATE_API_KEY

    # Tools
    GPTMARKET_API_URL: str = 'https://www.gptmarket.io/api'
    GPTMARKET_API_KEY: str | None = None


app_config = AppConfig()
