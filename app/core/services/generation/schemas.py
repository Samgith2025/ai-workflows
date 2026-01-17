from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GenerationType(str, Enum):
    """Types of generation supported by the platform."""

    IMAGE = 'image'
    VIDEO = 'video'
    VOICE = 'voice'
    PROMPT = 'prompt'


class GenerationStatus(str, Enum):
    """Status of a generation task."""

    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class GenerationError(BaseModel):
    """Error details for failed generations."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class GenerationResult(BaseModel):
    """Unified result type for all generation services.
    This provides a consistent interface for handling generation outputs.
    """

    task_id: str = Field(description='Unique identifier for the generation task')
    type: GenerationType = Field(description='Type of generation')
    status: GenerationStatus = Field(description='Current status of the generation')

    # Output fields
    output_url: str | None = Field(None, description='URL to the generated content')
    output_data: dict[str, Any] | None = Field(None, description='Raw output data from the provider')

    # Metadata
    provider: str = Field(description='Provider used for generation (e.g., replicate, elevenlabs)')
    model: str = Field(description='Model identifier used')
    duration_seconds: float | None = Field(None, description='Duration of generated content (for audio/video)')

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Error handling
    error: GenerationError | None = None

    # Cost tracking
    cost_credits: float | None = Field(None, description='Cost in platform credits')

    @property
    def processing_time_seconds(self) -> float | None:
        """Calculate total processing time if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def mark_processing(self) -> 'GenerationResult':
        """Mark the task as processing."""
        self.status = GenerationStatus.PROCESSING
        self.started_at = datetime.utcnow()
        return self

    def mark_completed(self, output_url: str | None = None, output_urls: list[str] | None = None) -> 'GenerationResult':
        """Mark the task as completed with outputs."""
        self.status = GenerationStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if output_url:
            self.output_url = output_url
        if output_urls:
            self.output_urls = output_urls
        return self

    def mark_failed(self, error: GenerationError) -> 'GenerationResult':
        """Mark the task as failed with error details."""
        self.status = GenerationStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error
        return self


class GenerationRequest(BaseModel):
    """Base request for all generation types."""

    webhook_url: str | None = Field(None, description='URL to receive completion webhook')
    metadata: dict[str, Any] | None = Field(None, description='Custom metadata to include with the result')
