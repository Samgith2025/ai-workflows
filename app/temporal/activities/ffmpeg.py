"""FFmpeg-based video processing activities.

These activities handle video manipulation tasks like:
- Speed adjustment (slow motion, speed up)
- Text overlay
- Audio/video combination
- Format conversion

Uses local FFmpeg via the FFmpeg service.
"""

import asyncio
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from pydantic import BaseModel, Field
from temporalio import activity

from app.core.services.ffmpeg import (
    CombineAudioInput,
    SlowDownInput,
    TextFont,
    TextOverlayInput,
    TextPosition,
    get_ffmpeg_service,
)
from app.core.services.storage.schemas import UploadRequest
from app.core.services.storage.service import get_storage


class SlowDownVideoInput(BaseModel):
    """Input for slow down video activity."""

    video_url: str = Field(..., description='URL of video to slow down')
    speed_factor: float = Field(0.5, description='Speed factor (0.5 = half speed, 2x slower)')
    preserve_audio: bool = Field(False, description='Slow audio too or remove it')
    output_folder: str = Field('ffmpeg/slowmo', description='Storage folder for output')


class SlowDownVideoOutput(BaseModel):
    """Output from slow down video activity."""

    output_url: str = Field(..., description='URL of slowed video')
    duration_seconds: float = Field(..., description='Processing time')


class TextOverlayActivityInput(BaseModel):
    """Input for text overlay activity.

    Long text is automatically wrapped and each line is rendered as a separate
    drawtext filter for reliable multi-line support. Lines are positioned from
    top to bottom based on font_size and line_spacing.

    Font size is auto-calculated based on video height:
    - font_size = video_height / font_scale_factor
    - Lower font_scale_factor = bigger text
    """

    video_url: str = Field(..., description='URL of video')
    text: str = Field(..., description='Text to overlay (can be long, will be wrapped)')
    position: TextPosition = Field(TextPosition.CENTER, description='Text position')

    # Font settings
    font: TextFont = Field(TextFont.IMPACT, description='Font family (Impact is best for TikTok style)')
    font_path: str | None = Field(None, description='Custom font file path (overrides font)')
    font_color: str = Field('white', description='Font color')

    # Auto-scaling factor (font_size = video_height / factor)
    font_scale_factor: float = Field(30.0, description='Font scale divisor (height/factor). Lower = bigger text.')

    # Background and effects
    background_color: str | None = Field('black@0.6', description='Background color with opacity')
    padding: int = Field(15, description='Padding around text')
    border_width: int = Field(2, description='Text border/outline width (0 to disable)')
    border_color: str = Field('black', description='Text border color')

    # Timing
    start_time: float = Field(0.0, description='When to start showing text')
    end_time: float | None = Field(None, description='When to stop showing text (None = until end)')
    line_spacing: int = Field(12, description='Spacing between wrapped lines')
    max_chars_per_line: int = Field(28, description='Max characters per line for wrapping')

    # Output
    output_folder: str = Field('ffmpeg/text', description='Storage folder for output')


class TextOverlayActivityOutput(BaseModel):
    """Output from text overlay activity."""

    output_url: str = Field(..., description='URL of video with text overlay')


async def _download_file(url: str, dest_path: str) -> None:
    """Download a file from URL to local path."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        with open(dest_path, 'wb') as f:
            f.write(response.content)


async def _upload_file(file_path: str, folder: str, content_type: str = 'video/mp4') -> str:
    """Upload a local file to storage and return the URL."""
    with open(file_path, 'rb') as f:
        data = f.read()

    # Determine extension from content type
    ext_map = {
        'video/mp4': 'mp4',
        'video/webm': 'webm',
        'video/quicktime': 'mov',
        'audio/mpeg': 'mp3',
        'audio/wav': 'wav',
    }
    extension = ext_map.get(content_type, 'mp4')

    # Generate key with date prefix for organization
    date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
    key = f'{folder}/{date_prefix}/{uuid.uuid4().hex[:12]}.{extension}'

    storage = get_storage()
    result = await storage.upload(
        UploadRequest(
            data=data,
            content_type=content_type,
            key=key,
        )
    )
    return result.url


@activity.defn
async def slow_down_video(input: SlowDownVideoInput) -> SlowDownVideoOutput:
    """Slow down a video by a given factor.

    Uses local FFmpeg for processing via the FFmpeg service.

    Args:
        input: SlowDownVideoInput with video URL and speed factor

    Example:
        # Make video 2x slower (half speed)
        result = await slow_down_video(SlowDownVideoInput(
            video_url='https://example.com/video.mp4',
            speed_factor=0.5,
        ))
    """
    activity.logger.info(f'Slowing down video by factor {input.speed_factor}')

    # Create temp directory for processing
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = str(tmpdir_path / 'input.mp4')
        output_path = str(tmpdir_path / 'output.mp4')

        # Download input video
        activity.logger.info('Downloading input video...')
        await _download_file(input.video_url, input_path)

        # Use FFmpeg service
        ffmpeg = get_ffmpeg_service()
        activity.logger.info('Running FFmpeg...')

        result = await ffmpeg.slow_down(
            SlowDownInput(
                input_path=input_path,
                output_path=output_path,
                speed_factor=input.speed_factor,
                preserve_audio=input.preserve_audio,
            )
        )

        activity.logger.debug(f'FFmpeg command: {" ".join(result.command)}')

        # Upload result
        activity.logger.info('Uploading result...')
        output_url = await _upload_file(output_path, input.output_folder)

    return SlowDownVideoOutput(
        output_url=output_url,
        duration_seconds=0.0,  # Could probe the output file for duration
    )


@activity.defn
async def add_text_overlay(input: TextOverlayActivityInput) -> TextOverlayActivityOutput:
    """Add TikTok-style text overlay to a video.

    Uses local FFmpeg for processing via the FFmpeg service.
    Long text is automatically wrapped and each line is rendered as a separate
    drawtext filter for reliable multi-line support.

    Args:
        input: TextOverlayActivityInput with video URL, text, and styling options

    Example:
        result = await add_text_overlay(TextOverlayActivityInput(
            video_url='https://example.com/video.mp4',
            text='Scientists just discovered that AI systems have been secretly communicating',
            position=TextPosition.CENTER,
            font_size=56,
        ))
    """
    activity.logger.info(f'Adding text overlay: "{input.text[:50]}..."')

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = str(tmpdir_path / 'input.mp4')
        output_path = str(tmpdir_path / 'output.mp4')

        # Download input video
        await _download_file(input.video_url, input_path)

        # Use FFmpeg service
        ffmpeg = get_ffmpeg_service()

        result = await ffmpeg.add_text_overlay(
            TextOverlayInput(
                input_path=input_path,
                output_path=output_path,
                text=input.text,
                position=input.position,
                font=input.font,
                font_path=input.font_path,
                font_color=input.font_color,
                font_scale_factor=input.font_scale_factor,
                background_color=input.background_color,
                padding=input.padding,
                border_width=input.border_width,
                border_color=input.border_color,
                start_time=input.start_time,
                end_time=input.end_time,
                line_spacing=input.line_spacing,
                max_chars_per_line=input.max_chars_per_line,
            )
        )

        activity.logger.debug(f'FFmpeg command: {" ".join(result.command)}')

        # Upload result
        output_url = await _upload_file(output_path, input.output_folder)

    return TextOverlayActivityOutput(output_url=output_url)


@activity.defn
async def combine_video_with_audio(video_url: str, audio_url: str) -> str:
    """Combine a video with an audio track.

    Replaces the video's audio with the provided audio file.

    Args:
        video_url: URL of the video file
        audio_url: URL of the audio file

    Returns:
        URL of the combined video
    """
    activity.logger.info('Combining video with audio')

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        video_path = str(tmpdir_path / 'video.mp4')
        audio_path = str(tmpdir_path / 'audio.mp3')
        output_path = str(tmpdir_path / 'output.mp4')

        # Download files
        await asyncio.gather(
            _download_file(video_url, video_path),
            _download_file(audio_url, audio_path),
        )

        # Use FFmpeg service
        ffmpeg = get_ffmpeg_service()

        result = await ffmpeg.combine_audio(
            CombineAudioInput(
                video_path=video_path,
                audio_path=audio_path,
                output_path=output_path,
            )
        )

        activity.logger.debug(f'FFmpeg command: {" ".join(result.command)}')

        # Upload result
        output_url = await _upload_file(output_path, 'ffmpeg/combined')

    return output_url
