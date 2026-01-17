"""AI model registry with auto-discovery.

Models are automatically discovered and registered by scanning the
image/ and video/ subdirectories. Each model file should call
`model_registry.register(MyModel)` at module level.

Usage:
    # Discover and register all models (call once at startup)
    from app.core.ai_models.registry import discover_models
    discover_models()

    # Then use the registry
    from app.core.ai_models.registry import model_registry
    model = model_registry.get('seedance-1.5-pro')
    all_models = model_registry.list_all()
"""

import importlib
import logging
import pkgutil
from typing import Any

from pydantic import BaseModel, Field

from app.core.ai_models.base import (
    ModelCategory,
    ModelDefinition,
    Provider,
)

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Registry of all available AI models."""

    def __init__(self):
        self._models: dict[str, ModelDefinition] = {}

    def register(self, model: ModelDefinition) -> None:
        """Register a model."""
        self._models[model.id] = model

    def get(self, model_id: str) -> ModelDefinition | None:
        """Get a model by ID."""
        return self._models.get(model_id)

    def list_all(self) -> list[ModelDefinition]:
        """List all registered models."""
        return list(self._models.values())

    def list_by_category(self, category: ModelCategory) -> list[ModelDefinition]:
        """List models by category."""
        return [m for m in self._models.values() if m.category == category]

    def list_by_provider(self, provider: Provider) -> list[ModelDefinition]:
        """List models that support a specific provider."""
        return [m for m in self._models.values() if m.supports_provider(provider)]

    def list_ids(self) -> list[str]:
        """List all model IDs."""
        return list(self._models.keys())

    def __contains__(self, model_id: str) -> bool:
        return model_id in self._models

    def __len__(self) -> int:
        return len(self._models)


# Global registry
model_registry = ModelRegistry()

# Model category subdirectories to scan
MODEL_CATEGORIES = ['image', 'video']


def discover_models(base_package: str = 'app.core.ai_models') -> dict[str, list[str]]:
    """Discover and register all AI models by scanning category subdirectories.

    Scans image/ and video/ subdirectories for model files.
    Each model file should call `model_registry.register()` at module level.

    Returns:
        Dict mapping category to list of registered model IDs.
        Example: {'image': ['flux-schnell', 'hidream'], 'video': ['seedance-1.5-pro']}

    Raises:
        RuntimeError: If no models were registered (indicates a problem).
    """
    import sys

    registered: dict[str, list[str]] = {}
    modules_loaded = 0
    modules_failed: list[str] = []

    # Track models before discovery to see what was added
    models_before = set(model_registry.list_ids())

    for category in MODEL_CATEGORIES:
        category_package = f'{base_package}.{category}'
        registered[category] = []

        try:
            package = importlib.import_module(category_package)
        except ImportError:
            msg = f'Failed to import model category package {category_package}'
            logger.exception(msg)
            print(f'ERROR: {msg}', file=sys.stderr)
            continue

        # Get the package path for scanning
        if not hasattr(package, '__path__'):
            continue

        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            # Skip __init__, common, and subpackages
            if module_name.startswith('_') or module_name == 'common' or is_pkg:
                continue

            full_module_name = f'{category_package}.{module_name}'

            try:
                importlib.import_module(full_module_name)
                modules_loaded += 1
                logger.debug(f'Loaded model module: {full_module_name}')
            except Exception:
                modules_failed.append(full_module_name)
                msg = f'Failed to import model module {full_module_name}'
                logger.exception(msg)
                print(f'ERROR: {msg}', file=sys.stderr)

    # Determine which models were added
    models_after = set(model_registry.list_ids())
    new_models = models_after - models_before

    # Categorize registered models
    for model_id in model_registry.list_ids():
        model = model_registry.get(model_id)
        if model:
            cat = model.category.value
            if cat in registered:
                registered[cat].append(model_id)

    # Log summary
    total = len(model_registry)
    logger.info(f'Model discovery: {modules_loaded} modules loaded, {total} models registered')

    if new_models:
        logger.info(f'Newly registered models: {sorted(new_models)}')

    if modules_failed:
        print(f'WARNING: Failed to import {len(modules_failed)} model modules: {modules_failed}', file=sys.stderr)

    # Fail if no models registered
    if total == 0:
        raise RuntimeError('No AI models registered! Check that model files call model_registry.register().')

    return registered


def ensure_models_registered() -> None:
    """Ensure models are registered. Call discover_models() if registry is empty.

    This is a convenience function for activities that need to verify
    the registry is populated before using it.
    """
    if len(model_registry) == 0:
        logger.warning('Model registry empty, running discovery...')
        discover_models()


# API response schemas
class ProviderInfoResponse(BaseModel):
    """Provider info in API response."""

    provider: Provider
    model_id: str


class ModelInfoResponse(BaseModel):
    """Model information for API response."""

    id: str = Field(description='Unique model ID')
    name: str = Field(description='Human-readable name')
    category: ModelCategory = Field(description='Model category')
    description: str = Field(description='Model description')
    author: str = Field(description='Model author')
    capabilities: list[str] = Field(description='Model capabilities')
    providers: list[ProviderInfoResponse] = Field(description='Supported providers')
    avg_generation_time_seconds: float | None = None
    input_schema: dict[str, Any] = Field(description='JSON schema for inputs')

    @classmethod
    def from_model(cls, model: ModelDefinition) -> 'ModelInfoResponse':
        """Create from a ModelDefinition."""
        return cls(
            id=model.id,
            name=model.name,
            category=model.category,
            description=model.description,
            author=model.author,
            capabilities=[c.value for c in model.capabilities],
            providers=[
                ProviderInfoResponse(provider=p, model_id=cfg.model_id) for p, cfg in model.provider_configs.items()
            ],
            avg_generation_time_seconds=model.avg_generation_time_seconds,
            input_schema=model.get_input_schema(),
        )


class ModelsListResponse(BaseModel):
    """Response for listing models."""

    models: list[ModelInfoResponse] = Field(description='List of available models')
    total: int = Field(description='Total number of models')
