"""HiDream image generation models.

Available on:
- Replicate: prunaai/hidream-l1-fast
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
from app.core.ai_models.image.common import OutputFormat
from app.core.ai_models.registry import model_registry


class HiDreamSpeedMode(str, Enum):
    """Speed optimization levels."""

    UNSQUEEZED = 'Unsqueezed 🍋 (highest quality)'
    LIGHTLY_JUICED = 'Lightly Juiced 🍊 (more consistent)'
    JUICED = 'Juiced 🔥 (more speed)'
    EXTRA_JUICED = 'Extra Juiced 🚀 (even more speed)'


# Internal mapping from AspectRatio to Replicate's resolution strings
_ASPECT_TO_RESOLUTION = {
    AspectRatio.SQUARE: '1024 × 1024 (Square)',
    AspectRatio.PORTRAIT_9_16: '768 × 1360 (Portrait)',
    AspectRatio.PORTRAIT_3_4: '880 × 1168 (Portrait)',
    AspectRatio.PORTRAIT_2_3: '832 × 1248 (Portrait)',
    AspectRatio.LANDSCAPE_16_9: '1360 × 768 (Landscape)',
    AspectRatio.LANDSCAPE_4_3: '1168 × 880 (Landscape)',
    AspectRatio.LANDSCAPE_3_2: '1248 × 832 (Landscape)',
    # Ultrawide - map to closest available
    AspectRatio.LANDSCAPE_21_9: '1360 × 768 (Landscape)',
    AspectRatio.PORTRAIT_9_21: '768 × 1360 (Portrait)',
}

# Mapping for FAL (width, height)
_ASPECT_TO_DIMENSIONS = {
    AspectRatio.SQUARE: (1024, 1024),
    AspectRatio.PORTRAIT_9_16: (768, 1360),
    AspectRatio.PORTRAIT_3_4: (880, 1168),
    AspectRatio.PORTRAIT_2_3: (832, 1248),
    AspectRatio.LANDSCAPE_16_9: (1360, 768),
    AspectRatio.LANDSCAPE_4_3: (1168, 880),
    AspectRatio.LANDSCAPE_3_2: (1248, 832),
    AspectRatio.LANDSCAPE_21_9: (1360, 768),
    AspectRatio.PORTRAIT_9_21: (768, 1360),
}


class HiDreamFastInput(ModelInput):
    """Input schema for HiDream Fast model."""

    prompt: str = Field(..., description='Text prompt for image generation')
    model_type: Literal['fast'] = Field('fast', description='Model type')
    speed_mode: HiDreamSpeedMode = Field(HiDreamSpeedMode.EXTRA_JUICED, description='Speed optimization')
    aspect_ratio: AspectRatio = Field(AspectRatio.SQUARE, description='Output aspect ratio')
    seed: int = Field(-1, description='Random seed (-1 for random)')
    output_format: OutputFormat = Field(OutputFormat.WEBP, description='Output format')
    output_quality: int = Field(100, ge=1, le=100, description='Output quality (1-100)')
    negative_prompt: str = Field('', description='Negative prompt')

    def to_replicate(self) -> dict[str, Any]:
        """Convert to Replicate format."""
        resolution = _ASPECT_TO_RESOLUTION.get(self.aspect_ratio, '1024 × 1024 (Square)')
        return {
            'prompt': self.prompt,
            'model_type': self.model_type,
            'speed_mode': self.speed_mode.value,
            'resolution': resolution,
            'seed': self.seed,
            'output_format': self.output_format.value,
            'output_quality': self.output_quality,
            'negative_prompt': self.negative_prompt,
        }

    def to_fal(self) -> dict[str, Any]:
        """Convert to FAL format."""
        width, height = _ASPECT_TO_DIMENSIONS.get(self.aspect_ratio, (1024, 1024))

        return {
            'prompt': self.prompt,
            'negative_prompt': self.negative_prompt,
            'width': width,
            'height': height,
            'seed': self.seed if self.seed >= 0 else None,
            'output_format': self.output_format.value,
        }


class HiDreamFastModel(ModelDefinition):
    """HiDream L1 Fast model definition."""

    input_class = HiDreamFastInput


HiDreamFast = HiDreamFastModel(
    id='hidream-fast',
    name='HiDream L1 Fast',
    category=ModelCategory.IMAGE,
    capabilities=[ModelCapability.TEXT_TO_IMAGE],
    description='Fast, high-quality image generation by Pruna AI.',
    author='Pruna AI',
    avg_generation_time_seconds=5.0,
    provider_configs={
        Provider.REPLICATE: ProviderConfig(
            provider=Provider.REPLICATE,
            model_id='prunaai/hidream-l1-fast',
        ),
    },
)

model_registry.register(HiDreamFast)
