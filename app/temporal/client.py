"""Temporal Client - for starting and querying workflows.

Use this from your FastAPI routes or Next.js server actions.

Example usage:
    from app.temporal.client import start_workflow, execute_workflow
    from app.temporal.workflows import HelloWorldWorkflow, HelloWorldInput

    # Start and wait for result
    result = await execute_workflow(
        HelloWorldWorkflow.run,
        HelloWorldInput(name="World"),
    )

    # Or start and get handle for async tracking
    handle = await start_workflow(
        HelloWorldWorkflow.run,
        HelloWorldInput(name="World"),
    )
    status = await handle.query(HelloWorldWorkflow.get_status)
    result = await handle.result()

Authentication:
    When WORKFLOW_SECRET_ENABLED=True (production), include secret_key in workflow input:
    result = await execute_workflow(
        MyWorkflow.run,
        MyInput(secret_key='your-secret-key', ...),
    )
"""

import logging
import uuid
from typing import Any, TypeVar

from temporalio.client import Client, WorkflowHandle
from temporalio.contrib.pydantic import pydantic_data_converter

from app.core.configs import app_config

logger = logging.getLogger('temporal.client')

T = TypeVar('T')


class _ClientHolder:
    """Holder for singleton Temporal client instance."""

    instance: Client | None = None


async def get_temporal_client() -> Client:
    """Get or create the Temporal client.

    Uses a singleton pattern to reuse connections.
    """
    if _ClientHolder.instance is None:
        logger.info('Connecting to Temporal at %s...', app_config.TEMPORAL_HOST)

        try:
            _ClientHolder.instance = await Client.connect(
                app_config.TEMPORAL_HOST,
                namespace=app_config.TEMPORAL_NAMESPACE,
                data_converter=pydantic_data_converter,
            )

            logger.info('Connected to Temporal successfully (namespace: %s)', app_config.TEMPORAL_NAMESPACE)
        except Exception:
            logger.exception('Failed to connect to Temporal at %s', app_config.TEMPORAL_HOST)
            raise

    return _ClientHolder.instance


async def start_workflow(
    workflow: Any,
    arg: Any,
    *,
    id: str | None = None,
    task_queue: str | None = None,
) -> WorkflowHandle:
    """Start a workflow and return a handle.

    Args:
        workflow: The workflow run method (e.g., HelloWorldWorkflow.run)
        arg: The workflow input (must include secret_key when auth enabled)
        id: Optional workflow ID (auto-generated if not provided)
        task_queue: Optional task queue (uses default if not provided)

    Returns:
        WorkflowHandle to query/wait for the workflow

    Example:
        handle = await start_workflow(
            HelloWorldWorkflow.run,
            HelloWorldInput(name="World"),
        )
        result = await handle.result()
    """
    client = await get_temporal_client()

    workflow_id = id or f'workflow-{uuid.uuid4().hex[:12]}'
    queue = task_queue or app_config.TEMPORAL_TASK_QUEUE

    handle = await client.start_workflow(
        workflow,
        arg,
        id=workflow_id,
        task_queue=queue,
    )

    return handle


async def execute_workflow(
    workflow: Any,
    arg: Any,
    *,
    id: str | None = None,
    task_queue: str | None = None,
) -> Any:
    """Start a workflow and wait for its result.

    This is a convenience method that combines start + wait.

    Args:
        workflow: The workflow run method
        arg: The workflow input (must include secret_key when auth enabled)
        id: Optional workflow ID
        task_queue: Optional task queue

    Returns:
        The workflow result
    """
    handle = await start_workflow(workflow, arg, id=id, task_queue=task_queue)
    return await handle.result()


async def get_workflow_handle(workflow_id: str) -> WorkflowHandle:
    """Get a handle to an existing workflow by ID.

    Useful for querying status or waiting for completion of
    a previously started workflow.

    Args:
        workflow_id: The workflow ID

    Returns:
        WorkflowHandle
    """
    client = await get_temporal_client()
    return client.get_workflow_handle(workflow_id)


async def cancel_workflow(workflow_id: str) -> None:
    """Cancel a running workflow.

    Args:
        workflow_id: The workflow ID to cancel
    """
    handle = await get_workflow_handle(workflow_id)
    await handle.cancel()


async def query_workflow(workflow_id: str, query_name: str) -> Any:
    """Query a workflow for its current state.

    Args:
        workflow_id: The workflow ID
        query_name: Name of the query (e.g., 'get_status', 'get_current_step')

    Returns:
        The query result
    """
    handle = await get_workflow_handle(workflow_id)
    return await handle.query(query_name)
