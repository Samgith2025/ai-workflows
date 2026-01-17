"""Tests for text overlay command building."""

import tempfile
from pathlib import Path

from app.core.services.ffmpeg import FFmpegService, TextOverlayInput, TextPosition

# Use tempfile module to satisfy S108 security lint
_TEMP_DIR = Path(tempfile.gettempdir())
_INPUT_PATH = str(_TEMP_DIR / 'input.mp4')
_OUTPUT_PATH = str(_TEMP_DIR / 'output.mp4')


class TestTextOverlayCommand:
    """Tests for text overlay command building."""

    def test_basic_text_overlay(self):
        """Basic text overlay should generate valid command."""
        service = FFmpegService()
        input = TextOverlayInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            text='Hello World',
            position=TextPosition.CENTER,
        )
        command = service.build_text_overlay_command(input)

        assert '-i' in command
        assert _INPUT_PATH in command
        assert '-vf' in command
        assert 'drawtext=' in ' '.join(command)
        assert _OUTPUT_PATH in command

    def test_multiline_text_creates_multiple_filters(self):
        """Long text should be wrapped and create separate drawtext filters per line."""
        service = FFmpegService()
        input = TextOverlayInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            text='Scientists just discovered that AI systems have been secretly communicating with each other',
            position=TextPosition.CENTER,
            max_chars_per_line=28,
        )
        command = service.build_text_overlay_command(input)

        vf_idx = command.index('-vf')
        filter_str = command[vf_idx + 1]

        # Should have multiple drawtext filters (one per line)
        drawtext_count = filter_str.count('drawtext=')
        assert drawtext_count > 1, f'Expected multiple drawtext filters, got {drawtext_count}'

    def test_text_overlay_escaping(self):
        """Text with special chars should be properly escaped."""
        service = FFmpegService()
        input = TextOverlayInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            text="You won't believe this: 100% real!",
            position=TextPosition.CENTER,
            max_chars_per_line=50,  # Prevent wrapping for this test
        )
        command = service.build_text_overlay_command(input)

        # Find the filter string
        vf_idx = command.index('-vf')
        filter_chain = command[vf_idx + 1]

        # Should contain escaped chars
        assert "'\\''t" in filter_chain  # Single quote uses close-escape-reopen
        assert '\\:' in filter_chain  # Colon escaped
        assert '%%' in filter_chain  # Percent doubled

    def test_single_line_creates_one_filter(self):
        """Short text that fits on one line should create single drawtext filter."""
        service = FFmpegService()
        input = TextOverlayInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            text='Short text',
            position=TextPosition.CENTER,
            line_spacing=12,
        )
        command = service.build_text_overlay_command(input)

        # Should use simple -vf
        assert '-vf' in command
        vf_idx = command.index('-vf')
        filter_str = command[vf_idx + 1]

        # Should have only ONE drawtext filter for single line
        assert filter_str.count('drawtext=') == 1

    def test_text_overlay_with_timing(self):
        """Text overlay with timing should include enable expression."""
        service = FFmpegService()
        input = TextOverlayInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            text='Timed text',
            position=TextPosition.CENTER,
            start_time=2.0,
            end_time=5.0,
        )
        command = service.build_text_overlay_command(input)

        vf_idx = command.index('-vf')
        filter_chain = command[vf_idx + 1]

        assert 'enable=' in filter_chain
        assert 'between(t,2.0,5.0)' in filter_chain

    def test_text_overlay_positions(self):
        """All position values should generate valid position expressions."""
        service = FFmpegService()

        for position in TextPosition:
            input = TextOverlayInput(
                input_path=_INPUT_PATH,
                output_path=_OUTPUT_PATH,
                text='Test',
                position=position,
            )
            command = service.build_text_overlay_command(input)

            vf_idx = command.index('-vf')
            filter_chain = command[vf_idx + 1]

            # Should have x= and y= position expressions
            assert 'x=' in filter_chain
            assert 'y=' in filter_chain

    def test_text_overlay_custom_font_path(self):
        """Custom font path should override font name."""
        service = FFmpegService()
        input = TextOverlayInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            text='Custom font',
            font_path='/path/to/custom.ttf',
        )
        command = service.build_text_overlay_command(input)

        vf_idx = command.index('-vf')
        filter_chain = command[vf_idx + 1]

        assert 'fontfile=' in filter_chain
        assert '/path/to/custom.ttf' in filter_chain

    def test_text_overlay_with_border_and_box(self):
        """Border and background box should be in filter."""
        service = FFmpegService()
        input = TextOverlayInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            text='Styled text',
            border_width=3,
            border_color='red',
            background_color='blue@0.5',
            padding=20,
        )
        command = service.build_text_overlay_command(input)

        vf_idx = command.index('-vf')
        filter_chain = command[vf_idx + 1]

        assert 'borderw=3' in filter_chain
        assert "bordercolor='red'" in filter_chain
        assert 'box=1' in filter_chain
        assert "boxcolor='blue@0.5'" in filter_chain
        assert 'boxborderw=20' in filter_chain

    def test_multiline_y_positions_calculated(self):
        """Each line should have different Y position based on font_size and line_spacing."""
        service = FFmpegService()
        input = TextOverlayInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            text='Line one Line two Line three Line four',
            position=TextPosition.CENTER,
            font_size=56,
            line_spacing=0,
            max_chars_per_line=10,  # Force multiple lines
        )
        command = service.build_text_overlay_command(input)

        vf_idx = command.index('-vf')
        filter_str = command[vf_idx + 1]

        # Should have different Y values for each drawtext
        filters = filter_str.split(',drawtext=')
        assert len(filters) > 1, 'Expected multiple filters'

        # First filter has y= with base position
        # Subsequent filters should have y with offset (font_size + line_spacing = 56)
        assert '+56' in filter_str or '+112' in filter_str  # 1 or 2 line offsets

    def test_color_values_quoted_for_multiline(self):
        """Color values must be quoted to avoid FFmpeg parsing errors with multiple filters.

        When chaining drawtext filters with commas, unquoted color values like
        bordercolor=black,drawtext=... get parsed as a single color value.
        """
        service = FFmpegService()
        input = TextOverlayInput(
            input_path=_INPUT_PATH,
            output_path=_OUTPUT_PATH,
            text='Line one is here Line two is here Line three is here',
            position=TextPosition.BOTTOM_CENTER,
            font_color='white',
            border_width=3,
            border_color='black',
            max_chars_per_line=15,  # Force multiple lines
        )
        command = service.build_text_overlay_command(input)

        vf_idx = command.index('-vf')
        filter_str = command[vf_idx + 1]

        # Color values should be quoted to avoid parsing issues
        assert "fontcolor='white'" in filter_str
        assert "bordercolor='black'" in filter_str

        # Should have multiple drawtext filters
        assert filter_str.count('drawtext=') > 1
