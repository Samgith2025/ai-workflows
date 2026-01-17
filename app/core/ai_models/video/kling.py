"""Kling v2.6 video generation model by Kuaishou.

Available on:
- Replicate: kuaishou/kling-v2.6
"""

from typing import Any, Literal

from pydantic import Field

from app.core.ai_models.base import (
    ModelCapability,
    ModelCategory,
    ModelDefinition,
    ModelInput,
    Provider,
    ProviderConfig,
)
from app.core.ai_models.common import AspectRatio
from app.core.ai_models.registry import model_registry


class KlingV26Input(ModelInput):
    """Input schema for Kling v2.6 model."""

    prompt: str = Field(..., description='Text prompt for video generation')
    negative_prompt: str = Field('', description='Things you do not want to see in the video')
    start_image: str | None = Field(None, description='First frame of the video (URL)')
    image: str | None = Field(None, description='Alias for start_image (for compatibility)')
    aspect_ratio: AspectRatio = Field(
        AspectRatio.LANDSCAPE_16_9,
        description='Aspect ratio of the video. Ignored if start_image is provided.',
    )
    duration: Literal[5, 10] = Field(5, description='Duration of the video in seconds')
    generate_audio: bool = Field(False, description='Generate synchronized audio for the video')

    def to_replicate(self) -> dict[str, Any]:
        """Convert to Replicate API format."""
        result: dict[str, Any] = {
            'prompt': self.prompt,
            'duration': self.duration,
            'aspect_ratio': self.aspect_ratio.value,
            'generate_audio': self.generate_audio,
        }

        if self.negative_prompt:
            result['negative_prompt'] = self.negative_prompt

        # Support both start_image and image (alias)
        image_url = self.start_image or self.image
        if image_url:
            result['start_image'] = image_url

        return result


class KlingV26Model(ModelDefinition):
    """Kling v2.6 model definition."""

    input_class = KlingV26Input


KlingV26 = KlingV26Model(
    id='kling-v2.6',
    name='Kling v2.6',
    category=ModelCategory.VIDEO,
    capabilities=[ModelCapability.TEXT_TO_VIDEO, ModelCapability.IMAGE_TO_VIDEO],
    description='High-quality video generation model by Kuaishou with audio generation support.',
    author='Kuaishou',
    avg_generation_time_seconds=120.0,
    provider_configs={
        Provider.REPLICATE: ProviderConfig(
            provider=Provider.REPLICATE,
            model_id='kwaivgi/kling-v2.6',
        ),
    },
)

model_registry.register(KlingV26)
