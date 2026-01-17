"""Shared types for all AI models (image, video, audio)."""

from enum import Enum


class AspectRatio(str, Enum):
    """Universal aspect ratios for media generation.

    These can be used across image and video models.
    Each model handles the conversion to its specific format internally.
    """

    # Portrait (vertical) - mobile/short-form
    PORTRAIT_9_16 = '9:16'  # TikTok, Reels, Shorts
    PORTRAIT_9_21 = '9:21'  # Ultra tall
    PORTRAIT_3_4 = '3:4'  # Traditional portrait
    PORTRAIT_2_3 = '2:3'  # Photo portrait

    # Landscape (horizontal) - desktop/TV
    LANDSCAPE_16_9 = '16:9'  # YouTube, TV, widescreen
    LANDSCAPE_21_9 = '21:9'  # Cinematic ultrawide
    LANDSCAPE_4_3 = '4:3'  # Traditional TV
    LANDSCAPE_3_2 = '3:2'  # Photo landscape

    # Square
    SQUARE = '1:1'  # Instagram feed, profile pics


class OutputFormat(str, Enum):
    """Output format options for generated media."""

    PNG = 'png'
    JPG = 'jpg'
    WEBP = 'webp'
    MP4 = 'mp4'
    WEBM = 'webm'
