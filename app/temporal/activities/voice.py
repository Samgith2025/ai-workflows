"""Voice generation activities using existing VoiceService.

These activities handle text-to-speech generation using ElevenLabs or Cartesia.
"""

from temporalio import activity

from app.core.services.voice.schemas import VoiceGenerationRequest, VoiceModel, VoiceProvider
from app.core.services.voice.service import get_voice_service
from app.temporal.activities.storage import upload_bytes_to_storage
from app.temporal.schemas import VoiceGenerationInput, VoiceGenerationOutput


@activity.defn
async def generate_voice(input: VoiceGenerationInput) -> VoiceGenerationOutput:
    """Generate voice audio from text using ElevenLabs.

    Uses the existing VoiceService for generation and uploads to S3.
    """
    activity.logger.info(f'Generating voice with voice_id: {input.voice_id}')

    service = get_voice_service(VoiceProvider.ELEVENLABS)

    try:
        voice = VoiceModel(
            provider=VoiceProvider.ELEVENLABS,
            model_id=input.model_id,
            voice_id=input.voice_id,
        )

        request = VoiceGenerationRequest(
            text=input.text,
            voice=voice,
        )

        # Note: The current ElevenLabs service returns bytes in output_data
        # We need to stream and upload to S3
        # For now, use the streaming approach

        audio_chunks: list[bytes] = []
        async for chunk in service.generate_stream(request):
            audio_chunks.append(chunk)

        audio_bytes = b''.join(audio_chunks)

        # Upload to S3
        output_url = await upload_bytes_to_storage(
            data=audio_bytes,
            content_type='audio/mpeg',
            folder='voice',
            extension='mp3',
        )

        # Estimate duration (rough: ~150 words per minute, ~5 chars per word)
        estimated_duration = len(input.text) / 5 / 150 * 60

        return VoiceGenerationOutput(
            output_url=output_url,
            duration_seconds=estimated_duration,
        )
    finally:
        await service.close()


@activity.defn
async def generate_voice_with_options(
    text: str,
    provider: str = 'elevenlabs',
    voice_id: str = 'EXAVITQu4vr4xnSDxMaL',
    model_id: str = 'eleven_multilingual_v2',
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> VoiceGenerationOutput:
    """Generate voice with full control over voice settings.

    Args:
        text: Text to synthesize
        provider: Voice provider ('elevenlabs' or 'cartesia')
        voice_id: Provider-specific voice ID
        model_id: Provider-specific model ID
        stability: Voice stability (0-1)
        similarity_boost: Similarity boost (0-1)
    """
    activity.logger.info(f'Generating voice with {provider}')

    provider_enum = VoiceProvider(provider)
    service = get_voice_service(provider_enum)

    try:
        voice = VoiceModel(
            provider=provider_enum,
            model_id=model_id,
            voice_id=voice_id,
        )

        request = VoiceGenerationRequest(
            text=text,
            voice=voice,
        )

        # Update settings if supported
        if hasattr(request, 'settings') and request.settings:
            request.settings.stability = stability
            request.settings.similarity_boost = similarity_boost

        audio_chunks: list[bytes] = []
        async for chunk in service.generate_stream(request):
            audio_chunks.append(chunk)

        audio_bytes = b''.join(audio_chunks)

        output_url = await upload_bytes_to_storage(
            data=audio_bytes,
            content_type='audio/mpeg',
            folder='voice',
            extension='mp3',
        )

        estimated_duration = len(text) / 5 / 150 * 60

        return VoiceGenerationOutput(
            output_url=output_url,
            duration_seconds=estimated_duration,
        )
    finally:
        await service.close()
