"""Replicate client - native async wrapper around the official replicate package."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

import replicate

from app.core.configs import app_config
from app.core.providers.replicate.schemas import (
    ModelInfo,
    ReplicatePrediction,
    ReplicatePredictionStatus,
)

if TYPE_CHECKING:
    from replicate.prediction import Prediction


class ReplicateClient:
    """Async client for Replicate API.

    Uses the native async methods from the replicate library.

    Example:
        client = ReplicateClient()

        # Simple run (waits for completion)
        output = await client.run('black-forest-labs/flux-schnell', {'prompt': 'A sunset'})

        # Or get prediction object with metadata
        prediction = await client.create_prediction('black-forest-labs/flux-schnell', {'prompt': 'A sunset'})
        await prediction.async_wait()
    """

    def __init__(self) -> None:
        """Initialize the Replicate client."""
        if not app_config.REPLICATE_API_KEY:
            raise ValueError('REPLICATE_API_KEY is not set.')
        self._client = replicate.Client(api_token=app_config.REPLICATE_API_KEY)

    async def run(
        self,
        model: str,
        input: dict[str, Any],
        wait: bool = True,
        poll_interval: float = 1.0,  # Not used with native async, kept for compatibility
    ) -> ReplicatePrediction:
        """Run a model and optionally wait for completion.

        Args:
            model: Model identifier (e.g., 'owner/model' or 'owner/model:version')
            input: Model-specific input parameters
            wait: If True, wait for completion
            poll_interval: Deprecated, kept for API compatibility

        Returns:
            ReplicatePrediction with output and metadata
        """
        prediction = await self.create_prediction(model, input)

        if not wait:
            return prediction

        # Use native async wait
        raw_prediction = await self._client.predictions.async_get(prediction.id)
        while raw_prediction.status not in ('succeeded', 'failed', 'canceled'):
            await raw_prediction.async_wait()
            raw_prediction = await self._client.predictions.async_get(prediction.id)

        return self._convert_prediction(raw_prediction)

    async def run_simple(
        self,
        model: str,
        input: dict[str, Any],
    ) -> Any:
        """Run a model and return just the output (simplest API).

        Args:
            model: Model identifier
            input: Model-specific input parameters

        Returns:
            Model output directly (usually a URL or list of URLs)
        """
        return await self._client.async_run(model, input)

    async def create_prediction(
        self,
        model: str,
        input: dict[str, Any],
        webhook: str | None = None,
        webhook_events_filter: list[str] | None = None,
    ) -> ReplicatePrediction:
        """Create a new prediction without waiting for completion."""
        model_owner, model_name, version = self._parse_model_string(model)

        kwargs: dict[str, Any] = {'input': input}
        if webhook:
            kwargs['webhook'] = webhook
        if webhook_events_filter:
            kwargs['webhook_events_filter'] = webhook_events_filter

        if version:
            # Use version-based prediction
            raw_prediction = await self._client.predictions.async_create(version=version, **kwargs)
        else:
            # Use model-based prediction (latest version)
            raw_prediction = await self._client.models.predictions.async_create(
                model=(model_owner, model_name), **kwargs
            )

        return self._convert_prediction(raw_prediction)

    async def get_prediction(self, prediction_id: str) -> ReplicatePrediction:
        """Get the current status of a prediction."""
        raw_prediction = await self._client.predictions.async_get(prediction_id)
        return self._convert_prediction(raw_prediction)

    async def cancel_prediction(self, prediction_id: str) -> ReplicatePrediction:
        """Cancel a running prediction."""
        raw_prediction = await self._client.predictions.async_cancel(prediction_id)
        return self._convert_prediction(raw_prediction)

    async def get_model(self, model: str) -> ModelInfo:
        """Get information about a model including its input schema."""
        model_obj = await self._client.models.async_get(model)

        latest_version = model_obj.latest_version

        return ModelInfo(
            owner=model_obj.owner,
            name=model_obj.name,
            description=model_obj.description,
            visibility=model_obj.visibility,
            latest_version=latest_version.id if latest_version else None,
            input_schema=latest_version.openapi_schema.get('components', {}).get('schemas', {}).get('Input')
            if latest_version
            else None,
            output_schema=latest_version.openapi_schema.get('components', {}).get('schemas', {}).get('Output')
            if latest_version
            else None,
        )

    def _parse_model_string(self, model: str) -> tuple[str, str, str | None]:
        """Parse a model string into owner, name, and optional version."""
        version = None
        if ':' in model:
            model, version = model.rsplit(':', 1)

        parts = model.split('/')
        if len(parts) != 2:
            raise ValueError(f'Invalid model format: {model}')

        return parts[0], parts[1], version

    def _convert_prediction(self, prediction: 'Prediction') -> ReplicatePrediction:
        """Convert replicate.Prediction to our ReplicatePrediction."""
        return ReplicatePrediction(
            id=prediction.id,
            model=f'{prediction.model}' if prediction.model else 'unknown',
            version=prediction.version,
            status=ReplicatePredictionStatus(prediction.status),
            input=prediction.input or {},
            output=prediction.output,
            created_at=self._parse_datetime(prediction.created_at),
            started_at=self._parse_datetime(prediction.started_at),
            completed_at=self._parse_datetime(prediction.completed_at),
            error=prediction.error,
            metrics=prediction.metrics,
            urls=prediction.urls,
        )

    def _parse_datetime(self, value: Any) -> datetime | None:
        """Parse a datetime value from the API."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return None
