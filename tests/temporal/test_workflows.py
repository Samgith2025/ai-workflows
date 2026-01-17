"""Tests for Temporal workflows.

These tests use Temporal's testing framework which runs workflows
in-memory WITHOUT needing a Temporal server.

This is the answer to "Can I test without Temporal?" - YES!

Run tests:
    pytest tests/temporal/test_workflows.py -v
"""

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.temporal.schemas import WorkflowStatus
from app.temporal.workflows.hello_world import (
    HelloWorldInput,
    HelloWorldWorkflow,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
async def workflow_environment():
    """Create a test workflow environment.

    This runs Temporal in-memory - no server needed!
    """
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env


@pytest.fixture
async def worker(workflow_environment):
    """Create a worker with HelloWorld workflow."""
    async with Worker(
        workflow_environment.client,
        task_queue='test-queue',
        workflows=[HelloWorldWorkflow],
    ):
        yield workflow_environment


# =============================================================================
# Tests
# =============================================================================


class TestHelloWorldWorkflow:
    """Tests for the HelloWorldWorkflow."""

    async def test_successful_execution(self, worker):
        """Test that the workflow completes successfully."""
        result = await worker.client.execute_workflow(
            HelloWorldWorkflow.run,
            HelloWorldInput(name='World'),
            id='test-hello-world-1',
            task_queue='test-queue',
        )

        assert result.message == 'Hello, World!'

    async def test_custom_name(self, worker):
        """Test with a custom name."""
        result = await worker.client.execute_workflow(
            HelloWorldWorkflow.run,
            HelloWorldInput(name='Temporal'),
            id='test-hello-world-2',
            task_queue='test-queue',
        )

        assert result.message == 'Hello, Temporal!'

    async def test_query_status(self, worker):
        """Test that we can query workflow status."""
        handle = await worker.client.start_workflow(
            HelloWorldWorkflow.run,
            HelloWorldInput(name='Test'),
            id='test-hello-world-3',
            task_queue='test-queue',
        )

        # Wait for completion
        await handle.result()

        # Query final status
        status = await handle.query(HelloWorldWorkflow.get_status)
        assert status == WorkflowStatus.COMPLETED
