"""Base workflow utilities to reduce boilerplate.

Provides:
- WorkflowInput: Base input model with secret auth support
- WorkflowContext: Status tracking with step() context manager
- run_activity(): Simplified activity execution
- upload_output(): Auto-upload to storage
- Standard retry policies
"""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, TypeVar

from pydantic import BaseModel, Field
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from app.temporal.schemas import StepProgress, StorageUploadInput, WorkflowInput, WorkflowStatus

# Standard retry policies
FAST_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_attempts=3,
)

SLOW_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),
    maximum_attempts=3,
)

LONG_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=30),
    maximum_attempts=3,
)


class StepConfig(BaseModel):
    """Configuration for a workflow step."""

    id: str = Field(..., description='Unique step identifier')
    name: str = Field(..., description='Human-readable step name')
    timeout_minutes: float = Field(5.0, description='Activity timeout')
    heartbeat_seconds: float | None = Field(None, description='Heartbeat interval')
    retry_policy: RetryPolicy | None = Field(None, description='Retry policy')

    model_config = {'arbitrary_types_allowed': True}


class WorkflowContext:
    """Shared context for workflow execution.

    Handles status tracking and step progress automatically.

    Usage:
        ctx = WorkflowContext()
        ctx.start(input)  # Pass workflow input for secret validation

        async with ctx.step('generate', 'Generate Image', 20):
            result = await run_activity(generate_image, input)

        ctx.complete()
    """

    def __init__(self) -> None:
        self._status = WorkflowStatus.PENDING
        self._current_step: StepProgress | None = None
        self._completed_steps: list[str] = []
        self._outputs: dict[str, Any] = {}

    @property
    def status(self) -> WorkflowStatus:
        return self._status

    @property
    def current_step(self) -> StepProgress | None:
        return self._current_step

    @property
    def outputs(self) -> dict[str, Any]:
        return self._outputs

    def start(self, input: WorkflowInput) -> None:
        """Mark workflow as running and validate secret key if auth is enabled.

        Args:
            input: Workflow input model (must inherit from WorkflowInput).

        Raises:
            ApplicationError: If secret auth is enabled but key is missing or invalid.
                              Error is non-retryable to prevent brute force attempts.
        """
        # Import config here to avoid sandbox issues
        with workflow.unsafe.imports_passed_through():
            from app.core.configs import app_config

        # Validate secret key if auth is enabled
        if app_config.WORKFLOW_SECRET_ENABLED:
            if not app_config.WORKFLOW_SECRET_KEY:
                raise ApplicationError(
                    'WORKFLOW_SECRET_KEY not configured on server',
                    non_retryable=True,
                )

            if input.secret_key != app_config.WORKFLOW_SECRET_KEY:
                raise ApplicationError(
                    'Authentication failed: invalid secret_key',
                    non_retryable=True,
                )

        self._status = WorkflowStatus.RUNNING

    def complete(self) -> None:
        """Mark workflow as completed."""
        self._status = WorkflowStatus.COMPLETED
        self._current_step = StepProgress(
            step_id='complete',
            step_name='Complete',
            status=WorkflowStatus.COMPLETED,
            progress_pct=100,
            message='Done!',
        )

    def fail(self, error: str) -> None:
        """Mark workflow as failed."""
        self._status = WorkflowStatus.FAILED
        if self._current_step:
            self._current_step.status = WorkflowStatus.FAILED
            self._current_step.message = error

    @asynccontextmanager
    async def step(
        self,
        step_id: str,
        step_name: str,
        progress_pct: int,
        message: str = '',
    ) -> AsyncGenerator[None, None]:
        """Context manager for workflow steps.

        Automatically handles step lifecycle (start, complete, fail).

        Example:
            async with ctx.step('enhance', 'Enhance Prompt', 10):
                result = await run_activity(enhance_prompt, input)
        """
        self._current_step = StepProgress(
            step_id=step_id,
            step_name=step_name,
            status=WorkflowStatus.RUNNING,
            progress_pct=progress_pct,
            message=message or f'{step_name}...',
        )
        try:
            yield
            # Step completed successfully
            self._current_step.status = WorkflowStatus.COMPLETED
            self._completed_steps.append(step_id)
        except Exception as e:
            # Step failed - mark both step and workflow as failed
            self._current_step.status = WorkflowStatus.FAILED
            self._current_step.message = str(e)
            self._status = WorkflowStatus.FAILED
            raise

    def set_output(self, key: str, value: Any) -> None:
        """Store an output value."""
        self._outputs[key] = value

    def get_output(self, key: str) -> Any:
        """Get a stored output value."""
        return self._outputs.get(key)


async def run_activity(
    activity: Callable | str,
    *args: Any,
    timeout_minutes: float = 5.0,
    heartbeat_seconds: float | None = None,
    retry_policy: RetryPolicy | None = None,
) -> Any:
    """Run an activity with standard configuration.

    Args:
        activity: Activity function or string name
        *args: Activity arguments (single input or multiple positional args)
        timeout_minutes: Activity timeout
        heartbeat_seconds: Heartbeat interval for long activities
        retry_policy: Retry configuration

    Examples:
        # Single input (Pydantic model)
        result = await run_activity(enhance_text, EnhanceTextInput(...))

        # Multiple args
        result = await run_activity(generate_image_with_model, 'model-id', {...})
    """
    exec_kwargs: dict[str, Any] = {
        'start_to_close_timeout': timedelta(minutes=timeout_minutes),
        'retry_policy': retry_policy or FAST_RETRY,
    }

    if heartbeat_seconds:
        exec_kwargs['heartbeat_timeout'] = timedelta(seconds=heartbeat_seconds)

    if len(args) == 1:
        # Single input - pass directly
        return await workflow.execute_activity(activity, args[0], **exec_kwargs)
    # Multiple args - use args parameter
    return await workflow.execute_activity(activity, args=args, **exec_kwargs)


T = TypeVar('T')


async def upload_output(url: str, folder: str) -> str:
    """Upload a URL to storage and return the permanent URL.

    This is a common pattern - most generation outputs need to be
    uploaded to permanent storage.
    """
    with workflow.unsafe.imports_passed_through():
        from app.temporal.activities import upload_to_storage

    result = await run_activity(
        upload_to_storage,
        StorageUploadInput(url=url, folder=folder),
        timeout_minutes=2.0,
    )
    return result.url


async def upload_outputs(outputs: dict[str, tuple[str, str]]) -> dict[str, str]:
    """Upload multiple outputs to storage in parallel.

    Args:
        outputs: Dict of {key: (url, folder)} pairs

    Returns:
        Dict of {key: permanent_url} pairs

    Example:
        urls = await upload_outputs({
            'image': (image_result.output_url, 'images'),
            'video': (video_result.output_url, 'videos'),
            'audio': (voice_result.output_url, 'voice'),
        })
        # urls = {'image': 's3://...', 'video': 's3://...', 'audio': 's3://...'}
    """
    import asyncio

    with workflow.unsafe.imports_passed_through():
        from app.temporal.activities import upload_to_storage

    async def upload_one(key: str, url: str, folder: str) -> tuple[str, str]:
        result = await run_activity(
            upload_to_storage,
            StorageUploadInput(url=url, folder=folder),
            timeout_minutes=2.0,
        )
        return key, result.url

    tasks = [upload_one(key, url, folder) for key, (url, folder) in outputs.items()]
    results = await asyncio.gather(*tasks)

    return dict(results)


# =============================================================================
# Media Rewriting Helpers
# =============================================================================


async def maybe_rewrite_video(
    video_url: str,
    input: WorkflowInput,
    playback_speed: float = 1.0,
) -> str:
    """Rewrite video if rewriting is enabled in workflow input.

    Applies metadata modification and visual augmentations to create unique variants.

    Args:
        video_url: URL of the video to potentially rewrite
        input: Workflow input with rewrite settings
        playback_speed: Playback speed multiplier (0.5-2.0)

    Returns:
        Rewritten URL if enabled, original URL otherwise

    Example:
        final_url = await maybe_rewrite_video(video_url, input)
    """
    if not input.rewrite_enabled:
        return video_url

    with workflow.unsafe.imports_passed_through():
        from app.temporal.activities.rewrite import RewriteVideoInput, rewrite_video

    result = await run_activity(
        rewrite_video,
        RewriteVideoInput(
            video_url=video_url,
            playback_speed=playback_speed,
            device=input.rewrite_device,
        ),
        timeout_minutes=3.0,
    )
    return result.rewritten_url


async def maybe_rewrite_image(image_url: str, input: WorkflowInput) -> str:
    """Rewrite a single image if rewriting is enabled in workflow input.

    Args:
        image_url: URL of the image to potentially rewrite
        input: Workflow input with rewrite settings

    Returns:
        Rewritten URL if enabled, original URL otherwise
    """
    if not input.rewrite_enabled:
        return image_url

    urls = await maybe_rewrite_images([image_url], input)
    return urls[0]


async def maybe_rewrite_images(image_urls: list[str], input: WorkflowInput) -> list[str]:
    """Rewrite images if rewriting is enabled in workflow input.

    Applies metadata modification and visual augmentations to create unique variants.

    Args:
        image_urls: URLs of the images to potentially rewrite
        input: Workflow input with rewrite settings

    Returns:
        List of rewritten URLs if enabled, original URLs otherwise

    Example:
        final_urls = await maybe_rewrite_images([url1, url2], input)
    """
    if not input.rewrite_enabled or not image_urls:
        return image_urls

    with workflow.unsafe.imports_passed_through():
        from app.temporal.activities.rewrite import RewriteImagesInput, rewrite_images

    result = await run_activity(
        rewrite_images,
        RewriteImagesInput(image_urls=image_urls, device=input.rewrite_device),
        timeout_minutes=3.0,
    )
    return result.rewritten_urls
