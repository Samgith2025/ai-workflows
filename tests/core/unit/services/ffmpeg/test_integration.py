"""Integration tests for FFmpeg service.

These tests actually run FFmpeg commands to verify they work.
Requires FFmpeg to be installed locally.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.core.services.ffmpeg import (
    SlowDownInput,
    TextFont,
    TextOverlayInput,
    TextPosition,
    get_ffmpeg_service,
)

# Skip all tests if FFmpeg is not installed
pytestmark = pytest.mark.skipif(
    shutil.which('ffmpeg') is None,
    reason='FFmpeg not installed',
)


@pytest.fixture
def test_video_path():
    """Create a simple test video using FFmpeg."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / 'test.mp4'

        # Create a 2-second test video with color bars
        subprocess.run(  # noqa: S603
            [  # noqa: S607
                'ffmpeg',
                '-f',
                'lavfi',
                '-i',
                'testsrc=duration=2:size=320x240:rate=30',
                '-f',
                'lavfi',
                '-i',
                'sine=frequency=1000:duration=2',
                '-c:v',
                'libx264',
                '-preset',
                'ultrafast',
                '-c:a',
                'aac',
                '-y',
                str(video_path),
            ],
            capture_output=True,
            check=False,
        )

        if video_path.exists():
            yield str(video_path)
        else:
            pytest.skip('Could not create test video')


class TestFFmpegIntegration:
    """Integration tests that run actual FFmpeg commands."""

    @pytest.mark.asyncio
    async def test_text_overlay_basic(self, test_video_path):
        """Basic text overlay should work."""
        service = get_ffmpeg_service()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.mp4'

            result = await service.add_text_overlay(
                TextOverlayInput(
                    input_path=test_video_path,
                    output_path=str(output_path),
                    text='Hello World',
                    position=TextPosition.CENTER,
                )
            )

            assert result.success
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_text_overlay_multiline(self, test_video_path):
        """Text overlay with multiple lines should work."""
        service = get_ffmpeg_service()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.mp4'

            result = await service.add_text_overlay(
                TextOverlayInput(
                    input_path=test_video_path,
                    output_path=str(output_path),
                    text='Scientists just discovered that AI systems have been secretly communicating',
                    position=TextPosition.CENTER,
                    line_spacing=12,
                    max_chars_per_line=28,
                )
            )

            assert result.success
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_text_overlay_with_special_chars(self, test_video_path):
        """Text with special characters should be properly escaped."""
        service = get_ffmpeg_service()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.mp4'

            # Use shorter text to avoid wrapping issues, and higher max_chars
            result = await service.add_text_overlay(
                TextOverlayInput(
                    input_path=test_video_path,
                    output_path=str(output_path),
                    text="It's 100% real!",  # Shorter text with special chars
                    position=TextPosition.CENTER,
                    font=TextFont.IMPACT,
                    font_size=24,
                    border_width=2,
                    background_color='black@0.5',
                    max_chars_per_line=50,  # Prevent wrapping
                )
            )

            assert result.success
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_text_overlay_tiktok_style(self, test_video_path):
        """Full TikTok-style overlay with all options should work."""
        service = get_ffmpeg_service()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.mp4'

            result = await service.add_text_overlay(
                TextOverlayInput(
                    input_path=test_video_path,
                    output_path=str(output_path),
                    text="You won't believe this...",
                    position=TextPosition.CENTER,
                    font=TextFont.IMPACT,
                    font_size=58,
                    font_color='white',
                    background_color='black@0.5',
                    padding=20,
                    border_width=3,
                    border_color='black',
                    line_spacing=12,
                )
            )

            assert result.success
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_text_overlay_long_multiline_with_border(self, test_video_path):
        """Long text with many lines and border should not cause FFmpeg parsing errors.

        This tests the fix for the issue where bordercolor=black followed by
        ,drawtext=... was being parsed as a single color value.
        """
        service = get_ffmpeg_service()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.mp4'

            # Long text that creates many lines - this caused "Cannot find color" errors
            long_text = (
                'im chat our professor just said "if i even THINK chatgpt wrote ur essay '
                'u get a ZERO". whole class goes silent. "if i see a single oxford comma '
                'or fake citation it\'s a zero". chat i am begging you to pls use a humaniser '
                'for the grammar and jenni for the fake citations do not risk ur whole degree '
                "for chatgpt it doesn't love u back like that"
            )

            result = await service.add_text_overlay(
                TextOverlayInput(
                    input_path=test_video_path,
                    output_path=str(output_path),
                    text=long_text,
                    position=TextPosition.BOTTOM_CENTER,
                    font=TextFont.ARIAL_BLACK,
                    font_size=24,
                    font_color='white',
                    border_width=3,
                    border_color='black',
                    line_spacing=8,
                    max_chars_per_line=28,
                )
            )

            assert result.success
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_slow_down_video(self, test_video_path):
        """Slow down video should work."""
        service = get_ffmpeg_service()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.mp4'

            result = await service.slow_down(
                SlowDownInput(
                    input_path=test_video_path,
                    output_path=str(output_path),
                    speed_factor=0.5,
                    preserve_audio=False,
                )
            )

            assert result.success
            assert output_path.exists()
            assert output_path.stat().st_size > 0
