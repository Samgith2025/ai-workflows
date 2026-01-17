"""Shared provider clients for external AI services.

This module contains async clients for various AI providers
that can be used by multiple services (image, video, audio, etc.).
"""

from app.core.providers.litellm import (
    CompletionRequest,
    CompletionResponse,
    FallbackConfig,
    LiteLLMClient,
    Message,
    MessageRole,
)
from app.core.providers.replicate import (
    ReplicateClient,
    ReplicatePrediction,
    ReplicatePredictionStatus,
)

__all__ = [
    # Replicate
    'ReplicateClient',
    'ReplicatePrediction',
    'ReplicatePredictionStatus',
    # LiteLLM
    'LiteLLMClient',
    'CompletionRequest',
    'CompletionResponse',
    'FallbackConfig',
    'Message',
    'MessageRole',
]
