import uuid
from collections.abc import AsyncGenerator

import httpx

from app.core.configs import app_config
from app.core.services.generation.schemas import (
    GenerationError,
    GenerationResult,
    GenerationStatus,
    GenerationType,
)
from app.core.services.voice.base_service import VoiceServiceInterface
from app.core.services.voice.schemas import (
    VoiceGenerationRequest,
    VoiceModel,
    VoiceProvider,
)


class CartesiaVoiceService(VoiceServiceInterface):
    """Cartesia voice generation service implementation."""

    BASE_URL = 'https://api.cartesia.ai'

    def __init__(self) -> None:
        if not app_config.CARTESIA_API_KEY:
            raise ValueError('CARTESIA_API_KEY is not set. Please set it in your environment or .env file.')
        self._api_key: str = app_config.CARTESIA_API_KEY
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    'X-API-Key': self._api_key,
                    'Cartesia-Version': '2024-06-10',
                    'Content-Type': 'application/json',
                },
                timeout=120.0,
            )
        return self._client

    async def generate(self, request: VoiceGenerationRequest) -> GenerationResult:
        """Generate voice audio from text using Cartesia."""
        task_id = str(uuid.uuid4())
        result = GenerationResult(
            task_id=task_id,
            type=GenerationType.VOICE,
            status=GenerationStatus.PENDING,
            provider='cartesia',
            model=request.voice.model_id,
        )

        try:
            result.mark_processing()
            client = await self._get_client()

            payload = {
                'model_id': request.voice.model_id,
                'transcript': request.text,
                'voice': {
                    'mode': 'id',
                    'id': request.voice.voice_id,
                },
                'output_format': {
                    'container': 'mp3',
                    'encoding': 'mp3',
                    'sample_rate': 44100,
                },
                'language': request.settings.language,
            }

            response = await client.post('/tts/bytes', json=payload)

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                result.mark_failed(
                    GenerationError(
                        code='cartesia_error',
                        message=error_data.get('message', 'Unknown error'),
                        details=error_data,
                    )
                )
                return result

            result.mark_completed()
            result.output_data = {
                'audio_bytes_length': len(response.content),
                'content_type': response.headers.get('content-type'),
            }

            return result

        except httpx.HTTPError as e:
            result.mark_failed(
                GenerationError(
                    code='http_error',
                    message=str(e),
                )
            )
            return result

    async def generate_stream(self, request: VoiceGenerationRequest) -> AsyncGenerator[bytes, None]:
        """Generate voice audio as a stream for real-time playback."""
        client = await self._get_client()

        payload = {
            'model_id': request.voice.model_id,
            'transcript': request.text,
            'voice': {
                'mode': 'id',
                'id': request.voice.voice_id,
            },
            'output_format': {
                'container': 'raw',
                'encoding': 'pcm_s16le',
                'sample_rate': 44100,
            },
            'language': request.settings.language,
        }

        async with client.stream('POST', '/tts/bytes', json=payload) as response:
            async for chunk in response.aiter_bytes():
                yield chunk

    async def list_voices(self) -> list[VoiceModel]:
        """List available voices from Cartesia."""
        client = await self._get_client()
        response = await client.get('/voices')

        if response.status_code != 200:
            return []

        data = response.json()
        return [
            VoiceModel(
                provider=VoiceProvider.CARTESIA,
                model_id='sonic-english',
                voice_id=voice['id'],
                name=voice.get('name'),
            )
            for voice in data.get('voices', [])
        ]

    async def get_voice(self, voice_id: str) -> VoiceModel | None:
        """Get details for a specific Cartesia voice."""
        client = await self._get_client()
        response = await client.get(f'/voices/{voice_id}')

        if response.status_code != 200:
            return None

        voice = response.json()
        return VoiceModel(
            provider=VoiceProvider.CARTESIA,
            model_id='sonic-english',
            voice_id=voice['id'],
            name=voice.get('name'),
        )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
