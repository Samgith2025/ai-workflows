"""Video generation activities using the model registry.

These activities use the registered AI models and their provider clients.
All models must be registered in the model registry.

Note: AI models are registered at worker startup in worker.py.
"""

from typing import Any

from temporalio import activity

from app.core.ai_models.base import ModelCategory, Provider
from app.core.ai_models.registry import model_registry
from app.core.providers.replicate import ReplicateClient
from app.temporal.schemas import VideoGenerationInput, VideoGenerationOutput


@activity.defn
async def generate_video(input: VideoGenerationInput) -> VideoGenerationOutput:
    """Generate a video using a registered model.

    Args:
        input: VideoGenerationInput with model ID from the registry

    Raises:
        ValueError: If the model is not found in the registry
    """
    activity.logger.info(f'Generating video with model: {input.model}')

    model_def = model_registry.get(input.model)
    if not model_def:
        available = [m.id for m in model_registry.list_by_category(ModelCategory.VIDEO)]
        raise ValueError(f"Model '{input.model}' not found in registry. Available video models: {available}")

    # Build typed input
    input_data: dict[str, Any] = {'prompt': input.prompt}

    if input.image_url:
        input_data['image'] = input.image_url

    typed_input = model_def.validate_input(input_data)

    activity.logger.info(f'Using registered video model: {model_def.name}')

    if model_def.supports_provider(Provider.REPLICATE):
        provider_config = model_def.get_provider_config(Provider.REPLICATE)

        client = ReplicateClient()
        prediction = await client.run(
            model=provider_config.get_full_model_string(),
            input=typed_input.to_replicate(),
            wait=True,
            poll_interval=5.0,  # Video takes longer
        )

        metrics = prediction.metrics or {}

        return VideoGenerationOutput(
            output_url=prediction.get_output_url() or '',
            duration_seconds=metrics.get('predict_time', 0.0),
        )

    raise ValueError(f'Model {model_def.id} has no supported provider configured')


@activity.defn
async def generate_video_with_model(
    model_id: str,
    model_input: dict[str, Any],
    provider: str = 'replicate',
) -> VideoGenerationOutput:
    """Generate a video using a specific registered model with full typed input.

    Args:
        model_id: Registered model ID
        model_input: Dict matching the model's input schema
        provider: Provider to use
    """
    model_def = model_registry.get(model_id)
    if not model_def:
        available = [m.id for m in model_registry.list_by_category(ModelCategory.VIDEO)]
        raise ValueError(f"Model '{model_id}' not found in registry. Available video models: {available}")

    activity.logger.info(f'Generating video with {model_def.name} via {provider}')

    typed_input = model_def.validate_input(model_input)
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
            poll_interval=5.0,
        )

        metrics = prediction.metrics or {}

        return VideoGenerationOutput(
            output_url=prediction.get_output_url() or '',
            duration_seconds=metrics.get('predict_time', 0.0),
        )

    raise ValueError(f'Provider {provider} not yet implemented')


@activity.defn
async def combine_audio_video(video_url: str, audio_url: str) -> str:  # noqa: ARG001
    """Combine a video file with an audio track.

    This is a placeholder - implement with:
    - FFmpeg (local processing)
    - AWS MediaConvert
    - Replicate ffmpeg model
    - Cloud function

    Args:
        video_url: URL to the video file
        audio_url: URL to the audio file (unused in placeholder)

    Returns:
        URL of the combined video (currently returns video_url as placeholder)
    """
    activity.logger.info('Combining audio and video')
    activity.logger.warning('combine_audio_video not yet implemented - returning video URL')

    # TODO: Implement using one of:
    # 1. Replicate's ffmpeg model
    # 2. AWS MediaConvert
    # 3. Local ffmpeg in worker

    return video_url
