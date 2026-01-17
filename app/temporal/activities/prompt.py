"""Prompt/LLM activities using existing PromptService.

These activities handle text generation tasks like:
- Enhancing image prompts
- Generating video scripts
- Generating UGC person prompts
- Generating UGC video reaction prompts
- Any structured text generation
"""

import json

from temporalio import activity

from app.core.services.prompt.schemas import PromptTemplates
from app.core.services.prompt.service import get_prompt_service
from app.temporal.schemas import (
    PromptEnhancementInput,
    PromptEnhancementOutput,
    ScriptGenerationInput,
    ScriptGenerationOutput,
    UGCPersonInput,
    UGCPersonOutput,
    UGCVideoReactionInput,
    UGCVideoReactionOutput,
)


@activity.defn
async def enhance_prompt(input: PromptEnhancementInput) -> PromptEnhancementOutput:
    """Enhance a simple concept into a detailed image generation prompt.

    Uses the existing PromptService with the IMAGE_PROMPT_ENHANCER template.
    """
    activity.logger.info(f'Enhancing prompt for concept: {input.concept[:50]}...')

    service = get_prompt_service()

    try:
        result = await service.generate_structured(
            template=PromptTemplates.IMAGE_PROMPT_ENHANCER,
            variables={
                'concept': input.concept,
                'style': input.style,
            },
        )

        return PromptEnhancementOutput(
            enhanced_prompt=result.get('enhanced_prompt', input.concept),
            negative_prompt=result.get('negative_prompt', ''),
            suggested_aspect_ratio=result.get('suggested_aspect_ratio', '1:1'),
            style_tags=result.get('style_tags', []),
        )
    finally:
        await service.close()


@activity.defn
async def generate_script(input: ScriptGenerationInput) -> ScriptGenerationOutput:
    """Generate a video script from a topic.

    Uses the existing PromptService with the VIDEO_SCRIPT_GENERATOR template.
    """
    activity.logger.info(f'Generating script for topic: {input.topic[:50]}...')

    service = get_prompt_service()

    try:
        result = await service.generate_structured(
            template=PromptTemplates.VIDEO_SCRIPT_GENERATOR,
            variables={
                'topic': input.topic,
                'duration_seconds': input.duration_seconds,
                'style': input.style,
                'mood': input.mood or input.style,
            },
        )

        # Extract scene descriptions from the structured response
        scenes = result.get('scenes', [])
        scene_descriptions = [scene.get('prompt', '') for scene in scenes]

        return ScriptGenerationOutput(
            title=result.get('title', f'Video about {input.topic}'),
            voiceover_script=result.get('voiceover_script', ''),
            scene_descriptions=scene_descriptions,
            music_suggestion=result.get('music_suggestion'),
        )
    finally:
        await service.close()


@activity.defn
async def generate_voiceover_script(
    topic: str,
    duration_seconds: int,
    tone: str = 'professional',
    audience: str = 'general',
) -> dict:
    """Generate a voiceover script with timing and emotion markers.

    Uses the VOICEOVER_SCRIPT_GENERATOR template.
    """
    activity.logger.info(f'Generating voiceover script for: {topic[:50]}...')

    service = get_prompt_service()

    try:
        result = await service.generate_structured(
            template=PromptTemplates.VOICEOVER_SCRIPT_GENERATOR,
            variables={
                'topic': topic,
                'duration_seconds': duration_seconds,
                'tone': tone,
                'audience': audience,
            },
        )

        return result
    finally:
        await service.close()


@activity.defn
async def generate_ugc_person(input: UGCPersonInput) -> UGCPersonOutput:
    """Generate a detailed JSON prompt for UGC-style person images.

    Creates hyper-detailed prompts that produce authentic-looking selfies
    and casual photos that look like real social media content.

    Uses the UGC_PERSON_GENERATOR template.
    """
    activity.logger.info(
        f'Generating UGC person prompt: {input.gender}, {input.age_range}, '
        f'{input.ethnicity}, {input.hair_color}, {input.emotion}'
    )

    service = get_prompt_service()

    try:
        result = await service.generate_structured(
            template=PromptTemplates.UGC_PERSON_GENERATOR,
            variables={
                'gender': input.gender,
                'age_range': input.age_range,
                'emotion': input.emotion,
                'style': input.style,
                'setting': input.background,  # Map background to setting for template
                'hair_color': input.hair_color,
                'ethnicity': input.ethnicity,
                'clothing': input.clothing,
                'context': input.context or 'casual social media content',
            },
        )

        # Convert the structured JSON to a flattened text prompt for image models
        text_prompt = _json_to_text_prompt(result)

        return UGCPersonOutput(
            json_prompt=result,
            text_prompt=text_prompt,
        )
    finally:
        await service.close()


def _json_to_text_prompt(json_prompt: dict) -> str:
    """Convert structured JSON prompt to a flattened text prompt.

    Image models work better with the raw JSON as the prompt,
    so we just stringify it with some formatting.
    """
    # For models like Nano Banana, the JSON structure itself works well as a prompt
    # We return a compact JSON string that can be used directly
    return json.dumps(json_prompt, separators=(',', ':'))


@activity.defn
async def generate_ugc_video_reaction(input: UGCVideoReactionInput) -> UGCVideoReactionOutput:
    """Generate an animation prompt to bring a static reaction image to life.

    The image is already generated with all details - this just describes
    the subtle movements to animate it (eyes, head, breathing, micro-expressions).

    Uses the UGC_VIDEO_REACTION_GENERATOR template.
    """
    activity.logger.info(f'Generating video reaction prompt: {input.emotion}, duration={input.duration}s')

    service = get_prompt_service()

    try:
        result = await service.generate_structured(
            template=PromptTemplates.UGC_VIDEO_REACTION_GENERATOR,
            variables={
                'emotion': input.emotion,
                'context': input.context or 'something surprising',
                'duration': input.duration,
            },
        )

        # Extract movements and final_prompt
        movements = result.get('movements', [])
        video_prompt = result.get('final_prompt', '')

        # Fallback if no final_prompt
        if not video_prompt and movements:
            video_prompt = _movements_to_prompt(movements, input.emotion)

        return UGCVideoReactionOutput(
            movements=movements,
            video_prompt=video_prompt,
        )
    finally:
        await service.close()


def _movements_to_prompt(movements: list[str], emotion: str) -> str:
    """Convert movement list to a video prompt if final_prompt is missing."""
    movement_text = '. '.join(movements)
    return f'{movement_text}. Slow, cinematic {emotion} reaction. No speech, no text, mouth stays closed.'
