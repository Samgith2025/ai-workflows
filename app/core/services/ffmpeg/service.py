"""FFmpeg service for video processing.

Uses the local FFmpeg binary for video processing.
"""

import asyncio
import logging

from app.core.services.ffmpeg.schemas import (
    CombineAudioInput,
    CombineAudioOutput,
    SlowDownInput,
    SlowDownOutput,
    TextOverlayInput,
    TextOverlayOutput,
    TextPosition,
)

logger = logging.getLogger(__name__)


# FFmpeg filter expressions for text position
# Using percentage-based positioning for better responsiveness
POSITION_MAP = {
    TextPosition.TOP_LEFT: ('w*0.05', 'h*0.08'),
    TextPosition.TOP_CENTER: ('(w-text_w)/2', 'h*0.08'),
    TextPosition.TOP_RIGHT: ('w*0.95-text_w', 'h*0.08'),
    TextPosition.CENTER: ('(w-text_w)/2', '(h-text_h)/2'),
    TextPosition.BOTTOM_LEFT: ('w*0.05', 'h*0.85-text_h'),
    TextPosition.BOTTOM_CENTER: ('(w-text_w)/2', 'h*0.85-text_h'),
    TextPosition.BOTTOM_RIGHT: ('w*0.95-text_w', 'h*0.85-text_h'),
}


def _wrap_text(text: str, max_chars_per_line: int = 30) -> str:
    """Wrap text to multiple lines for TikTok-style display."""
    words = text.split()
    lines: list[str] = []
    current_line: list[str] = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= max_chars_per_line:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)

    if current_line:
        lines.append(' '.join(current_line))

    return '\n'.join(lines)


def _escape_drawtext_value(text: str) -> str:
    r"""Escape text for FFmpeg drawtext filter.

    When using multiple chained drawtext filters, we must escape commas
    to prevent FFmpeg from interpreting them as filter separators.

    FFmpeg drawtext escaping (in order):
    1. Backslash: \\ -> \\\\
    2. Single quote: ' -> '\\''  (close-escape-reopen pattern)
    3. Colon: : -> \\:
    4. Semicolon: ; -> \\;
    5. Comma: , -> \\,  (critical for filter chains!)
    6. Brackets: [ ] -> \\[ \\]
    7. Percent: % -> %%  (not backslash-escaped in drawtext)

    Args:
        text: Raw text to escape

    Returns:
        Properly escaped text for drawtext filter
    """
    # Order matters: escape backslashes first
    text = text.replace('\\', '\\\\')
    # Single quotes: use the close-escape-reopen pattern for shell safety
    text = text.replace("'", "'\\''")
    text = text.replace(':', '\\:')
    text = text.replace(';', '\\;')
    # CRITICAL: escape commas to prevent breaking filter chains
    text = text.replace(',', '\\,')
    text = text.replace('[', '\\[')
    text = text.replace(']', '\\]')
    # Percent is special in drawtext - doubled, not backslash-escaped
    text = text.replace('%', '%%')
    return text


def _build_drawtext_filter(
    text: str,
    font_spec: str,
    font_size: int,
    font_color: str,
    x_expr: str,
    y_expr: str,
    border_width: int = 0,
    border_color: str = 'black',
    box: bool = False,
    box_color: str | None = None,
    box_padding: int = 0,
    enable_expr: str | None = None,
) -> str:
    """Build a single drawtext filter string for one line of text.

    Args:
        text: Already escaped text (single line, no newlines)
        font_spec: Font specification (font='name' or fontfile='path')
        font_size: Font size in pixels
        font_color: Font color
        x_expr: X position expression
        y_expr: Y position expression
        border_width: Border width (0 to disable)
        border_color: Border color
        box: Whether to draw background box
        box_color: Background box color with opacity
        box_padding: Padding around text for box
        enable_expr: Optional enable expression for timing

    Returns:
        Complete drawtext filter string
    """
    # Build parts list - order matters for FFmpeg
    # Quote color values to avoid issues when chaining multiple drawtext filters
    parts = [
        f"text='{text}'",
        font_spec,
        f'fontsize={font_size}',
        f"fontcolor='{font_color}'",
        f'x={x_expr}',
        f'y={y_expr}',
    ]

    if border_width > 0:
        parts.append(f'borderw={border_width}')
        parts.append(f"bordercolor='{border_color}'")

    if box and box_color:
        parts.append('box=1')
        parts.append(f"boxcolor='{box_color}'")
        parts.append(f'boxborderw={box_padding}')

    if enable_expr:
        parts.append(f"enable='{enable_expr}'")

    # Join with colons
    return 'drawtext=' + ':'.join(parts)


def _build_multiline_drawtext_filters(
    lines: list[str],
    font_spec: str,
    font_size: int,
    font_color: str,
    position: TextPosition,
    line_spacing: int,
    border_width: int = 0,
    border_color: str = 'black',
    box: bool = False,
    box_color: str | None = None,
    box_padding: int = 0,
    enable_expr: str | None = None,
) -> list[str]:
    """Build drawtext filters for multiple lines of text.

    Each line gets its own drawtext filter with calculated Y position.
    This avoids FFmpeg newline handling issues.

    Args:
        lines: List of already-escaped text lines
        font_spec: Font specification
        font_size: Font size in pixels
        font_color: Font color
        position: Text position enum
        line_spacing: Spacing between lines in pixels
        border_width: Border width (0 to disable)
        border_color: Border color
        box: Whether to draw background box
        box_color: Background box color with opacity
        box_padding: Padding around text for box
        enable_expr: Optional enable expression for timing

    Returns:
        List of drawtext filter strings
    """
    num_lines = len(lines)
    if num_lines == 0:
        return []

    # Calculate total text block height
    # Height = (num_lines * font_size) + ((num_lines - 1) * line_spacing)
    line_height = font_size + line_spacing

    # Get base X position from the position map
    x_expr, _ = POSITION_MAP.get(position, POSITION_MAP[TextPosition.CENTER])

    # Calculate starting Y based on position type
    # For vertical positioning, we calculate based on the text block height
    if position in (TextPosition.TOP_LEFT, TextPosition.TOP_CENTER, TextPosition.TOP_RIGHT):
        # Start from top (8% from top edge)
        start_y_expr = 'h*0.08'
    elif position in (TextPosition.BOTTOM_LEFT, TextPosition.BOTTOM_CENTER, TextPosition.BOTTOM_RIGHT):
        # Position so last line is at 85% from top
        # start_y = h*0.85 - (num_lines * font_size) - ((num_lines - 1) * line_spacing)
        total_height = (num_lines * font_size) + ((num_lines - 1) * line_spacing)
        start_y_expr = f'h*0.85-{total_height}'
    else:
        # CENTER - center the text block vertically
        # start_y = (h - total_height) / 2
        total_height = (num_lines * font_size) + ((num_lines - 1) * line_spacing)
        start_y_expr = f'(h-{total_height})/2'

    filters = []
    for i, line in enumerate(lines):
        # Calculate Y position for this line
        # y = start_y + (i * line_height)
        if i == 0:
            y_expr = start_y_expr
        else:
            y_offset = i * line_height
            y_expr = f'{start_y_expr}+{y_offset}'

        filter_str = _build_drawtext_filter(
            text=line,
            font_spec=font_spec,
            font_size=font_size,
            font_color=font_color,
            x_expr=x_expr,
            y_expr=y_expr,
            border_width=border_width,
            border_color=border_color,
            box=box,
            box_color=box_color,
            box_padding=box_padding,
            enable_expr=enable_expr,
        )
        filters.append(filter_str)

    return filters


class FFmpegService:
    """FFmpeg service using local binary."""

    async def _run_ffmpeg(self, args: list[str]) -> tuple[int, str, str]:
        """Run FFmpeg with the given arguments.

        Args:
            args: FFmpeg arguments (without 'ffmpeg' command)

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        logger.debug(f'Running FFmpeg: ffmpeg {" ".join(args)}')

        process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return process.returncode or 0, stdout.decode(), stderr.decode()

    async def get_video_dimensions(self, video_path: str) -> tuple[int, int]:
        """Get video dimensions using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Tuple of (width, height)
        """
        process = await asyncio.create_subprocess_exec(
            'ffprobe',
            '-v',
            'error',
            '-select_streams',
            'v:0',
            '-show_entries',
            'stream=width,height',
            '-of',
            'csv=s=x:p=0',
            video_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f'ffprobe failed: {stderr.decode()}')
            raise RuntimeError(f'ffprobe failed: {stderr.decode()}')

        dimensions = stdout.decode().strip()
        width, height = map(int, dimensions.split('x'))
        return width, height

    def build_slow_down_command(self, input: SlowDownInput) -> list[str]:
        """Build FFmpeg command for slow down operation.

        Args:
            input: SlowDownInput with speed settings

        Returns:
            FFmpeg command arguments
        """
        pts_factor = 1.0 / input.speed_factor

        if input.preserve_audio and 0.5 <= input.speed_factor <= 2.0:
            # Adjust both video and audio
            # atempo only works in range 0.5-2.0
            filter_complex = f'[0:v]setpts={pts_factor}*PTS[v];[0:a]atempo={input.speed_factor}[a]'
            return [
                '-i',
                input.input_path,
                '-filter_complex',
                filter_complex,
                '-map',
                '[v]',
                '-map',
                '[a]',
                '-c:v',
                'libx264',
                '-preset',
                'fast',
                '-c:a',
                'aac',
                '-y',
                input.output_path,
            ]
        # Video only, remove audio
        return [
            '-i',
            input.input_path,
            '-vf',
            f'setpts={pts_factor}*PTS',
            '-an',
            '-c:v',
            'libx264',
            '-preset',
            'fast',
            '-y',
            input.output_path,
        ]

    async def slow_down(self, input: SlowDownInput) -> SlowDownOutput:
        """Slow down or speed up a video.

        Args:
            input: SlowDownInput with paths and speed settings

        Returns:
            SlowDownOutput with result
        """
        command = self.build_slow_down_command(input)

        returncode, _stdout, stderr = await self._run_ffmpeg(command)

        if returncode != 0:
            logger.error(f'FFmpeg slow_down failed: {stderr}')
            raise RuntimeError(f'FFmpeg failed with code {returncode}: {stderr}')

        return SlowDownOutput(
            success=True,
            output_path=input.output_path,
            command=['ffmpeg', *command],
        )

    def build_text_overlay_command(self, input: TextOverlayInput) -> list[str]:
        """Build FFmpeg command for text overlay operation.

        Wraps text into multiple lines and creates a separate drawtext filter
        for each line. This avoids FFmpeg newline handling issues and gives
        precise control over line positioning.

        Args:
            input: TextOverlayInput with text and styling

        Returns:
            FFmpeg command arguments
        """
        # Wrap text into lines
        wrapped_text = _wrap_text(input.text, input.max_chars_per_line)
        lines = wrapped_text.split('\n')

        # Escape each line separately
        escaped_lines = [_escape_drawtext_value(line) for line in lines]

        # Determine font specification
        font_spec = f"fontfile='{input.font_path}'" if input.font_path else f"font='{input.font.value}'"

        # Build enable expression for timing if needed
        enable_expr = None
        if input.start_time > 0 or input.end_time is not None:
            if input.end_time is not None:
                enable_expr = f'between(t,{input.start_time},{input.end_time})'
            else:
                enable_expr = f'gte(t,{input.start_time})'

        # Build separate drawtext filter for each line
        filters = _build_multiline_drawtext_filters(
            lines=escaped_lines,
            font_spec=font_spec,
            font_size=input.font_size,
            font_color=input.font_color,
            position=input.position,
            line_spacing=input.line_spacing,
            border_width=input.border_width,
            border_color=input.border_color,
            box=input.background_color is not None,
            box_color=input.background_color,
            box_padding=input.padding,
            enable_expr=enable_expr,
        )

        # Chain filters with commas
        filter_chain = ','.join(filters)

        return [
            '-i',
            input.input_path,
            '-vf',
            filter_chain,
            '-c:v',
            'libx264',
            '-preset',
            'fast',
            '-crf',
            '23',
            '-c:a',
            'copy',
            '-y',
            input.output_path,
        ]

    async def add_text_overlay(self, input: TextOverlayInput) -> TextOverlayOutput:
        """Add text overlay to a video.

        If auto_scale=True, calculates font size based on video dimensions:
        - font_size = video_height / font_scale_factor
        - Default factor of 18 gives good results for TikTok-style videos

        Args:
            input: TextOverlayInput with paths, text, and styling

        Returns:
            TextOverlayOutput with result
        """
        # Always auto-scale font size based on video dimensions
        width, height = await self.get_video_dimensions(input.input_path)
        calculated_font_size = int(height / input.font_scale_factor)
        # Clamp to reasonable range
        calculated_font_size = max(24, min(calculated_font_size, 200))

        logger.info(f'Auto-scale: {width}x{height} -> font_size={calculated_font_size}')

        # Create new input with calculated font size
        effective_input = input.model_copy(update={'font_size': calculated_font_size})

        command = self.build_text_overlay_command(effective_input)

        logger.debug(f'Text overlay filter: {command}')

        returncode, _stdout, stderr = await self._run_ffmpeg(command)

        if returncode != 0:
            logger.error(f'FFmpeg text overlay failed: {stderr}')
            raise RuntimeError(f'FFmpeg failed with code {returncode}: {stderr}')

        return TextOverlayOutput(
            success=True,
            output_path=input.output_path,
            command=['ffmpeg', *command],
        )

    def build_combine_audio_command(self, input: CombineAudioInput) -> list[str]:
        """Build FFmpeg command for combine audio operation.

        Args:
            input: CombineAudioInput with paths

        Returns:
            FFmpeg command arguments
        """
        return [
            '-i',
            input.video_path,
            '-i',
            input.audio_path,
            '-c:v',
            'copy',
            '-c:a',
            'aac',
            '-map',
            '0:v:0',
            '-map',
            '1:a:0',
            '-shortest',
            '-y',
            input.output_path,
        ]

    async def combine_audio(self, input: CombineAudioInput) -> CombineAudioOutput:
        """Combine video with audio track.

        Args:
            input: CombineAudioInput with video, audio paths

        Returns:
            CombineAudioOutput with result
        """
        command = self.build_combine_audio_command(input)

        returncode, _stdout, stderr = await self._run_ffmpeg(command)

        if returncode != 0:
            logger.error(f'FFmpeg combine audio failed: {stderr}')
            raise RuntimeError(f'FFmpeg failed with code {returncode}: {stderr}')

        return CombineAudioOutput(
            success=True,
            output_path=input.output_path,
            command=['ffmpeg', *command],
        )


def get_ffmpeg_service() -> FFmpegService:
    """Get an FFmpeg service instance.

    Returns:
        FFmpegService instance
    """
    return FFmpegService()
