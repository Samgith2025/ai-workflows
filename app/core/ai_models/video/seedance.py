"""Seedance 1.5 Pro video generation model by ByteDance.

Available on:
- Replicate: bytedance/seedance-1.5-pro
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


class Seedance15ProInput(ModelInput):
    """Input schema for Seedance 1.5 Pro model."""

    prompt: str = Field(..., description='Text prompt for video generation')
    image: str | None = Field(None, description='Input image URL for image-to-video generation')
    last_frame_image: str | None = Field(
        None,
        description='Input image for last frame generation. Only works if image is also provided.',
    )
    duration: int = Field(5, ge=2, le=12, description='Video duration in seconds')
    aspect_ratio: AspectRatio = Field(
        AspectRatio.LANDSCAPE_16_9,
        description='Video aspect ratio. Ignored if an image is used.',
    )
    fps: Literal[24] = Field(24, description='Frame rate (frames per second)')
    camera_fixed: bool = Field(False, description='Whether to fix camera position')
    generate_audio: bool = Field(
        False,
        description='Generate audio synchronized with the video',
    )
    seed: int | None = Field(None, description='Random seed for reproducible generation')

    def to_replicate(self) -> dict[str, Any]:
        """Convert to Replicate API format."""
        result: dict[str, Any] = {
            'prompt': self.prompt,
            'duration': self.duration,
            'aspect_ratio': self.aspect_ratio.value,
            'fps': self.fps,
            'camera_fixed': self.camera_fixed,
            'generate_audio': self.generate_audio,
        }

        if self.image:
            result['image'] = self.image

        if self.last_frame_image:
            result['last_frame_image'] = self.last_frame_image

        if self.seed is not None:
            result['seed'] = self.seed

        return result


class Seedance15ProModel(ModelDefinition):
    """Seedance 1.5 Pro model definition."""

    input_class = Seedance15ProInput


Seedance15Pro = Seedance15ProModel(
    id='seedance-1.5-pro',
    name='Seedance 1.5 Pro',
    category=ModelCategory.VIDEO,
    capabilities=[ModelCapability.TEXT_TO_VIDEO, ModelCapability.IMAGE_TO_VIDEO],
    description='High-quality video generation model by ByteDance with image-to-video support.',
    author='ByteDance',
    avg_generation_time_seconds=60.0,
    provider_configs={
        Provider.REPLICATE: ProviderConfig(
            provider=Provider.REPLICATE,
            model_id='bytedance/seedance-1.5-pro',
        ),
    },
)

model_registry.register(Seedance15Pro)
