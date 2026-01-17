"""Replicate schemas - generic types for working with Replicate API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReplicatePredictionStatus(str, Enum):
    """Status of a Replicate prediction."""

    STARTING = 'starting'
    PROCESSING = 'processing'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELED = 'canceled'


class ReplicatePrediction(BaseModel):
    """Generic Replicate prediction result.

    This can hold any model's output, making it flexible for the
    hundreds of different models available on Replicate.
    """

    id: str = Field(description='Prediction ID')
    model: str = Field(description='Model identifier')
    version: str | None = Field(None, description='Model version hash')
    status: ReplicatePredictionStatus = Field(description='Current status')

    # Input/Output
    input: dict[str, Any] = Field(default_factory=dict)
    output: Any = Field(None, description='Model output (type varies by model)')

    # Timing
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Error
    error: str | None = None

    # Metrics
    metrics: dict[str, Any] | None = None

    # URLs
    urls: dict[str, str] | None = None

    @property
    def is_terminal(self) -> bool:
        """Check if the prediction has reached a terminal state."""
        return self.status in [
            ReplicatePredictionStatus.SUCCEEDED,
            ReplicatePredictionStatus.FAILED,
            ReplicatePredictionStatus.CANCELED,
        ]

    @property
    def is_successful(self) -> bool:
        """Check if the prediction succeeded."""
        return self.status == ReplicatePredictionStatus.SUCCEEDED

    @property
    def predict_time(self) -> float | None:
        """Get prediction time in seconds if available."""
        if self.metrics and 'predict_time' in self.metrics:
            return float(self.metrics['predict_time'])
        return None

    def get_output_url(self) -> str | None:
        """Get the primary output URL."""
        if self.output is None:
            return None

        if isinstance(self.output, str):
            return self.output

        if isinstance(self.output, list) and self.output:
            first = self.output[0]
            if isinstance(first, str):
                return first
            if hasattr(first, 'url'):
                return str(first.url)

        if isinstance(self.output, dict) and 'url' in self.output:
            return str(self.output['url'])

        return None

    def get_all_output_urls(self) -> list[str]:
        """Get all output URLs from the prediction."""
        urls: list[str] = []

        if self.output is None:
            return urls

        if isinstance(self.output, str):
            return [self.output]

        if isinstance(self.output, list):
            for item in self.output:
                if isinstance(item, str):
                    urls.append(item)
                elif hasattr(item, 'url'):
                    urls.append(item.url)

        return urls


class ModelInfo(BaseModel):
    """Information about a Replicate model."""

    owner: str = Field(description='Model owner/organization')
    name: str = Field(description='Model name')
    description: str | None = None
    visibility: str = Field(default='public')
    latest_version: str | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None

    @property
    def full_name(self) -> str:
        """Get full model identifier (owner/name)."""
        return f'{self.owner}/{self.name}'
