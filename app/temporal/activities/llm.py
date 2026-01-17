"""LLM activities using LiteLLM with fallback support.

These activities provide flexible LLM capabilities for workflows:
- enhance_text: Enhance/transform any text with instructions
- generate_json: Generate structured JSON output
- complete_chat: Full chat completion with messages

All activities use LiteLLM with automatic fallback from primary to secondary model.
"""

from pydantic import BaseModel, Field
from temporalio import activity

from app.core.providers.litellm import (
    CompletionRequest,
    CompletionResponse,
    LiteLLMClient,
)

# =============================================================================
# Activity-specific schemas (minimal, reuse provider schemas where possible)
# =============================================================================


class EnhanceTextInput(BaseModel):
    """Input for text enhancement."""

    text: str = Field(..., description='Original text to enhance')
    instructions: str = Field(..., description='Instructions for how to enhance the text')
    temperature: float = Field(0.7, ge=0.0, le=2.0, description='Creativity level')
    max_tokens: int = Field(2048, description='Maximum tokens in response')


class EnhanceTextOutput(BaseModel):
    """Output from text enhancement."""

    enhanced_text: str = Field(..., description='The enhanced text')
    model_used: str = Field(..., description='Model that generated the response')
    fallback_used: bool = Field(False, description='Whether fallback model was used')


class ImagePromptOutput(BaseModel):
    """Output from image prompt enhancement."""

    enhanced_prompt: str = Field(..., description='Enhanced image generation prompt')
    negative_prompt: str = Field('', description='What to avoid in the image')
    model_used: str = Field(..., description='Model that generated the response')
    fallback_used: bool = Field(False, description='Whether fallback model was used')


# =============================================================================
# Activities
# =============================================================================


@activity.defn
async def enhance_text(input: EnhanceTextInput) -> EnhanceTextOutput:
    """Enhance or transform text based on instructions.

    This is a flexible activity for any text transformation:
    - Prompt enhancement for image/video generation
    - Text rewriting, summarization, expansion
    - Style transfer, tone adjustment

    Example:
        result = await enhance_text(EnhanceTextInput(
            text='a sunset',
            instructions='Transform into a detailed image generation prompt',
        ))
    """
    activity.logger.info(f'Enhancing text: "{input.text[:50]}..."')

    client = LiteLLMClient()

    system_prompt = (
        'You are an expert at text enhancement and transformation. '
        "Follow the user's instructions precisely. "
        'Output ONLY the enhanced text, no explanations or preamble.'
    )

    user_prompt = f"""## Original Text
{input.text}

## Instructions
{input.instructions}

## Enhanced Text"""

    response = await client.complete_text(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=input.temperature,
        max_tokens=input.max_tokens,
    )

    return EnhanceTextOutput(
        enhanced_text=response.content.strip(),
        model_used=response.model,
        fallback_used=response.fallback_used,
    )


@activity.defn
async def generate_json(request: CompletionRequest) -> CompletionResponse:
    """Generate structured JSON data from a completion request.

    Uses the LiteLLM CompletionRequest/Response directly for full flexibility.

    Example:
        result = await generate_json(CompletionRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content='Output valid JSON'),
                Message(role=MessageRole.USER, content='List 3 colors'),
            ],
            json_mode=True,
        ))
        # result.parsed = {"colors": ["red", "green", "blue"]}
    """
    activity.logger.info('Generating JSON response')

    # Ensure json_mode is enabled
    request_with_json = CompletionRequest(
        messages=request.messages,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        json_mode=True,
        timeout=request.timeout,
    )

    client = LiteLLMClient()
    return await client.complete(request=request_with_json)


@activity.defn
async def complete_chat(request: CompletionRequest) -> CompletionResponse:
    """Complete a chat conversation.

    Uses the LiteLLM CompletionRequest/Response directly for full control.

    Example:
        result = await complete_chat(CompletionRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content='You are helpful'),
                Message(role=MessageRole.USER, content='Hello!'),
            ],
            temperature=0.5,
        ))
    """
    activity.logger.info(f'Completing chat with {len(request.messages)} messages')

    client = LiteLLMClient()
    return await client.complete(request=request)


@activity.defn
async def enhance_image_prompt(concept: str, style: str = 'photorealistic') -> ImagePromptOutput:
    """Enhance a concept into a detailed image generation prompt.

    Convenience wrapper for image prompt enhancement.

    Example:
        result = await enhance_image_prompt('sunset over mountains', 'cinematic')
        # result.enhanced_prompt = 'A breathtaking golden sunset...'
        # result.negative_prompt = 'blurry, watermark, text...'
        # result.aspect_ratio = '16:9'
    """
    activity.logger.info(f'Enhancing image prompt for: {concept[:50]}...')

    client = LiteLLMClient()

    system_prompt = """You are an expert at creating image generation prompts.
Given a concept and style, output a JSON object with:
- enhanced_prompt: A detailed, vivid prompt (50-150 words)
- negative_prompt: What to avoid in the image

Output ONLY valid JSON, no markdown."""

    prompt = f'Concept: {concept}\nStyle: {style}'

    response = await client.complete_text(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.7,
        json_mode=True,
    )

    # Parse the response
    if response.parsed and isinstance(response.parsed, dict):
        return ImagePromptOutput(
            enhanced_prompt=response.parsed.get('enhanced_prompt', concept),
            negative_prompt=response.parsed.get('negative_prompt', ''),
            model_used=response.model,
            fallback_used=response.fallback_used,
        )

    # Fallback if parsing failed
    return ImagePromptOutput(
        enhanced_prompt=concept,
        negative_prompt='',
        model_used=response.model,
        fallback_used=response.fallback_used,
    )
