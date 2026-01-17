"""Tests for combine audio command building."""

import tempfile
from pathlib import Path

from app.core.services.ffmpeg import CombineAudioInput, FFmpegService

# Use tempfile module to satisfy S108 security lint
_TEMP_DIR = Path(tempfile.gettempdir())
_VIDEO_PATH = str(_TEMP_DIR / 'video.mp4')
_AUDIO_PATH = str(_TEMP_DIR / 'audio.mp3')
_OUTPUT_PATH = str(_TEMP_DIR / 'output.mp4')


class TestCombineAudioCommand:
    """Tests for combine audio command building."""

    def test_combine_audio_basic(self):
        """Basic audio combination should generate valid command."""
        service = FFmpegService()
        input = CombineAudioInput(
            video_path=_VIDEO_PATH,
            audio_path=_AUDIO_PATH,
            output_path=_OUTPUT_PATH,
        )
        command = service.build_combine_audio_command(input)

        # Should have two inputs
        assert command.count('-i') == 2
        assert _VIDEO_PATH in command
        assert _AUDIO_PATH in command

        # Should map video from first input, audio from second
        assert '-map' in command
        assert '0:v:0' in command
        assert '1:a:0' in command

        # Should use shortest duration
        assert '-shortest' in command
