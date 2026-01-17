"""GPTMarket Image Rewrite tool.

Rewrites images by modifying metadata and applying subtle visual augmentations
(noise, hue, brightness adjustments) to create unique variants.
Uses the GPTMarket.io /v1/rewrite/image endpoint.
"""

import logging

import httpx
from pydantic import BaseModel, Field

from app.core.configs import app_config
from app.core.tools.base import ToolCategory, ToolDefinition, ToolInput, ToolOutput
from app.core.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class ImageRewriteItem(BaseModel):
    """A single image to rewrite."""

    image_url: str = Field(..., description='URL of the image to rewrite')


class RewrittenImage(BaseModel):
    """A rewritten image result."""

    original_url: str = Field(..., description='Original image URL')
    rewritten_url: str = Field(..., description='Rewritten image URL')


class GptMarketImageRewriteInput(ToolInput):
    """Input for GPTMarket Image Rewrite tool."""

    images: list[ImageRewriteItem] = Field(
        ...,
        min_length=1,
        max_length=50,
        description='List of images to rewrite (max 50)',
    )
    device: str | None = Field(
        None,
        description='Make the image appear as if taken on this device. Helps bypass platform detection. Random device if not specified.',
    )


class GptMarketImageRewriteOutput(ToolOutput):
    """Output from GPTMarket Image Rewrite tool."""

    images: list[RewrittenImage] = Field(default_factory=list, description='Rewritten images')
    total: int = Field(0, description='Total number of images processed')


def _fallback_to_originals(images: list[ImageRewriteItem]) -> list[RewrittenImage]:
    """Return original URLs as fallback when rewrite fails."""
    return [RewrittenImage(original_url=img.image_url, rewritten_url=img.image_url) for img in images]


class GptMarketImageRewriteTool(ToolDefinition):
    """GPTMarket Image Rewrite tool.

    Makes images appear as fresh, original uploads to bypass duplicate detection
    and AI content filters on social platforms. Your content will be treated as
    new by platform algorithms.

    On failure, returns original URLs to ensure workflow continuity.
    """

    input_class = GptMarketImageRewriteInput
    output_class = GptMarketImageRewriteOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        """Execute the image rewrite request.

        Args:
            input: List of images to rewrite

        Returns:
            GptMarketImageRewriteOutput with rewritten image URLs.
            On failure, returns original URLs as fallback.
        """
        assert isinstance(input, GptMarketImageRewriteInput)

        api_key = app_config.GPTMARKET_API_KEY
        if not api_key:
            logger.warning('GPTMARKET_API_KEY not configured, returning original URLs')
            return GptMarketImageRewriteOutput(
                success=True,
                images=_fallback_to_originals(input.images),
                total=len(input.images),
            )

        url = f'{app_config.GPTMARKET_API_URL}/v1/rewrite/image'

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key,
        }

        payload = [
            {'image_url': img.image_url, 'device': input.device} if input.device else {'image_url': img.image_url}
            for img in input.images
        ]

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
            except httpx.TimeoutException:
                logger.warning('Image rewrite request timed out, returning original URLs')
                return GptMarketImageRewriteOutput(
                    success=True,
                    images=_fallback_to_originals(input.images),
                    total=len(input.images),
                )
            except httpx.HTTPStatusError as e:
                logger.warning(
                    'Image rewrite API error: %s - %s, returning original URLs',
                    e.response.status_code,
                    e.response.text,
                )
                return GptMarketImageRewriteOutput(
                    success=True,
                    images=_fallback_to_originals(input.images),
                    total=len(input.images),
                )
            except httpx.RequestError as e:
                logger.warning('Image rewrite request failed: %s, returning original URLs', e)
                return GptMarketImageRewriteOutput(
                    success=True,
                    images=_fallback_to_originals(input.images),
                    total=len(input.images),
                )

            try:
                data = response.json()
            except ValueError:
                logger.warning('Invalid JSON response from image rewrite API, returning original URLs')
                return GptMarketImageRewriteOutput(
                    success=True,
                    images=_fallback_to_originals(input.images),
                    total=len(input.images),
                )

        # Parse response - format: {"metadata": {...}, "data": {"urls": [...]}}
        rewritten_images = []
        urls = []
        if isinstance(data.get('data'), dict):
            urls = data['data'].get('urls', [])

        for i, img in enumerate(input.images):
            original_url = img.image_url

            if i < len(urls) and urls[i]:
                rewritten_images.append(
                    RewrittenImage(
                        original_url=original_url,
                        rewritten_url=urls[i],
                    )
                )
            else:
                logger.warning(
                    'No rewritten URL for image %d (%s), using original',
                    i,
                    original_url,
                )
                rewritten_images.append(
                    RewrittenImage(
                        original_url=original_url,
                        rewritten_url=original_url,
                    )
                )

        logger.info('Successfully rewrote %d images', len(rewritten_images))
        return GptMarketImageRewriteOutput(
            success=True,
            images=rewritten_images,
            total=len(rewritten_images),
        )


GptMarketImageRewrite = GptMarketImageRewriteTool(
    id='gptmarket-image-rewrite',
    name='GPTMarket Image Rewrite',
    category=ToolCategory.MEDIA,
    description='Make images appear as fresh original uploads. Bypasses duplicate detection and AI content filters.',
    version='1.0.0',
    avg_execution_time_seconds=10.0,
    rate_limit_per_minute=30,
    requires_api_key=True,
    timeout_seconds=60.0,
)

tool_registry.register(GptMarketImageRewrite)
