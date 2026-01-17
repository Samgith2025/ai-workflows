"""Schemas for LiteLLM provider."""

from enum import Enum

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message role in a conversation."""

    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assistant'


class Message(BaseModel):
    """A single message in the conversation."""

    role: MessageRole = Field(..., description='Role of the message sender')
    content: str = Field(..., description='Message content')


class FallbackConfig(BaseModel):
    """Configuration for fallback behavior."""

    enabled: bool = Field(True, description='Whether fallback is enabled')
    fallback_model: str = Field(..., description='Model to use on primary failure')
    max_retries: int = Field(2, description='Max retries per model before fallback')
    retry_exceptions: list[str] = Field(
        default_factory=lambda: [
            'RateLimitError',
            'APIConnectionError',
            'Timeout',
            'ServiceUnavailableError',
        ],
        description='Exception types that trigger retry/fallback',
    )


class CompletionRequest(BaseModel):
    """Request for LLM completion."""

    messages: list[Message] = Field(..., description='Conversation messages')
    model: str | None = Field(None, description='Model to use (defaults to primary)')
    temperature: float = Field(0.7, ge=0.0, le=2.0, description='Sampling temperature')
    max_tokens: int = Field(2048, ge=1, description='Maximum tokens to generate')
    json_mode: bool = Field(False, description='Request JSON output format')
    timeout: int | None = Field(None, description='Request timeout in seconds')


class UsageInfo(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(0, description='Tokens in the prompt')
    completion_tokens: int = Field(0, description='Tokens in the completion')
    total_tokens: int = Field(0, description='Total tokens used')


class CompletionResponse(BaseModel):
    """Response from LLM completion."""

    content: str = Field(..., description='Generated content')
    model: str = Field(..., description='Model that generated the response')
    usage: UsageInfo = Field(default_factory=UsageInfo, description='Token usage')
    fallback_used: bool = Field(False, description='Whether fallback model was used')
    parsed: dict | None = Field(None, description='Parsed JSON if json_mode was enabled')
