"""Temporal workflow orchestration for GPTMarket.

This package contains:
- activities: Individual tasks (API calls to OpenAI, Replicate, etc.)
- workflows: Orchestration logic (Ruby, Pinterest slideshows, etc.)
- worker: Worker process that executes workflows
- client: Client for starting/querying workflows
- schemas: Shared data types

Quick Start:
    # Start Temporal (dev mode)
    temporal server start-dev

    # Start the worker
    python -m app.temporal.worker

    # Start a workflow
    from app.temporal.client import execute_workflow
    from app.temporal.workflows import HelloWorldWorkflow, HelloWorldInput

    result = await execute_workflow(
        HelloWorldWorkflow.run,
        HelloWorldInput(name="World"),
    )
"""

# Re-export commonly used items
from app.temporal.schemas import (
    ImageGenerationInput,
    ImageGenerationOutput,
    RewriteDevice,
    VoiceGenerationInput,
    VoiceGenerationOutput,
    WorkflowInput,
    WorkflowStatus,
)

__all__ = [
    # Schemas
    'ImageGenerationInput',
    'ImageGenerationOutput',
    'VoiceGenerationInput',
    'VoiceGenerationOutput',
    'WorkflowInput',
    'WorkflowStatus',
    'RewriteDevice',
]


# Lazy imports for client utilities (avoid circular imports)
def get_temporal_client():
    """Get or create the Temporal client."""
    from app.temporal.client import get_temporal_client as _get_client

    return _get_client()


def start_workflow(*args, **kwargs):
    """Start a workflow and return a handle."""
    from app.temporal.client import start_workflow as _start

    return _start(*args, **kwargs)
