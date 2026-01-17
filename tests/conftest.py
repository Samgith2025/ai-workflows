"""Pytest configuration and fixtures.

Test Markers:
    - Default: Unit tests run automatically
    - @pytest.mark.manual: Integration tests against real services
    - @pytest.mark.slow: Tests that take more than a few seconds

Run commands:
    pytest                          # Run unit tests only (default)
    pytest -m manual                # Run manual/integration tests
    pytest -m "manual and ruby"     # Run specific manual tests
    pytest -m "not slow"            # Skip slow tests
    pytest -m ""                    # Run ALL tests (no filter)
"""

import pytest
from faker import Faker


@pytest.fixture(scope='session')
def faker() -> Faker:
    return Faker()


# =============================================================================
# Temporal Fixtures for Manual Tests
# =============================================================================


@pytest.fixture(scope='session')
def temporal_client():
    """Get a Temporal client connected to the real server.

    Only used for manual tests.
    """
    import asyncio

    from temporalio.client import Client
    from temporalio.contrib.pydantic import pydantic_data_converter

    from app.core.configs import app_config

    async def connect():
        return await Client.connect(
            app_config.TEMPORAL_HOST,
            namespace=app_config.TEMPORAL_NAMESPACE,
            data_converter=pydantic_data_converter,
        )

    return asyncio.get_event_loop().run_until_complete(connect())


@pytest.fixture(scope='session')
def task_queue():
    """Get the configured task queue."""
    from app.core.configs import app_config

    return app_config.TEMPORAL_TASK_QUEUE
