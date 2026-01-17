"""Manual tests for Ruby workflow.

These tests run against real Temporal and AI services.
Make sure:
1. Temporal is running (make temporal)
2. Worker is running (make worker)
3. .env has valid API keys

Run:
    pytest -m manual tests/temporal/manual/test_ruby.py -v
    pytest -m manual tests/temporal/manual/test_ruby.py::test_ruby_basic -v
"""

import uuid

import pytest

from app.temporal.workflows.generations.ruby import RubyInput, RubyWorkflow

pytestmark = pytest.mark.manual


@pytest.fixture
def workflow_id() -> str:
    """Generate a unique workflow ID."""
    return f'test-ruby-{uuid.uuid4().hex[:8]}'


async def test_ruby_basic(temporal_client, task_queue, workflow_id):
    """Test Ruby workflow with minimal settings.

    This runs a full generation - expect ~2-3 minutes.
    """
    result = await temporal_client.execute_workflow(
        RubyWorkflow.run,
        RubyInput(
            topic='Hiring UGC creators',
            emotion='shocked',
            text_overlay="it's 2026 and you're still scrolling tiktok manually to find creators instead of using topyappers.com to export 10k creators in 2 clicks",
            gender='female',
            aspect_ratio='9:16',
            video_duration=5,
            slowed_video=True,
        ),
        id=workflow_id,
        task_queue=task_queue,
    )

    print('\n✅ Ruby workflow completed!')
    print(f'   Face: {result.face_image_url}')
    print(f'   Raw video: {result.raw_video_url}')
    print(f'   Final video: {result.final_video_url}')
    print(f'   Image model: {result.image_model}')
    print(f'   Video model: {result.video_model}')
    print(f'   Image prompt: {result.enhanced_image_prompt[:100]}...')
    print(f'   Video prompt: {result.enhanced_video_prompt[:100]}...')

    assert result.face_image_url.startswith('http')
    assert result.raw_video_url.startswith('http')
    assert result.final_video_url.startswith('http')
    assert len(result.enhanced_image_prompt) > 50
    assert len(result.enhanced_video_prompt) > 20
