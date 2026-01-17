"""AI model definitions with auto-discovery.

Models are automatically discovered by scanning image/ and video/ subdirectories.
Each model file calls `model_registry.register(MyModel)` at module level.

Usage:

    # At application startup (e.g., worker.py), discover all models:
    from app.core.ai_models.registry import discover_models
    discover_models()

    # Then use the registry:
    from app.core.ai_models import model_registry, AspectRatio

    model = model_registry.get('flux-schnell')
    all_models = model_registry.list_all()

    # Or import specific models directly:
    from app.core.ai_models.image import FluxSchnell, FluxSchnellInput

    input = FluxSchnellInput(
        prompt='A beautiful sunset',
        aspect_ratio=AspectRatio.SQUARE,
    )
    replicate_input = input.to_replicate()
"""

from app.core.ai_models.base import (
    ModelCapability,
    ModelCategory,
    ModelDefinition,
    ModelInput,
    Provider,
)
from app.core.ai_models.common import AspectRatio, OutputFormat
from app.core.ai_models.registry import (
    discover_models,
    ensure_models_registered,
    model_registry,
)

__all__ = [
    # Common types
    'AspectRatio',
    'OutputFormat',
    # Base types
    'Provider',
    'ModelCategory',
    'ModelCapability',
    'ModelDefinition',
    'ModelInput',
    # Registry & Discovery
    'model_registry',
    'discover_models',
    'ensure_models_registered',
]
