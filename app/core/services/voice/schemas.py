from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.core.services.generation.schemas import GenerationRequest


class VoiceProvider(str, Enum):
    """Supported voice generation providers."""

    ELEVENLABS = 'elevenlabs'
    CARTESIA = 'cartesia'


class VoiceModel(BaseModel):
    """Voice model configuration."""

    provider: VoiceProvider
    model_id: str = Field(description='Provider-specific model identifier')
    voice_id: str = Field(description='Voice identifier for the selected provider')
    name: str | None = Field(None, description='Human-readable voice name')


class VoiceSettings(BaseModel):
    """Voice generation settings."""

    # Common settings
    stability: float = Field(0.5, ge=0.0, le=1.0, description='Voice stability (0-1)')
    similarity_boost: float = Field(0.75, ge=0.0, le=1.0, description='Similarity to original voice (0-1)')
    speed: float = Field(1.0, ge=0.5, le=2.0, description='Speech speed multiplier')

    # ElevenLabs specific
    style: float = Field(0.0, ge=0.0, le=1.0, description='Style exaggeration (ElevenLabs)')
    use_speaker_boost: bool = Field(True, description='Enable speaker boost (ElevenLabs)')

    # Cartesia specific
    emotion: str | None = Field(None, description='Emotion preset (Cartesia)')
    language: str = Field('en', description='Language code')

    # Output settings
    output_format: str = Field('mp3_44100_128', description='Audio output format')


class VoiceGenerationRequest(GenerationRequest):
    """Request for voice generation."""

    text: str = Field(description='Text to convert to speech')
    voice: VoiceModel = Field(description='Voice model configuration')
    settings: VoiceSettings = Field(default_factory=lambda: VoiceSettings(), description='Voice generation settings')

    # Optional features
    timestamps: bool = Field(False, description='Include word-level timestamps in output')

    def to_provider_params(self) -> dict[str, Any]:
        """Convert to provider-specific parameters."""
        if self.voice.provider == VoiceProvider.ELEVENLABS:
            return {
                'text': self.text,
                'model_id': self.voice.model_id,
                'voice_settings': {
                    'stability': self.settings.stability,
                    'similarity_boost': self.settings.similarity_boost,
                    'style': self.settings.style,
                    'use_speaker_boost': self.settings.use_speaker_boost,
                },
            }
        # VoiceProvider.CARTESIA
        return {
            'text': self.text,
            'model_id': self.voice.model_id,
            'voice': {'id': self.voice.voice_id},
            'language': self.settings.language,
            'output_format': self.settings.output_format,
        }
