from app.core.services.voice.base_service import VoiceServiceInterface
from app.core.services.voice.schemas import VoiceProvider


def get_voice_service(provider: VoiceProvider = VoiceProvider.ELEVENLABS) -> VoiceServiceInterface:
    """Factory function to get a voice service instance.

    Args:
        provider: Voice provider to use (default: ElevenLabs)

    Returns:
        VoiceServiceInterface implementation
    """
    if provider == VoiceProvider.ELEVENLABS:
        from app.core.services.voice.providers.elevenlabs.service import ElevenLabsVoiceService

        return ElevenLabsVoiceService()
    if provider == VoiceProvider.CARTESIA:
        from app.core.services.voice.providers.cartesia.service import CartesiaVoiceService

        return CartesiaVoiceService()
    raise ValueError(f'Unsupported voice provider: {provider}')
