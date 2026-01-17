"""Temporal workflows - orchestration logic for generation pipelines.

Workflows define the sequence of activities and their dependencies.
They use the base utilities for common patterns like:
- Status tracking with step() context manager
- Auto-upload to storage
- Standard retry policies

See .cursorrules for the recommended workflow structure.
"""

from app.temporal.workflows.base import (
    FAST_RETRY,
    LONG_RETRY,
    SLOW_RETRY,
    WorkflowContext,
    run_activity,
    upload_output,
    upload_outputs,
)
from app.temporal.workflows.generations import (
    GENERATION_WORKFLOWS,
    RubyInput,
    RubyOutput,
    RubyWorkflow,
)
from app.temporal.workflows.hello_world import (
    HelloWorldInput,
    HelloWorldOutput,
    HelloWorldWorkflow,
)

__all__ = [
    # Test workflow
    'HelloWorldWorkflow',
    'HelloWorldInput',
    'HelloWorldOutput',
    # Generation workflows (frontend-facing)
    'GENERATION_WORKFLOWS',
    'RubyWorkflow',
    'RubyInput',
    'RubyOutput',
    # Base utilities
    'WorkflowContext',
    'run_activity',
    'upload_output',
    'upload_outputs',
    # Retry policies
    'FAST_RETRY',
    'SLOW_RETRY',
    'LONG_RETRY',
]
