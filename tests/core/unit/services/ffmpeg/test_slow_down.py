"""Tests for slow down command building."""

import tempfile
from pathlib import Path

from app.core.services.ffmpeg import FFmpegService, SlowDownInput

# Use tempfile module to satisfy S108 security lint
_TEMP_DIR = Path(tempfile.gettempdir())
_INPUT_PATH = str(_TEMP_DIR / 'input.mp4')
_OUTPUT_PATH = str(_TEMP_DIR / 'output.mp4')


class TestSlowDownCommand:
    """Tests for slow down command building."""

    def test_slow_down_half_speed_no_audio(self):
        """Half speed should double PTS and remove audio by default."""
        service = FFmpegService()
        input = SlowDownInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            speed_factor=0.5,
            preserve_audio=False,
        )
        command = service.build_slow_down_command(input)

        assert '-i' in command
        assert _INPUT_PATH in command
        assert '-vf' in command
        assert 'setpts=2.0*PTS' in command
        assert '-an' in command  # No audio
        assert _OUTPUT_PATH in command

    def test_slow_down_with_audio(self):
        """Slow down with audio should use filter_complex and atempo."""
        service = FFmpegService()
        input = SlowDownInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            speed_factor=0.5,
            preserve_audio=True,
        )
        command = service.build_slow_down_command(input)

        assert '-filter_complex' in command
        # atempo is inside the filter_complex string
        filter_idx = command.index('-filter_complex')
        filter_str = command[filter_idx + 1]
        assert 'atempo=0.5' in filter_str
        assert 'setpts=2.0*PTS' in filter_str
        assert '-map' in command

    def test_speed_up_double(self):
        """Double speed should halve PTS."""
        service = FFmpegService()
        input = SlowDownInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            speed_factor=2.0,
            preserve_audio=False,
        )
        command = service.build_slow_down_command(input)

        assert 'setpts=0.5*PTS' in command
