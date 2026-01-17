"""Temporal Worker - runs workflows and activities.

Usage:
    python -m app.temporal.worker
"""

import asyncio
import logging
import signal
import sys
from typing import Any

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from app.core.configs import app_config
from app.temporal.registry import discover_activities, discover_tools, discover_workflows

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('temporal.worker')


def _register_ai_models() -> None:
    """Discover and register all AI models.

    Uses the model registry's auto-discovery to scan image/ and video/
    subdirectories for model files.
    """
    from app.core.ai_models.registry import discover_models

    registered = discover_models()

    # Log per-category breakdown
    for category, model_ids in registered.items():
        if model_ids:
            logger.info(f'Registered {category} models: {model_ids}')


async def run_worker() -> None:
    """Run the Temporal worker."""
    # Register AI models first (before activity discovery)
    _register_ai_models()

    # Discover workflows, activities, and tools
    workflows = discover_workflows()
    activities = discover_activities()
    tools = discover_tools()

    activity_names = [a.__name__ for a in activities]
    logger.info(f'Discovered workflows: {[w.__name__ for w in workflows]}')
    logger.info(f'Discovered activities: {activity_names}')
    logger.info(f'Discovered tools: {tools}')

    if not workflows:
        logger.warning('No workflows discovered!')

    if not activities:
        logger.warning('No activities discovered!')

    logger.info(f'Connecting to Temporal at {app_config.TEMPORAL_HOST}...')

    # Log auth status
    if app_config.WORKFLOW_SECRET_ENABLED:
        if not app_config.WORKFLOW_SECRET_KEY:
            raise ValueError('WORKFLOW_SECRET_ENABLED=True but WORKFLOW_SECRET_KEY is not set!')
        logger.info('Workflow secret authentication ENABLED')
    else:
        logger.info('Workflow secret authentication DISABLED')

    client = await Client.connect(
        app_config.TEMPORAL_HOST,
        namespace=app_config.TEMPORAL_NAMESPACE,
        data_converter=pydantic_data_converter,
    )

    logger.info(f'Connected! Task queue: {app_config.TEMPORAL_TASK_QUEUE}')

    worker = Worker(
        client,
        task_queue=app_config.TEMPORAL_TASK_QUEUE,
        workflows=workflows,
        activities=activities,
    )

    shutdown_event = asyncio.Event()

    def signal_handler(_sig: int, _frame: Any) -> None:
        logger.info('Shutting down...')
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info('Starting worker...')

    async with worker:
        logger.info(f'Worker started! Registered {len(activities)} activities: {activity_names}')
        await shutdown_event.wait()


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
