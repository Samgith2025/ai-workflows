from app.core.services.prompt.base_service import PromptServiceInterface
from app.core.services.prompt.schemas import PromptProvider


def get_prompt_service(provider: PromptProvider = PromptProvider.OPENAI) -> PromptServiceInterface:
    """Factory function to get a prompt service instance.

    Args:
        provider: LLM provider to use (default: OpenAI)

    Returns:
        PromptServiceInterface implementation
    """
    if provider == PromptProvider.OPENAI:
        from app.core.services.prompt.providers.openai.service import OpenAIPromptService

        return OpenAIPromptService()
    raise ValueError(f'Unsupported prompt provider: {provider}')
