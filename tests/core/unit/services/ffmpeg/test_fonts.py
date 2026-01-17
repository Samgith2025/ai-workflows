"""Tests for font handling."""

import tempfile
from pathlib import Path

from app.core.services.ffmpeg import FFmpegService, TextFont, TextOverlayInput

# Use tempfile module to satisfy S108 security lint
_TEMP_DIR = Path(tempfile.gettempdir())
_INPUT_PATH = str(_TEMP_DIR / 'input.mp4')
_OUTPUT_PATH = str(_TEMP_DIR / 'output.mp4')


class TestTextFonts:
    """Tests for font handling."""

    def test_all_fonts_valid(self):
        """All defined fonts should be usable."""
        service = FFmpegService()

        for font in TextFont:
            input = TextOverlayInput(
                input_path=_INPUT_PATH,
                output_path=_OUTPUT_PATH,
                text='Test',
                font=font,
            )
            command = service.build_text_overlay_command(input)

            vf_idx = command.index('-vf')
            filter_chain = command[vf_idx + 1]

            assert f"font='{font.value}'" in filter_chain
