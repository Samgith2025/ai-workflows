"""Common enums and types for image models."""

from enum import Enum

from app.core.ai_models.common import AspectRatio


class OutputFormat(str, Enum):
    """Output format options for images."""

    PNG = 'png'
    JPG = 'jpg'
    WEBP = 'webp'


__all__ = ['AspectRatio', 'OutputFormat']
