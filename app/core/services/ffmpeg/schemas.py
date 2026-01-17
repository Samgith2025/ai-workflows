"""FFmpeg service schemas.

All Pydantic models for FFmpeg video processing operations.
"""

from enum import Enum

from pydantic import BaseModel, Field


class TextPosition(str, Enum):
    """Position for text overlay on video."""

    TOP_LEFT = 'top_left'
    TOP_CENTER = 'top_center'
    TOP_RIGHT = 'top_right'
    CENTER = 'center'
    BOTTOM_LEFT = 'bottom_left'
    BOTTOM_CENTER = 'bottom_center'
    BOTTOM_RIGHT = 'bottom_right'


class TextFont(str, Enum):
    """Available fonts for text overlay.

    These are Linux-compatible fonts installed in the Docker image.
    For custom fonts, use font_path instead.
    """

    # Bold, impactful fonts (best for TikTok-style captions)
    IMPACT = 'DejaVu Sans Bold'  # Impact substitute
    ARIAL_BLACK = 'Liberation Sans Bold'
    HELVETICA_BOLD = 'FreeSans Bold'

    # Modern, clean fonts
    ARIAL = 'Liberation Sans'
    HELVETICA = 'FreeSans'
    ROBOTO = 'Roboto'

    # Serif fonts
    GEORGIA = 'Liberation Serif'
    TIMES = 'FreeSerif'

    # Monospace
    COURIER = 'Liberation Mono'


class FFmpegResult(BaseModel):
    """Result from an FFmpeg operation."""

    success: bool = Field(..., description='Whether the operation succeeded')
    output_path: str = Field(..., description='Path to the output file')
    returncode: int = Field(0, description='FFmpeg return code')
    stdout: str = Field('', description='FFmpeg stdout')
    stderr: str = Field('', description='FFmpeg stderr')
    command: list[str] = Field(default_factory=list, description='FFmpeg command that was run')


# Slow Down Video Schemas


class SlowDownInput(BaseModel):
    """Input for slow down video operation."""

    input_path: str = Field(..., description='Path to input video file')
    output_path: str = Field(..., description='Path for output video file')
    speed_factor: float = Field(0.5, gt=0, le=4.0, description='Speed factor (0.5 = half speed)')
    preserve_audio: bool = Field(False, description='Adjust audio speed too or remove it')


class SlowDownOutput(BaseModel):
    """Output from slow down video operation."""

    success: bool = Field(..., description='Whether the operation succeeded')
    output_path: str = Field(..., description='Path to the output file')
    command: list[str] = Field(default_factory=list, description='FFmpeg command used')


# Text Overlay Schemas


class TextOverlayInput(BaseModel):
    """Input for text overlay operation.

    For long text, the text is automatically wrapped and each line is rendered
    as a separate drawtext filter to avoid FFmpeg newline issues. Lines are
    positioned from top to bottom based on font_size and line_spacing.

    Font size is auto-calculated based on video height:
    - font_size = video_height / font_scale_factor
    - Lower font_scale_factor = bigger text
    """

    input_path: str = Field(..., description='Path to input video file')
    output_path: str = Field(..., description='Path for output video file')
    text: str = Field(..., description='Text to overlay on video')
    position: TextPosition = Field(TextPosition.CENTER, description='Text position')

    # Font settings
    font: TextFont = Field(TextFont.IMPACT, description='Font family')
    font_path: str | None = Field(None, description='Custom font file path (overrides font)')
    font_size: int = Field(56, ge=8, le=200, description='Base font size (auto-scaled based on video)')
    font_color: str = Field('white', description='Font color (name or hex)')

    # Auto-scaling factor (font_size = video_height / factor)
    font_scale_factor: float = Field(
        30.0, ge=15.0, le=60.0, description='Font scale divisor (height/factor). Lower = bigger text.'
    )

    # Background and effects
    background_color: str | None = Field('black@0.6', description='Background color with opacity')
    padding: int = Field(15, ge=0, description='Padding around text')
    border_width: int = Field(2, ge=0, description='Text border/outline width')
    border_color: str = Field('black', description='Text border color')

    # Timing
    start_time: float = Field(0.0, ge=0, description='When to start showing text (seconds)')
    end_time: float | None = Field(None, description='When to stop showing text')
    line_spacing: int = Field(0, ge=0, description='Spacing between wrapped lines')
    max_chars_per_line: int = Field(28, ge=10, le=60, description='Max characters per line for wrapping')


class TextOverlayOutput(BaseModel):
    """Output from text overlay operation."""

    success: bool = Field(..., description='Whether the operation succeeded')
    output_path: str = Field(..., description='Path to the output file')
    command: list[str] = Field(default_factory=list, description='FFmpeg command used')


# Combine Audio Schemas


class CombineAudioInput(BaseModel):
    """Input for combining video with audio."""

    video_path: str = Field(..., description='Path to input video file')
    audio_path: str = Field(..., description='Path to input audio file')
    output_path: str = Field(..., description='Path for output video file')
    replace_audio: bool = Field(True, description='Replace existing audio or mix')


class CombineAudioOutput(BaseModel):
    """Output from combine audio operation."""

    success: bool = Field(..., description='Whether the operation succeeded')
    output_path: str = Field(..., description='Path to the output file')
    command: list[str] = Field(default_factory=list, description='FFmpeg command used')
