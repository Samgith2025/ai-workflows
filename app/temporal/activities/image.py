"""Image generation activities using the model registry.

These activities use the registered AI models and their provider clients.
All models must be registered in the model registry.
"""

from typing import Any

from temporalio import activity

# Import to ensure all models are registered
import app.core.ai_models  # noqa: F401
from app.core.ai_models.base import ModelCategory, Provider
from app.core.ai_models.registry import model_registry
from app.core.providers.replicate import ReplicateClient
from app.temporal.schemas import ImageGenerationInput, ImageGenerationOutput


@activity.defn
async def generate_image(input: ImageGenerationInput) -> ImageGenerationOutput:
    """Generate an image using a registered model.

    Args:
        input: ImageGenerationInput with model ID from the registry
               (e.g., 'flux-schnell', 'flux-dev', 'hidream-fast')

    Raises:
        ValueError: If the model is not found in the registry
    """
    activity.logger.info(f'Generating image with model: {input.model}')

    model_def = model_registry.get(input.model)
    if not model_def:
        available = [m.id for m in model_registry.list_by_category(ModelCategory.IMAGE)]
        raise ValueError(f"Model '{input.model}' not found in registry. Available image models: {available}")

    # Build typed input using the model's input class
    input_data: dict[str, Any] = {'prompt': input.prompt}

    # Map common fields based on what the model supports
    input_schema = model_def.input_class.model_fields

    if 'aspect_ratio' in input_schema and input.aspect_ratio:
        input_data['aspect_ratio'] = input.aspect_ratio

    if 'negative_prompt' in input_schema and input.negative_prompt:
        input_data['negative_prompt'] = input.negative_prompt

    # Validate and create typed input
    typed_input = model_def.validate_input(input_data)

    activity.logger.info(f'Using registered model: {model_def.name}')

    # Get the provider config (prefer Replicate)
    if model_def.supports_provider(Provider.REPLICATE):
        provider_config = model_def.get_provider_config(Provider.REPLICATE)
        replicate_input = typed_input.to_replicate()

        client = ReplicateClient()
        prediction = await client.run(
            model=provider_config.get_full_model_string(),
            input=replicate_input,
            wait=True,
        )

        return ImageGenerationOutput(
            output_url=prediction.get_output_url() or '',
            model=model_def.id,
        )

    # TODO: Add FAL, RunPod support when needed
    raise ValueError(f'Model {model_def.id} has no supported provider configured')


@activity.defn
async def generate_image_with_model(
    model_id: str,
    model_input: dict[str, Any],
    provider: str = 'replicate',
) -> ImageGenerationOutput:
    """Generate an image using a specific registered model with full typed input.

    This is the preferred activity for advanced usage where you want to use
    all the model-specific parameters.

    Args:
        model_id: Registered model ID (e.g., 'flux-schnell', 'flux-dev', 'hidream-fast')
        model_input: Dict matching the model's input schema
        provider: Provider to use ('replicate', 'fal', etc.)

    Example:
        await generate_image_with_model(
            'flux-dev',
            {
                'prompt': 'A sunset over mountains',
                'aspect_ratio': '16:9',
                'guidance_scale': 3.5,
                'num_inference_steps': 28,
            },
        )

        await generate_image_with_model(
            'hidream-fast',
            {
                'prompt': 'A cyberpunk city',
                'resolution': '1024 × 1024 (Square)',
                'speed_mode': 'Extra Juiced 🚀 (even more speed)',
            },
        )
    """
    model_def = model_registry.get(model_id)
    if not model_def:
        available = [m.id for m in model_registry.list_by_category(ModelCategory.IMAGE)]
        raise ValueError(f"Model '{model_id}' not found in registry. Available image models: {available}")

    activity.logger.info(f'Generating with {model_def.name} via {provider}')

    # Validate and create typed input
    typed_input = model_def.validate_input(model_input)

    # Get provider
    provider_enum = Provider(provider)
    if not model_def.supports_provider(provider_enum):
        available_providers = [p.value for p in model_def.providers]
        raise ValueError(
            f"Model '{model_id}' does not support provider '{provider}'. Available providers: {available_providers}"
        )

    provider_config = model_def.get_provider_config(provider_enum)

    if provider_enum == Provider.REPLICATE:
        client = ReplicateClient()
        prediction = await client.run(
            model=provider_config.get_full_model_string(),
            input=typed_input.to_replicate(),
            wait=True,
        )

        return ImageGenerationOutput(
            output_url=prediction.get_output_url() or '',
            model=model_id,
        )

    # TODO: Add FAL, RunPod support
    raise ValueError(f'Provider {provider} not yet implemented')
