"""Nano Banana Pro image generation model by Google.

Available on:
- Replicate: google/nano-banana-pro
"""

from enum import Enum
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


class NanoBananaResolution(str, Enum):
    """Resolution options for Nano Banana."""

    RES_1K = '1K'
    RES_2K = '2K'
    RES_4K = '4K'


class NanoBananaSafetyLevel(str, Enum):
    """Safety filter levels."""

    BLOCK_LOW_AND_ABOVE = 'block_low_and_above'
    BLOCK_MEDIUM_AND_ABOVE = 'block_medium_and_above'
    BLOCK_ONLY_HIGH = 'block_only_high'


# Mapping from our AspectRatio enum to Nano Banana's string format
_ASPECT_RATIO_MAP = {
    AspectRatio.SQUARE: '1:1',
    AspectRatio.PORTRAIT_2_3: '2:3',
    AspectRatio.LANDSCAPE_3_2: '3:2',
    AspectRatio.PORTRAIT_3_4: '3:4',
    AspectRatio.LANDSCAPE_4_3: '4:3',
    AspectRatio.PORTRAIT_9_16: '9:16',
    AspectRatio.LANDSCAPE_16_9: '16:9',
    AspectRatio.LANDSCAPE_21_9: '21:9',
    # Map unsupported ratios to closest available
    AspectRatio.PORTRAIT_9_21: '9:16',
}


class NanoBananaInput(ModelInput):
    """Input schema for Nano Banana model."""

    prompt: str = Field(..., description='A text description of the image you want to generate')
    image_input: list[str] = Field(
        default_factory=list,
        description='Input images to transform or use as reference (supports up to 14 images)',
    )
    aspect_ratio: AspectRatio = Field(
        AspectRatio.SQUARE,
        description='Aspect ratio of the generated image',
    )
    resolution: NanoBananaResolution = Field(
        NanoBananaResolution.RES_2K,
        description='Resolution of the generated image',
    )
    output_format: Literal['jpg', 'png'] = Field('jpg', description='Format of the output image')
    safety_filter_level: NanoBananaSafetyLevel = Field(
        NanoBananaSafetyLevel.BLOCK_ONLY_HIGH,
        description='Safety filter strictness level',
    )
    negative_prompt: str = Field('', description='Things you do not want in the image')

    def to_replicate(self) -> dict[str, Any]:
        """Convert to Replicate API format."""
        result: dict[str, Any] = {
            'prompt': self.prompt,
            'resolution': self.resolution.value,
            'output_format': self.output_format,
            'safety_filter_level': self.safety_filter_level.value,
        }

        # Handle aspect ratio - use match_input_image if images provided, otherwise map
        if self.image_input:
            result['image_input'] = self.image_input
            result['aspect_ratio'] = 'match_input_image'
        else:
            result['aspect_ratio'] = _ASPECT_RATIO_MAP.get(self.aspect_ratio, '1:1')

        return result


class NanoBananaModel(ModelDefinition):
    """Nano Banana model definition."""

    input_class = NanoBananaInput


NanoBanana = NanoBananaModel(
    id='nano-banana',
    name='Nano Banana Pro',
    category=ModelCategory.IMAGE,
    capabilities=[ModelCapability.TEXT_TO_IMAGE, ModelCapability.IMAGE_TO_IMAGE],
    description='Fast, high-quality image generation by Google with multi-image input support.',
    author='Google',
    avg_generation_time_seconds=10.0,
    provider_configs={
        Provider.REPLICATE: ProviderConfig(
            provider=Provider.REPLICATE,
            model_id='google/nano-banana-pro',
        ),
    },
)

model_registry.register(NanoBanana)
