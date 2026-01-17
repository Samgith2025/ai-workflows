"""Media rewriting activities.

Make generated media appear as fresh, original uploads to bypass duplicate
detection and AI content filters on social platforms.
"""

from pydantic import BaseModel, Field
from temporalio import activity

from app.core.tools.gptmarket.image_rewrite import (
    GptMarketImageRewrite,
    GptMarketImageRewriteInput,
    GptMarketImageRewriteOutput,
    ImageRewriteItem,
)
from app.core.tools.gptmarket.video_rewrite import (
    GptMarketVideoRewrite,
    GptMarketVideoRewriteInput,
    GptMarketVideoRewriteOutput,
)


class RewriteVideoInput(BaseModel):
    """Input for video rewriting activity."""

    video_url: str = Field(..., description='URL of the video to rewrite')
    playback_speed: float = Field(
        1.0,
        ge=0.5,
        le=2.0,
        description='Playback speed multiplier (0.5-2.0)',
    )
    device: str | None = Field(
        None,
        description='Device model for metadata (e.g., "iPhone 15 Pro")',
    )


class RewriteVideoOutput(BaseModel):
    """Output from video rewriting activity."""

    original_url: str = Field(..., description='Original video URL')
    rewritten_url: str = Field(..., description='Rewritten video URL (or original on failure)')


class RewriteImagesInput(BaseModel):
    """Input for batch image rewriting activity."""

    image_urls: list[str] = Field(..., min_length=1, description='URLs of images to rewrite')
    device: str | None = Field(
        None,
        description='Device model for metadata (e.g., "iPhone 15 Pro")',
    )


class RewriteImagesOutput(BaseModel):
    """Output from batch image rewriting activity."""

    original_urls: list[str] = Field(..., description='Original image URLs')
    rewritten_urls: list[str] = Field(..., description='Rewritten URLs (or originals on failure)')


@activity.defn
async def rewrite_video(input: RewriteVideoInput) -> RewriteVideoOutput:
    """Rewrite a video with modified metadata and visual augmentations.

    On failure, returns the original URL to ensure workflow continuity.

    Args:
        input: Video URL, optional playback speed, and optional device

    Returns:
        RewriteVideoOutput with rewritten URL
    """
    activity.logger.info(f'Rewriting video: {input.video_url} (device: {input.device})')

    tool_input = GptMarketVideoRewriteInput(
        video_url=input.video_url,
        playback_speed=input.playback_speed,
        device=input.device,
    )

    result = await GptMarketVideoRewrite.execute(tool_input)
    assert isinstance(result, GptMarketVideoRewriteOutput)

    activity.logger.info(f'Video rewrite complete: {input.video_url} -> {result.rewritten_url}')

    return RewriteVideoOutput(
        original_url=input.video_url,
        rewritten_url=result.rewritten_url,
    )


@activity.defn
async def rewrite_images(input: RewriteImagesInput) -> RewriteImagesOutput:
    """Rewrite images with modified metadata and visual augmentations.

    On failure, returns the original URLs to ensure workflow continuity.

    Args:
        input: List of image URLs to rewrite and optional device

    Returns:
        RewriteImagesOutput with rewritten URLs
    """
    activity.logger.info(f'Rewriting {len(input.image_urls)} images (device: {input.device})')

    tool_input = GptMarketImageRewriteInput(
        images=[ImageRewriteItem(image_url=url) for url in input.image_urls],
        device=input.device,
    )

    result = await GptMarketImageRewrite.execute(tool_input)
    assert isinstance(result, GptMarketImageRewriteOutput)

    rewritten_urls = [img.rewritten_url for img in result.images]

    activity.logger.info(f'Image rewrite complete: {len(rewritten_urls)} images processed')

    return RewriteImagesOutput(
        original_urls=input.image_urls,
        rewritten_urls=rewritten_urls,
    )
