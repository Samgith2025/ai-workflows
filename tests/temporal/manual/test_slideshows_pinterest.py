"""Manual tests for Pinterest Slideshows workflow.

These tests run against real Temporal and AI services.
Make sure:
1. Temporal is running (make temporal)
2. Worker is running (make worker)
3. .env has valid API keys (GEMINI_API_KEY, GPTMARKET_API_KEY)

Run:
    pytest -m manual tests/temporal/manual/test_slideshows_pinterest.py -v
    pytest -m manual tests/temporal/manual/test_slideshows_pinterest.py::test_pinterest_basic -v
"""

import uuid

import pytest

from app.temporal.workflows.generations.slideshows_pinterest import (
    SlideshowsPinterestInput,
    SlideshowsPinterestWorkflow,
)

pytestmark = pytest.mark.manual


@pytest.fixture
def workflow_id() -> str:
    """Generate a unique workflow ID."""
    return f'test-pinterest-{uuid.uuid4().hex[:8]}'


async def test_pinterest_basic(temporal_client, task_queue, workflow_id):
    """Test Pinterest slideshow workflow with basic input.

    This generates search queries and scrapes Pinterest - expect ~30-60 seconds.
    """
    result = await temporal_client.execute_workflow(
        SlideshowsPinterestWorkflow.run,
        SlideshowsPinterestInput(
            prompt='cozy winter cabin aesthetics with warm lighting and hot cocoa vibes',
        ),
        id=workflow_id,
        task_queue=task_queue,
    )

    print('\n✅ Pinterest slideshow workflow completed!')
    print(f'   Queries used: {result.queries_used}')
    print(f'   Total scraped: {result.total_scraped}')
    print(f'   Images returned: {len(result.images)}')
    for i, img in enumerate(result.images[:5], 1):
        print(f'   {i}. {img.title or "No title"}: {img.image_url[:80]}...')
    if len(result.images) > 5:
        print(f'   ... and {len(result.images) - 5} more')

    assert len(result.images) > 0
    assert len(result.queries_used) > 0
    assert all(img.image_url.startswith('http') for img in result.images)
