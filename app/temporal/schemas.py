"""Shared schemas for Temporal workflows and activities.

These are the data contracts between:
- Client -> Workflow (inputs)
- Workflow -> Activities (inputs)
- Activities -> Workflow (outputs)
- Workflow -> Client (outputs)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# Workflow Status
# =============================================================================


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class StepProgress:
    """Progress information for a workflow step."""

    step_id: str
    step_name: str
    status: WorkflowStatus
    progress_pct: int = 0
    message: str | None = None


# =============================================================================
# Base Workflow Input
# =============================================================================


# Device presets for metadata rewriting
RewriteDevice = Literal[
    # iPhone 17 series
    'iPhone 17 Pro Max',
    'iPhone 17 Pro',
    'iPhone 17 Plus',
    'iPhone 17',
    # iPhone 16 series
    'iPhone 16 Pro Max',
    'iPhone 16 Pro',
    'iPhone 16 Plus',
    'iPhone 16',
    # iPhone 15 series
    'iPhone 15 Pro Max',
    'iPhone 15 Pro',
    'iPhone 15 Plus',
    'iPhone 15',
    # iPhone 14 series
    'iPhone 14 Pro Max',
    'iPhone 14 Pro',
    'iPhone 14 Plus',
    'iPhone 14',
    # iPhone 13 series
    'iPhone 13 Pro Max',
    'iPhone 13 Pro',
    'iPhone 13',
    'iPhone 13 mini',
    # Other devices
    'Ray-Ban Meta Smart Glasses',
]


class WorkflowInput(BaseModel):
    """Base input model for all workflows.

    All workflow input models should inherit from this class.
    Provides automatic secret key validation when WORKFLOW_SECRET_ENABLED=True.

    Example:
        class MyWorkflowInput(WorkflowInput):
            topic: str = Field(..., description='Topic to generate')
            style: str = Field('default', description='Style option')

    When calling from frontend with auth enabled:
        await client.start_workflow(
            MyWorkflow.run,
            MyWorkflowInput(
                secret_key='your-secret-key',  # Required when auth enabled
                rewrite_enabled=True,  # Enable metadata rewriting
                rewrite_device='iPhone 15 Pro',  # Device to emulate
                topic='...',
                style='...',
            ),
            ...
        )
    """

    secret_key: str | None = Field(
        None,
        description='Secret key for authentication (required when WORKFLOW_SECRET_ENABLED=True)',
    )

    # Media rewriting options
    rewrite_enabled: bool = Field(
        False,
        description='Make your content appear as fresh, original uploads. Bypasses duplicate detection and AI content filters on social platforms.',
    )
    rewrite_device: RewriteDevice | None = Field(
        None,
        description='Make media appear as if created on this device. Adds authenticity and helps bypass platform detection. Random device if not specified.',
    )


# =============================================================================
# Image Generation Activity
# =============================================================================


@dataclass
class ImageGenerationInput:
    """Input for image generation activity."""

    prompt: str
    model: str = 'black-forest-labs/flux-schnell'
    aspect_ratio: str = '1:1'
    negative_prompt: str | None = None


@dataclass
class ImageGenerationOutput:
    """Output from image generation activity."""

    output_url: str
    model: str


# =============================================================================
# Voice Generation Activity
# =============================================================================


@dataclass
class VoiceGenerationInput:
    """Input for voice generation activity."""

    text: str
    voice_id: str = 'EXAVITQu4vr4xnSDxMaL'  # Default ElevenLabs voice
    model_id: str = 'eleven_multilingual_v2'
    stability: float = 0.5
    similarity_boost: float = 0.75


@dataclass
class VoiceGenerationOutput:
    """Output from voice generation activity."""

    output_url: str
    duration_seconds: float


# =============================================================================
# Video Generation Activity
# =============================================================================


@dataclass
class VideoGenerationInput:
    """Input for video generation activity."""

    prompt: str
    model: str = 'minimax/video-01'
    image_url: str | None = None
    aspect_ratio: str = '16:9'


@dataclass
class VideoGenerationOutput:
    """Output from video generation activity."""

    output_url: str
    duration_seconds: float


# =============================================================================
# Script Generation Activity (LLM)
# =============================================================================


@dataclass
class ScriptGenerationInput:
    """Input for script generation activity."""

    topic: str
    duration_seconds: int
    style: str
    mood: str | None = None


@dataclass
class ScriptGenerationOutput:
    """Output from script generation activity."""

    title: str
    voiceover_script: str
    scene_descriptions: list[str]
    music_suggestion: str | None = None


# =============================================================================
# Prompt Enhancement Activity (LLM)
# =============================================================================


@dataclass
class PromptEnhancementInput:
    """Input for prompt enhancement activity."""

    concept: str
    style: str


@dataclass
class PromptEnhancementOutput:
    """Output from prompt enhancement activity."""

    enhanced_prompt: str
    negative_prompt: str
    suggested_aspect_ratio: str
    style_tags: list[str]


# =============================================================================
# UGC Person Generation Activity (LLM)
# =============================================================================

# Age range presets
UGCAge = Literal[
    'teen',  # 16-19
    'early_20s',  # 20-24
    'mid_20s',  # 25-29
    'early_30s',  # 30-34
    'mid_30s',  # 35-39
    'early_40s',  # 40-44
    'mid_40s',  # 45-49
    'mature',  # 50+
]

# Hair color presets
UGCHairColor = Literal[
    'black',
    'brown',
    'blonde',
    'red',
    'auburn',
    'platinum',
    'gray',
    'white',
    'pink',
    'blue',
    'purple',
    'green',
    'ombre',
    'highlights',
]

# Ethnicity presets
UGCEthnicity = Literal[
    'caucasian',
    'black',
    'asian',
    'latino',
    'middle_eastern',
    'south_asian',
    'southeast_asian',
    'mixed',
]

# Background/setting presets
UGCBackground = Literal[
    'bedroom',
    'living_room',
    'bathroom',
    'kitchen',
    'office',
    'cafe',
    'restaurant',
    'gym',
    'park',
    'beach',
    'city_street',
    'rooftop',
    'car',
    'mall',
    'club',
    'studio',
]

# Clothing presets
UGCClothing = Literal[
    'casual',
    'streetwear',
    'formal',
    'business',
    'athletic',
    'swimwear',
    'sleepwear',
    'dress',
    'uniform',
    'vintage',
    'bohemian',
    'minimalist',
]

# Style presets (aesthetic)
UGCStyle = Literal[
    'coquette',
    'clean_girl',
    'dark_academia',
    'cottagecore',
    'streetwear',
    'minimalist',
    'y2k',
    'soft_girl',
    'grunge',
    'preppy',
]


class UGCPersonInput(BaseModel):
    """Input for UGC person prompt generation activity."""

    gender: str = Field('female', description='Gender: female, male')
    age_range: UGCAge | str = Field(
        'early_20s',
        description='Age: teen, early_20s, mid_20s, early_30s, mid_30s, early_40s, mid_40s, mature',
    )
    emotion: str = Field('neutral', description='Emotion/expression for the person')
    style: UGCStyle | str = Field(
        'coquette',
        description='Style: coquette, clean_girl, dark_academia, cottagecore, streetwear, minimalist, y2k, soft_girl, grunge, preppy',
    )
    background: UGCBackground | str = Field(
        'bedroom',
        description='Background: bedroom, living_room, bathroom, kitchen, office, cafe, restaurant, gym, park, beach, city_street, rooftop, car, mall, club, studio',
    )
    hair_color: UGCHairColor | str = Field(
        'brown',
        description='Hair: black, brown, blonde, red, auburn, platinum, gray, white, pink, blue, purple, green, ombre, highlights',
    )
    ethnicity: UGCEthnicity | str = Field(
        'caucasian',
        description='Ethnicity: caucasian, black, asian, latino, middle_eastern, south_asian, southeast_asian, mixed',
    )
    clothing: UGCClothing | str = Field(
        'casual',
        description='Clothing: casual, streetwear, formal, business, athletic, swimwear, sleepwear, dress, uniform, vintage, bohemian, minimalist',
    )
    context: str | None = Field(None, description='Optional user prompt or context for the scene')


class UGCPersonOutput(BaseModel):
    """Output from UGC person prompt generation activity."""

    json_prompt: dict[str, Any] = Field(..., description='The full structured JSON prompt')
    text_prompt: str = Field(..., description='Flattened text version for image models')


# =============================================================================
# UGC Video Reaction Generation Activity (LLM)
# =============================================================================


class UGCVideoReactionInput(BaseModel):
    """Input for UGC video reaction prompt generation activity.

    Simplified - the image already has all the details (person, setting, style).
    We only need to know what emotion to animate and for how long.
    """

    emotion: str = Field(..., description='Emotion/expression to animate')
    context: str | None = Field(None, description='Optional user prompt or context for the reaction')
    duration: int = Field(5, ge=5, le=10, description='Video duration in seconds')


class UGCVideoReactionOutput(BaseModel):
    """Output from UGC video reaction prompt generation activity."""

    movements: list[str] = Field(..., description='List of specific movements')
    video_prompt: str = Field(..., description='The final video generation prompt')


# =============================================================================
# Storage Activity
# =============================================================================


@dataclass
class StorageUploadInput:
    """Input for storage upload activity."""

    url: str
    content_type: str = 'auto'
    folder: str = 'generations'


@dataclass
class StorageUploadOutput:
    """Output from storage upload activity."""

    url: str
    key: str
