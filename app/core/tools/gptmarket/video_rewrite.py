"""GPTMarket Video Rewrite tool.

Rewrites videos by modifying metadata and applying subtle visual augmentations
(noise, hue, brightness adjustments) to create unique variants.
Uses the GPTMarket.io /v1/rewrite/video endpoint.
"""

import logging

import httpx
from pydantic import Field

from app.core.configs import app_config
from app.core.tools.base import ToolCategory, ToolDefinition, ToolInput, ToolOutput
from app.core.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class GptMarketVideoRewriteInput(ToolInput):
    """Input for GPTMarket Video Rewrite tool."""

    video_url: str = Field(..., description='URL of the video to rewrite')
    playback_speed: float = Field(
        1.0,
        ge=0.5,
        le=2.0,
        description='Playback speed multiplier (0.5-2.0, default 1.0)',
    )
    device: str | None = Field(
        None,
        description='Make the video appear as if recorded on this device. Helps bypass platform detection. Random device if not specified.',
    )


class GptMarketVideoRewriteOutput(ToolOutput):
    """Output from GPTMarket Video Rewrite tool."""

    original_url: str = Field('', description='Original video URL')
    rewritten_url: str = Field('', description='Rewritten video URL')


class GptMarketVideoRewriteTool(ToolDefinition):
    """GPTMarket Video Rewrite tool.

    Makes videos appear as fresh, original uploads to bypass duplicate detection
    and AI content filters on social platforms. Your content will be treated as
    new by platform algorithms.

    On failure, returns original URL to ensure workflow continuity.
    """

    input_class = GptMarketVideoRewriteInput
    output_class = GptMarketVideoRewriteOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        """Execute the video rewrite request.

        Args:
            input: Video URL and optional parameters

        Returns:
            GptMarketVideoRewriteOutput with rewritten video URL.
            On failure, returns original URL as fallback.
        """
        assert isinstance(input, GptMarketVideoRewriteInput)

        api_key = app_config.GPTMARKET_API_KEY
        if not api_key:
            logger.warning('GPTMARKET_API_KEY not configured, returning original URL')
            return GptMarketVideoRewriteOutput(
                success=True,
                original_url=input.video_url,
                rewritten_url=input.video_url,
            )

        url = f'{app_config.GPTMARKET_API_URL}/v1/rewrite/video'

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key,
        }

        payload: dict = {
            'video_url': input.video_url,
            'playback_speed': input.playback_speed,
        }
        if input.device:
            payload['device'] = input.device

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
            except httpx.TimeoutException:
                logger.warning(
                    'Video rewrite request timed out for %s, returning original URL',
                    input.video_url,
                )
                return GptMarketVideoRewriteOutput(
                    success=True,
                    original_url=input.video_url,
                    rewritten_url=input.video_url,
                )
            except httpx.HTTPStatusError as e:
                logger.warning(
                    'Video rewrite API error: %s - %s for %s, returning original URL',
                    e.response.status_code,
                    e.response.text,
                    input.video_url,
                )
                return GptMarketVideoRewriteOutput(
                    success=True,
                    original_url=input.video_url,
                    rewritten_url=input.video_url,
                )
            except httpx.RequestError as e:
                logger.warning(
                    'Video rewrite request failed: %s for %s, returning original URL',
                    e,
                    input.video_url,
                )
                return GptMarketVideoRewriteOutput(
                    success=True,
                    original_url=input.video_url,
                    rewritten_url=input.video_url,
                )

            try:
                data = response.json()
            except ValueError:
                logger.warning(
                    'Invalid JSON response from video rewrite API for %s, returning original URL',
                    input.video_url,
                )
                return GptMarketVideoRewriteOutput(
                    success=True,
                    original_url=input.video_url,
                    rewritten_url=input.video_url,
                )

        # Parse response - format: {"metadata": {...}, "data": {"url": "..."}}
        rewritten_url = ''
        if isinstance(data.get('data'), dict):
            rewritten_url = data['data'].get('url', '')

        if not rewritten_url:
            logger.warning(
                'No rewritten URL in response for %s, returning original URL',
                input.video_url,
            )
            return GptMarketVideoRewriteOutput(
                success=True,
                original_url=input.video_url,
                rewritten_url=input.video_url,
            )

        logger.info('Successfully rewrote video %s', input.video_url)
        return GptMarketVideoRewriteOutput(
            success=True,
            original_url=input.video_url,
            rewritten_url=rewritten_url,
        )


GptMarketVideoRewrite = GptMarketVideoRewriteTool(
    id='gptmarket-video-rewrite',
    name='GPTMarket Video Rewrite',
    category=ToolCategory.MEDIA,
    description='Make videos appear as fresh original uploads. Bypasses duplicate detection and AI content filters.',
    version='1.0.0',
    avg_execution_time_seconds=30.0,
    rate_limit_per_minute=10,
    requires_api_key=True,
    timeout_seconds=120.0,
)

tool_registry.register(GptMarketVideoRewrite)
