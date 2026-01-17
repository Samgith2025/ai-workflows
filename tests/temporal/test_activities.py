"""Tests for Temporal activities.

These tests run the actual activity code but with mocked external services.
No Temporal server needed - activities are just regular async functions!

Run tests:
    pytest tests/temporal/test_activities.py -v
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.temporal.schemas import (
    ImageGenerationInput,
    PromptEnhancementInput,
    ScriptGenerationInput,
)


class TestPromptActivities:
    """Tests for prompt/LLM activities."""

    @pytest.fixture
    def mock_openai_response(self):
        """Mock successful OpenAI response."""
        return {
            'choices': [
                {
                    'message': {
                        'content': '{"enhanced_prompt": "A beautiful sunset", "negative_prompt": "blurry", "suggested_aspect_ratio": "16:9", "style_tags": ["nature", "sunset"]}'
                    }
                }
            ]
        }

    async def test_enhance_prompt_success(self, mock_openai_response):
        """Test successful prompt enhancement."""
        with patch('app.temporal.activities.prompt.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            from app.temporal.activities.prompt import enhance_prompt

            # We need to mock the activity context
            with patch('temporalio.activity.logger'):
                result = await enhance_prompt(PromptEnhancementInput(concept='sunset', style='impressionist'))

            assert result.enhanced_prompt == 'A beautiful sunset'
            assert result.suggested_aspect_ratio == '16:9'
            assert 'nature' in result.style_tags

    async def test_generate_script_success(self):
        """Test successful script generation."""
        mock_response_data = {
            'choices': [
                {
                    'message': {
                        'content': '{"title": "AI Revolution", "voiceover_script": "Welcome to the future...", "scene_descriptions": ["Opening shot"], "music_suggestion": "epic"}'
                    }
                }
            ]
        }

        with patch('app.temporal.activities.prompt.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            from app.temporal.activities.prompt import generate_script

            with patch('temporalio.activity.logger'):
                result = await generate_script(
                    ScriptGenerationInput(topic='AI', duration_seconds=60, style='documentary')
                )

            assert result.title == 'AI Revolution'
            assert 'future' in result.voiceover_script


class TestImageActivities:
    """Tests for image generation activities."""

    async def test_generate_image_success(self):
        """Test successful image generation."""
        # Mock the prediction creation and polling
        create_response = {'id': 'pred-123', 'status': 'starting'}
        poll_response = {
            'id': 'pred-123',
            'status': 'succeeded',
            'output': ['https://replicate.com/output/image.png'],
        }

        with patch('app.temporal.activities.image.httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()

            # First call: create prediction
            create_resp = AsyncMock()
            create_resp.status_code = 201
            create_resp.json.return_value = create_response

            # Second call: poll for status (completed)
            poll_resp = AsyncMock()
            poll_resp.status_code = 200
            poll_resp.json.return_value = poll_response

            mock_instance.post = AsyncMock(return_value=create_resp)
            mock_instance.get = AsyncMock(return_value=poll_resp)

            mock_client.return_value.__aenter__.return_value = mock_instance

            from app.temporal.activities.image import generate_image

            with patch('temporalio.activity.logger'), patch('temporalio.activity.heartbeat'):
                result = await generate_image(ImageGenerationInput(prompt='a sunset', model='flux-schnell'))

            assert result.output_url == 'https://replicate.com/output/image.png'


class TestStorageActivities:
    """Tests for storage activities."""

    async def test_upload_to_storage_success(self):
        """Test successful upload to S3."""
        with (
            patch('app.temporal.activities.storage.httpx.AsyncClient') as mock_http,
            patch('app.temporal.activities.storage.get_s3_client') as mock_s3_ctx,
        ):
            # Mock HTTP download
            download_resp = AsyncMock()
            download_resp.status_code = 200
            download_resp.content = b'fake image data'
            download_resp.headers = {'content-type': 'image/png'}

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=download_resp)

            # Mock S3 upload
            mock_s3 = AsyncMock()
            mock_s3_ctx.return_value.__aenter__.return_value = mock_s3

            from app.temporal.activities.storage import upload_to_storage
            from app.temporal.schemas import StorageUploadInput

            with patch('temporalio.activity.logger'):
                result = await upload_to_storage(
                    StorageUploadInput(url='https://example.com/image.png', folder='images')
                )

            assert result.url.startswith('https://')
            assert 'images' in result.key
            mock_s3.put_object.assert_called_once()
