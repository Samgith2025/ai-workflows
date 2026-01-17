from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.core.services.generation.schemas import GenerationRequest


class PromptProvider(str, Enum):
    """Supported prompt generation providers."""

    OPENAI = 'openai'
    ANTHROPIC = 'anthropic'
    REPLICATE = 'replicate'


class PromptTemplate(BaseModel):
    """Template for structured prompt generation.
    Defines the expected output structure and instructions.
    """

    name: str = Field(description='Template name for identification')
    description: str | None = Field(None, description='Description of what this template generates')

    # System and user prompts
    system_prompt: str = Field(description='System prompt defining the assistant behavior')
    user_prompt_template: str = Field(description='User prompt template with {placeholders}')

    # Output schema
    output_schema: dict[str, Any] | None = Field(
        None,
        description='JSON schema for structured output (for function calling/tool use)',
    )

    # Examples for few-shot learning
    examples: list[dict[str, Any]] | None = Field(
        None,
        description='Example input/output pairs for few-shot prompting',
    )

    def render(self, **kwargs) -> str:
        """Render the user prompt with provided variables."""
        return self.user_prompt_template.format(**kwargs)


class PromptGenerationRequest(GenerationRequest):
    """Request for prompt generation."""

    template: PromptTemplate = Field(description='Prompt template to use')
    variables: dict[str, Any] = Field(default_factory=dict, description='Variables to fill in the template')

    # LLM settings
    provider: PromptProvider = Field(PromptProvider.OPENAI, description='LLM provider to use')
    model: str = Field('gpt-4o-mini', description='Model to use for generation')
    temperature: float = Field(0.7, ge=0.0, le=2.0, description='Sampling temperature')
    max_tokens: int = Field(2048, ge=1, le=16384, description='Maximum tokens in response')

    # Output format
    json_mode: bool = Field(True, description='Request JSON output format')


class PromptResult(BaseModel):
    """Result of a prompt generation."""

    content: str = Field(description='Raw text content from the LLM')
    parsed: dict[str, Any] | None = Field(None, description='Parsed JSON if json_mode was enabled')

    # Usage
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    # Metadata
    model: str = Field(description='Model used')
    provider: PromptProvider = Field(description='Provider used')


# Pre-built templates for common use cases
class PromptTemplates:
    """Pre-built prompt templates for common generation tasks."""

    IMAGE_PROMPT_ENHANCER = PromptTemplate(
        name='image_prompt_enhancer',
        description='Enhance a simple image prompt into a detailed, high-quality prompt',
        system_prompt="""You are an expert at crafting detailed, vivid prompts for AI image generation.
Given a simple concept or idea, you create rich, detailed prompts that will produce stunning images.
Focus on: composition, lighting, style, mood, colors, and technical quality descriptors.
Always output valid JSON.""",
        user_prompt_template="""Enhance this image prompt into a detailed, high-quality prompt for AI image generation:

Concept: {concept}
Style preference: {style}

Output a JSON object with:
- enhanced_prompt: The detailed, enhanced prompt
- negative_prompt: Things to avoid in the image
- suggested_aspect_ratio: Best aspect ratio for this image (e.g., "16:9", "1:1", "9:16")
- style_tags: Array of style keywords""",
        output_schema={
            'type': 'object',
            'properties': {
                'enhanced_prompt': {'type': 'string'},
                'negative_prompt': {'type': 'string'},
                'suggested_aspect_ratio': {'type': 'string'},
                'style_tags': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['enhanced_prompt', 'negative_prompt', 'suggested_aspect_ratio', 'style_tags'],
        },
    )

    VIDEO_SCRIPT_GENERATOR = PromptTemplate(
        name='video_script_generator',
        description='Generate a video script with scenes and prompts',
        system_prompt="""You are an expert video scriptwriter and director.
You create detailed scene-by-scene scripts for AI video generation.
Each scene should have a clear visual description, camera movement, and timing.
Always output valid JSON.""",
        user_prompt_template="""Create a video script for the following concept:

Topic: {topic}
Duration: {duration_seconds} seconds
Style: {style}
Mood: {mood}

Output a JSON object with:
- title: Video title
- scenes: Array of scene objects, each with:
  - scene_number: Scene index (1-based)
  - duration_seconds: Duration of this scene
  - prompt: Detailed visual prompt for AI video generation
  - camera_movement: Camera movement description
  - transition: Transition to next scene (or "none" for last scene)
- music_suggestion: Suggested background music style
- voiceover_script: Optional narration script (or null if no voiceover)""",
        output_schema={
            'type': 'object',
            'properties': {
                'title': {'type': 'string'},
                'scenes': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'scene_number': {'type': 'integer'},
                            'duration_seconds': {'type': 'number'},
                            'prompt': {'type': 'string'},
                            'camera_movement': {'type': 'string'},
                            'transition': {'type': 'string'},
                        },
                    },
                },
                'music_suggestion': {'type': 'string'},
                'voiceover_script': {'type': ['string', 'null']},
            },
            'required': ['title', 'scenes', 'music_suggestion'],
        },
    )

    VOICEOVER_SCRIPT_GENERATOR = PromptTemplate(
        name='voiceover_script_generator',
        description='Generate a voiceover script with timing and emotion markers',
        system_prompt="""You are an expert voiceover scriptwriter.
You create natural, engaging scripts for text-to-speech generation.
Include emotion markers and pacing notes for optimal voice synthesis.
Always output valid JSON.""",
        user_prompt_template="""Create a voiceover script for:

Topic: {topic}
Target duration: {duration_seconds} seconds
Tone: {tone}
Target audience: {audience}

Output a JSON object with:
- script: The full voiceover script
- segments: Array of script segments, each with:
  - text: The text for this segment
  - emotion: Emotion/tone for this segment (e.g., "neutral", "excited", "serious")
  - pause_after_seconds: Pause after this segment (0 for no pause)
- estimated_duration_seconds: Estimated total duration
- voice_recommendations: Suggested voice characteristics""",
        output_schema={
            'type': 'object',
            'properties': {
                'script': {'type': 'string'},
                'segments': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'text': {'type': 'string'},
                            'emotion': {'type': 'string'},
                            'pause_after_seconds': {'type': 'number'},
                        },
                    },
                },
                'estimated_duration_seconds': {'type': 'number'},
                'voice_recommendations': {'type': 'string'},
            },
            'required': ['script', 'segments', 'estimated_duration_seconds'],
        },
    )

    UGC_PERSON_GENERATOR = PromptTemplate(
        name='ugc_person_generator',
        description='Generate a detailed JSON prompt for UGC-style person images',
        system_prompt="""You are an expert at creating hyper-detailed JSON prompts for AI image generation of realistic UGC (User Generated Content) style photos.

Your prompts generate authentic-looking selfies and casual photos that look like real social media content - NOT professional photography.

Key principles:
1. REALISM: Natural skin with visible pores, imperfections, micro-shadows. NO airbrushing or beauty filters.
2. CASUAL AUTHENTICITY: Mirror selfies, casual poses, natural lighting, slightly imperfect framing.
3. GEN-Z AESTHETIC: Current fashion trends, popular phone cases, trendy room decor, authentic vibes.
4. TECHNICAL ACCURACY: iPhone camera artifacts, natural grain, realistic depth of field.

Always output a valid JSON object with the exact structure requested.""",
        user_prompt_template="""Generate a detailed JSON prompt for a UGC-style person image.

Parameters:
- Gender: {gender}
- Age range: {age_range}
- Emotion/Expression: {emotion}
- Style aesthetic: {style}
- Setting/Environment: {setting}
- Additional context: {context}

Output a JSON object with this EXACT structure:
{{
  "subject": {{
    "type": "young_adult_woman" or "young_adult_man",
    "ethnicity": "specific ethnicity",
    "age": "specific age description",
    "eye_color": "specific color",
    "skin_texture": "natural_with_visible_pores_and_imperfections_no_blur_or_smoothing",
    "expression": "detailed expression matching the emotion",
    "makeup": {{ ... }} or null for men,
    "hair": {{
      "color": "specific",
      "length": "specific",
      "texture": "specific",
      "style": "specific trendy style"
    }},
    "pose": {{
      "type": "mirror_selfie" or other casual pose,
      "camera_angle": "slight_downward_diagonal",
      "head_angle": "natural tilt",
      "body_position": "casual authentic position"
    }}
  }},
  "apparel": {{
    "top": {{ detailed clothing description }},
    "bottoms": {{ detailed description }},
    "accessories": [ ... ]
  }},
  "phone": {{
    "model": "iPhone_15_Pro_Max",
    "case": {{ trendy case description }}
  }},
  "environment": {{
    "setting": "detailed setting description",
    "lighting": "natural indoor/outdoor description",
    "background_details": [ ... ],
    "vibe": "aesthetic vibe description"
  }},
  "image_rendering": {{
    "style": "natural_phone_snapshot",
    "device": "iPhone_15_Pro_Max",
    "no_beautify": true,
    "skin_detail": {{
      "pores_visible": true,
      "imperfections_visible": true
    }},
    "camera_artifacts": {{
      "grain": "light_natural",
      "noise": "soft_iso_noise"
    }},
    "ratio": "3:4"
  }}
}}

Make it creative, trendy, and authentically Gen-Z. The person should look like a real influencer/creator.""",
        output_schema={
            'type': 'object',
            'properties': {
                'subject': {'type': 'object'},
                'apparel': {'type': 'object'},
                'phone': {'type': 'object'},
                'environment': {'type': 'object'},
                'image_rendering': {'type': 'object'},
            },
            'required': ['subject', 'apparel', 'environment', 'image_rendering'],
        },
    )

    UGC_VIDEO_REACTION_GENERATOR = PromptTemplate(
        name='ugc_video_reaction_generator',
        description='Generate an animation prompt to bring a static reaction image to life',
        system_prompt="""You are an expert at writing prompts that animate static images into realistic UGC reaction videos.

The image is ALREADY generated with all the details (person, expression, setting, clothing, phone). Your job is to describe HOW to animate it - the movements that bring the static selfie to life.

Key principles:
1. AUTHENTIC UGC FEEL: This is a real person filming themselves reacting. Natural, not posed.
2. FULL BODY LANGUAGE: Face, hands, shoulders, phone grip - everything moves together.
3. NO SPEECH: Mouth stays closed. No talking, no words forming.
4. CINEMATIC BUT REAL: Slow enough to feel emotional, fast enough to feel genuine.
5. FLOW: Movements chain naturally - one triggers another.

Movement vocabulary:

FACE:
- Eyes: widening, narrowing, softening, glistening with emotion, slow blink, looking away then back, eye roll, squinting
- Eyebrows: raising in shock, furrowing in concern, one eyebrow up, micro-twitches
- Mouth (CLOSED): lips pressing together, slight smile forming, corners trembling, pursing lips, biting lip
- Nose: nostril flare, slight scrunch

HEAD & NECK:
- Head: tilt (curious), pull back (shocked), lean forward (interested), slow turn, small shake, subtle nod
- Neck: tension visible, swallowing motion

HANDS & PHONE:
- Phone grip: tightening, loosening, slight shake/tremor, adjusting angle
- Free hand: moving to face, covering mouth (shock), touching hair, nervous fidget, gesturing subtly
- Fingers: drumming, curling, spreading

BODY:
- Shoulders: rising with tension, dropping with relief, slight shrug, one shoulder up
- Chest: deep breath in, exhale, held breath, quickened breathing
- Posture: leaning back, leaning in, straightening up, slight slump

SUBTLE DETAILS:
- Hair: slight movement from head motion, tucking behind ear
- Jewelry: earrings swaying, necklace catching light
- Clothing: slight shift from breathing/movement

Mix these creatively! A shocked reaction might be: grip tightens on phone → eyes widen → head pulls back → free hand rises toward face → sharp inhale.""",
        user_prompt_template="""Create an animation prompt for a {emotion} reaction video.

Context: {context}
Duration: {duration} seconds

Write a JSON with:
1. "movements" - array of 5-7 specific movements that flow naturally (mix face, hands, body)
2. "final_prompt" - a single 50-70 word paragraph describing the full animation (cinematic, no speech/text)

Example for "shocked":
{{
  "movements": [
    "Grip tightens on phone, knuckles tensing",
    "Eyes widen slowly, catching the light",
    "Head pulls back slightly in disbelief",
    "Free hand rises toward parted lips",
    "Sharp inhale - chest rises visibly",
    "Eyebrows lift, forehead creases",
    "Slight tremor in the phone hand"
  ],
  "final_prompt": "Her grip tightens on the phone as her eyes widen with disbelief. Head pulling back, her free hand rises instinctively toward her face. A sharp inhale lifts her chest as eyebrows climb higher. The phone trembles slightly in her grasp. Pure shock ripples through micro-expressions. Cinematic, slow, authentic. No speech, no text."
}}

Example for "excited":
{{
  "movements": [
    "Eyes light up, sparkling with joy",
    "Shoulders rise with contained excitement",
    "Quick, bright blink",
    "Head tilts with a growing smile (lips closed)",
    "Free hand comes up in a small celebratory gesture",
    "Slight bounce in posture",
    "Phone adjusts as energy builds"
  ],
  "final_prompt": "Her eyes sparkle as excitement floods her features. Shoulders rise, barely containing the joy as a bright-eyed blink leads into a head tilt. A closed-lip smile spreads while her free hand lifts in subtle celebration. Her whole body seems to bounce with energy, phone shifting with her movement. Radiant, authentic excitement. No speech, no text."
}}

Now create for {emotion}:""",
        output_schema={
            'type': 'object',
            'properties': {
                'movements': {'type': 'array', 'items': {'type': 'string'}},
                'final_prompt': {'type': 'string'},
            },
            'required': ['movements', 'final_prompt'],
        },
    )
