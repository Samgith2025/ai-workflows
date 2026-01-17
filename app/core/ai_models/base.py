"""Base types for AI model definitions."""

from abc import abstractmethod
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class Provider(str, Enum):
    """Supported AI providers."""

    REPLICATE = 'replicate'
    RUNPOD = 'runpod'
    MODAL = 'modal'


class ModelCategory(str, Enum):
    """Category of the model."""

    IMAGE = 'image'
    VIDEO = 'video'
    AUDIO = 'audio'
    TEXT = 'text'


class ModelCapability(str, Enum):
    """Capabilities a model can have."""

    TEXT_TO_IMAGE = 'text_to_image'
    IMAGE_TO_IMAGE = 'image_to_image'
    INPAINTING = 'inpainting'
    UPSCALING = 'upscaling'
    TEXT_TO_VIDEO = 'text_to_video'
    IMAGE_TO_VIDEO = 'image_to_video'
    TEXT_TO_SPEECH = 'text_to_speech'
    SPEECH_TO_TEXT = 'speech_to_text'


class ProviderConfig(BaseModel):
    """Provider-specific configuration for a model."""

    provider: Provider
    model_id: str = Field(description='Provider-specific model identifier')
    version: str | None = Field(None, description='Model version (if applicable)')

    def get_full_model_string(self) -> str:
        """Get the full model string for API calls."""
        if self.version:
            return f'{self.model_id}:{self.version}'
        return self.model_id


class ModelInput(BaseModel):
    """Base class for model input schemas.

    Each model should define its own input class inheriting from this,
    with conversion methods for each supported provider.
    """

    @abstractmethod
    def to_replicate(self) -> dict[str, Any]:
        """Convert to Replicate API input format."""
        raise NotImplementedError('Subclass must implement to_replicate()')

    def to_fal(self) -> dict[str, Any]:
        """Convert to FAL API input format."""
        raise NotImplementedError(f'{self.__class__.__name__} does not support FAL')

    def to_runpod(self) -> dict[str, Any]:
        """Convert to RunPod API input format."""
        raise NotImplementedError(f'{self.__class__.__name__} does not support RunPod')

    def to_provider(self, provider: Provider) -> dict[str, Any]:
        """Convert to the specified provider's input format."""
        converters = {
            Provider.REPLICATE: self.to_replicate,
            Provider.RUNPOD: self.to_runpod,
        }
        converter = converters.get(provider)
        if not converter:
            raise ValueError(f'Unknown provider: {provider}')
        return converter()


class ModelDefinition(BaseModel):
    """Definition of an AI model.

    Contains metadata about a model and its provider configurations.
    """

    # Identification
    id: str = Field(description='Unique model ID (e.g., "hidream-fast")')
    name: str = Field(description='Human-readable model name')

    # Categorization
    category: ModelCategory = Field(description='Model category')
    capabilities: list[ModelCapability] = Field(default_factory=list)

    # Metadata
    description: str = Field('', description='Model description')
    author: str = Field('', description='Model author/organization')

    # Provider configurations
    provider_configs: dict[Provider, ProviderConfig] = Field(
        default_factory=dict,
        description='Provider-specific configurations',
    )

    # Performance hints
    avg_generation_time_seconds: float | None = Field(None)

    # Input schema class
    input_class: ClassVar[type[ModelInput]]

    @property
    def providers(self) -> list[Provider]:
        """Get list of supported providers."""
        return list(self.provider_configs.keys())

    def supports_provider(self, provider: Provider) -> bool:
        """Check if this model supports a provider."""
        return provider in self.provider_configs

    def get_provider_config(self, provider: Provider) -> ProviderConfig:
        """Get configuration for a specific provider."""
        if provider not in self.provider_configs:
            raise ValueError(f'Model {self.id} does not support provider {provider}')
        return self.provider_configs[provider]

    def get_input_schema(self) -> dict[str, Any]:
        """Get the JSON schema for this model's inputs."""
        return self.input_class.model_json_schema()

    def validate_input(self, input_data: dict[str, Any]) -> ModelInput:
        """Validate and parse input data against this model's schema."""
        return self.input_class.model_validate(input_data)

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
