from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.core.services.generation.schemas import GenerationResult
from app.core.services.voice.schemas import VoiceGenerationRequest, VoiceModel


class VoiceServiceInterface(ABC):
    """Interface for voice generation services."""

    async def close(self) -> None:  # noqa: B027
        """Close any resources held by the service.

        Override in implementations that need cleanup.
        """

    @abstractmethod
    async def generate(self, request: VoiceGenerationRequest) -> GenerationResult:
        """Generate voice audio from text.

        Args:
            request: Voice generation request with text and settings

        Returns:
            GenerationResult with audio URL and metadata
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_stream(self, request: VoiceGenerationRequest) -> AsyncGenerator[bytes, None]:
        """Generate voice audio as a stream (for real-time playback).

        Args:
            request: Voice generation request with text and settings

        Yields:
            Audio chunks as bytes
        """
        # Abstract method - mypy requires a body but we yield to make it a generator
        yield b''  # pragma: no cover

    @abstractmethod
    async def list_voices(self) -> list[VoiceModel]:
        """List available voices from the provider.

        Returns:
            List of available voice models
        """
        raise NotImplementedError

    @abstractmethod
    async def get_voice(self, voice_id: str) -> VoiceModel | None:
        """Get details for a specific voice.

        Args:
            voice_id: Provider-specific voice identifier

        Returns:
            Voice model details or None if not found
        """
        raise NotImplementedError
