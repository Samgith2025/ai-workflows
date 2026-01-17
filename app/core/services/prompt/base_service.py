from abc import ABC, abstractmethod

from app.core.services.prompt.schemas import (
    PromptGenerationRequest,
    PromptResult,
    PromptTemplate,
)


class PromptServiceInterface(ABC):
    """Interface for prompt generation services."""

    async def close(self) -> None:  # noqa: B027
        """Close any resources held by the service.

        Override in implementations that need cleanup.
        """

    @abstractmethod
    async def generate(self, request: PromptGenerationRequest) -> PromptResult:
        """Generate a prompt/content using an LLM.

        Args:
            request: Prompt generation request with template and variables

        Returns:
            PromptResult with generated content
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_structured(
        self,
        template: PromptTemplate,
        variables: dict,
        model: str | None = None,
    ) -> dict:
        """Generate structured JSON output using an LLM.

        Args:
            template: Prompt template with output schema
            variables: Variables to fill in the template
            model: Optional model override

        Returns:
            Parsed JSON object matching the template's output schema
        """
        raise NotImplementedError

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> PromptResult:
        """Simple completion without using templates.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            json_mode: Whether to request JSON output

        Returns:
            PromptResult with generated content
        """
        raise NotImplementedError
