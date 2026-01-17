"""LiteLLM client with automatic fallback support.

Provides a unified interface for multiple LLM providers with automatic
fallback from primary model to secondary on failures.

Example:
    client = LiteLLMClient()

    response = await client.complete(
        messages=[Message(role=MessageRole.USER, content='Hello!')],
    )

    # Or with custom request
    response = await client.complete(
        CompletionRequest(
            messages=[...],
            temperature=0.5,
            json_mode=True,
        )
    )
"""

import json
import os
from typing import Any

from pydantic import BaseModel

from app.core.configs import app_config
from app.core.providers.litellm.schemas import (
    CompletionRequest,
    CompletionResponse,
    FallbackConfig,
    Message,
    MessageRole,
    UsageInfo,
)


class LiteLLMClient:
    """Async client for LiteLLM with fallback support.

    Automatically falls back from primary model to fallback model
    on rate limits, timeouts, and other transient errors.
    """

    def __init__(
        self,
        primary_model: str | None = None,
        fallback_config: FallbackConfig | None = None,
    ) -> None:
        """Initialize the LiteLLM client.

        Args:
            primary_model: Override default primary model
            fallback_config: Custom fallback configuration
        """
        self._primary_model = primary_model or app_config.LITELLM_PRIMARY_MODEL
        self._fallback_config = fallback_config or FallbackConfig(
            enabled=app_config.LITELLM_FALLBACK_ENABLED,
            fallback_model=app_config.LITELLM_FALLBACK_MODEL,
            max_retries=app_config.LITELLM_MAX_RETRIES,
        )
        self._timeout = app_config.LITELLM_TIMEOUT

        # Set API keys for litellm
        self._setup_api_keys()

    def _setup_api_keys(self) -> None:
        """Set up API keys for various providers."""
        if app_config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = app_config.GEMINI_API_KEY
        if app_config.OPENAI_API_KEY:
            os.environ['OPENAI_API_KEY'] = app_config.OPENAI_API_KEY

    async def complete(
        self,
        messages: list[Message] | None = None,
        request: CompletionRequest | None = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        """Generate a completion with automatic fallback.

        Args:
            messages: List of messages (alternative to request)
            request: Full completion request
            **kwargs: Additional arguments passed to CompletionRequest

        Returns:
            CompletionResponse with generated content

        Example:
            # Simple usage
            response = await client.complete(
                messages=[Message(role=MessageRole.USER, content='Hi!')],
            )

            # With request object
            response = await client.complete(
                request=CompletionRequest(
                    messages=[...],
                    temperature=0.5,
                )
            )
        """
        # Build request from arguments
        if request is None:
            if messages is None:
                raise ValueError('Either messages or request must be provided')
            request = CompletionRequest(messages=messages, **kwargs)

        # Try primary model first
        model = request.model or self._primary_model

        try:
            return await self._complete_with_model(request, model, fallback_used=False)
        except Exception as primary_error:
            if not self._fallback_config.enabled:
                raise

            if not self._should_fallback(primary_error):
                raise

            # Try fallback model
            fallback_model = self._fallback_config.fallback_model
            try:
                return await self._complete_with_model(request, fallback_model, fallback_used=True)
            except Exception as fallback_error:
                # Both failed, raise the original error with context
                raise RuntimeError(
                    f'Both primary ({model}) and fallback ({fallback_model}) models failed. '
                    f'Primary error: {primary_error}. Fallback error: {fallback_error}'
                ) from fallback_error

    async def complete_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        """Simple text completion helper.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional arguments for CompletionRequest

        Returns:
            CompletionResponse
        """
        messages = []
        if system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(Message(role=MessageRole.USER, content=prompt))

        return await self.complete(messages=messages, **kwargs)

    async def complete_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> dict | BaseModel:
        """Complete and parse JSON response.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            response_model: Optional Pydantic model to parse response into
            **kwargs: Additional arguments

        Returns:
            Parsed dict or Pydantic model instance
        """
        response = await self.complete_text(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            **kwargs,
        )

        if response.parsed is None:
            try:
                parsed = json.loads(response.content)
            except json.JSONDecodeError as e:
                raise ValueError(f'Failed to parse JSON response: {e}') from e
        else:
            parsed = response.parsed

        if response_model:
            return response_model.model_validate(parsed)

        return parsed

    async def _complete_with_model(
        self,
        request: CompletionRequest,
        model: str,
        fallback_used: bool,
    ) -> CompletionResponse:
        """Execute completion with a specific model."""
        # Import litellm here to avoid import issues
        import litellm

        # Build messages for litellm
        messages = [{'role': msg.role.value, 'content': msg.content} for msg in request.messages]

        # Build kwargs
        kwargs: dict[str, Any] = {
            'model': model,
            'messages': messages,
            'temperature': request.temperature,
            'max_tokens': request.max_tokens,
            'timeout': request.timeout or self._timeout,
            'num_retries': self._fallback_config.max_retries,
        }

        if request.json_mode:
            kwargs['response_format'] = {'type': 'json_object'}

        # Make the async call
        response = await litellm.acompletion(**kwargs)

        # Extract content
        content = response.choices[0].message.content or ''

        # Parse JSON if requested
        parsed = None
        if request.json_mode:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                pass

        # Build usage info
        usage = UsageInfo(
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
        )

        return CompletionResponse(
            content=content,
            model=model,
            usage=usage,
            fallback_used=fallback_used,
            parsed=parsed,
        )

    def _should_fallback(self, error: Exception) -> bool:
        """Determine if we should attempt fallback for this error."""
        error_type = type(error).__name__

        # Check if error type is in retry exceptions
        for exc_name in self._fallback_config.retry_exceptions:
            if exc_name in error_type or exc_name.lower() in str(error).lower():
                return True

        # Also fallback on common transient errors
        transient_indicators = [
            'rate limit',
            'timeout',
            'connection',
            'unavailable',
            'overloaded',
            '429',
            '503',
            '502',
        ]

        error_str = str(error).lower()
        return any(indicator in error_str for indicator in transient_indicators)


def get_litellm_client(
    primary_model: str | None = None,
    fallback_config: FallbackConfig | None = None,
) -> LiteLLMClient:
    """Factory function to create a LiteLLM client.

    Args:
        primary_model: Override default primary model
        fallback_config: Custom fallback configuration

    Returns:
        Configured LiteLLMClient instance
    """
    return LiteLLMClient(
        primary_model=primary_model,
        fallback_config=fallback_config,
    )
