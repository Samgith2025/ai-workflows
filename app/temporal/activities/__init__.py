"""Temporal activities - individual tasks that interact with external services.

Activities are the building blocks of workflows. Each activity:
- Performs a single, focused task
- Can be retried independently
- Has configurable timeouts
- Reports heartbeats for long-running operations

## Auto-Discovery

Activities are AUTOMATICALLY discovered by the worker via `discover_activities()`.
Just decorate a function with `@activity.defn` and it will be registered.
No need to add anything to this file.

## Infrastructure Used

- LiteLLM for LLM tasks (with fallback)
- Model Registry for AI model definitions
- ReplicateClient for image/video generation
- VoiceService (ElevenLabs/Cartesia) for TTS
- S3 for storage

## Convenience Imports

The imports below are for workflow convenience only - they don't affect registration.
"""

# FFmpeg schemas from service (enums)
from app.core.services.ffmpeg.schemas import TextFont, TextPosition

# FFmpeg activities
from app.temporal.activities.ffmpeg import (
    SlowDownVideoInput,
    SlowDownVideoOutput,
    TextOverlayActivityInput,
    TextOverlayActivityOutput,
    add_text_overlay,
    combine_video_with_audio,
    slow_down_video,
)

# Image generation
from app.temporal.activities.image import generate_image, generate_image_with_model

# LLM activities (preferred)
from app.temporal.activities.llm import (
    EnhanceTextInput,
    EnhanceTextOutput,
    ImagePromptOutput,
    complete_chat,
    enhance_image_prompt,
    enhance_text,
    generate_json,
)

# Legacy prompt activities
from app.temporal.activities.prompt import (
    enhance_prompt,
    generate_script,
    generate_ugc_person,
    generate_ugc_video_reaction,
    generate_voiceover_script,
)

# Media rewriting
from app.temporal.activities.rewrite import (
    RewriteImagesInput,
    RewriteImagesOutput,
    RewriteVideoInput,
    RewriteVideoOutput,
    rewrite_images,
    rewrite_video,
)

# Storage
from app.temporal.activities.storage import upload_bytes_to_storage, upload_to_storage

# Tool execution
from app.temporal.activities.tools import (
    ExecuteToolInput,
    ExecuteToolOutput,
    execute_tool,
    list_available_tools,
)

# Video generation
from app.temporal.activities.video import (
    combine_audio_video,
    generate_video,
    generate_video_with_model,
)

# Voice generation
from app.temporal.activities.voice import generate_voice, generate_voice_with_options

# UGC schemas
from app.temporal.schemas import (
    UGCPersonInput,
    UGCPersonOutput,
    UGCVideoReactionInput,
    UGCVideoReactionOutput,
)

__all__ = [
    # LLM activities (LiteLLM with fallback) - PREFERRED
    'enhance_text',
    'generate_json',
    'complete_chat',
    'enhance_image_prompt',
    'EnhanceTextInput',
    'EnhanceTextOutput',
    'ImagePromptOutput',
    # Legacy prompt activities (OpenAI direct)
    'enhance_prompt',
    'generate_script',
    'generate_voiceover_script',
    # UGC person generation
    'generate_ugc_person',
    'UGCPersonInput',
    'UGCPersonOutput',
    # UGC video reaction generation
    'generate_ugc_video_reaction',
    'UGCVideoReactionInput',
    'UGCVideoReactionOutput',
    # Image generation (uses model registry)
    'generate_image',
    'generate_image_with_model',
    # Video generation (uses model registry)
    'generate_video',
    'generate_video_with_model',
    'combine_audio_video',
    # FFmpeg video processing
    'slow_down_video',
    'add_text_overlay',
    'combine_video_with_audio',
    'SlowDownVideoInput',
    'SlowDownVideoOutput',
    'TextOverlayActivityInput',
    'TextOverlayActivityOutput',
    'TextPosition',
    'TextFont',
    # Voice generation
    'generate_voice',
    'generate_voice_with_options',
    # Storage
    'upload_to_storage',
    'upload_bytes_to_storage',
    # Tool execution
    'execute_tool',
    'list_available_tools',
    'ExecuteToolInput',
    'ExecuteToolOutput',
    # Media rewriting
    'rewrite_video',
    'rewrite_images',
    'RewriteVideoInput',
    'RewriteVideoOutput',
    'RewriteImagesInput',
    'RewriteImagesOutput',
]
