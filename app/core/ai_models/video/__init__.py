"""Video generation models.

Available models:
- Kling v2.6: High-quality video generation with audio by Kuaishou
- Seedance 1.5 Pro: High-quality image-to-video generation by ByteDance
"""

from app.core.ai_models.common import AspectRatio
from app.core.ai_models.video.kling import KlingV26, KlingV26Input
from app.core.ai_models.video.seedance import Seedance15Pro, Seedance15ProInput

__all__ = [
    # Common types
    'AspectRatio',
    # Kling
    'KlingV26',
    'KlingV26Input',
    # Seedance
    'Seedance15Pro',
    'Seedance15ProInput',
]
