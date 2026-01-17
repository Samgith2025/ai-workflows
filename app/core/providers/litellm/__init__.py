"""LiteLLM provider with fallback support.

Provides a unified interface for LLM completions with automatic
fallback from primary to secondary model on failures.
"""

from app.core.providers.litellm.client import LiteLLMClient
from app.core.providers.litellm.schemas import (
    CompletionRequest,
    CompletionResponse,
    FallbackConfig,
    Message,
    MessageRole,
    UsageInfo,
)

__all__ = [
    'LiteLLMClient',
    'CompletionRequest',
    'CompletionResponse',
    'FallbackConfig',
    'Message',
    'MessageRole',
    'UsageInfo',
]
