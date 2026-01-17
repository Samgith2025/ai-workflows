"""Ruby - AI Influencer for Short-form Videos.

Creates attention-grabbing short-form content with an AI-generated
"influencer" character reacting to a topic. Think viral TikTok/Reels style.

Flow: Generate UGC person prompt → Generate face → Animate with video model → Slow motion → Text overlay
"""

from typing import Any, Literal

from pydantic import BaseModel, Field
from temporalio import workflow

from app.temporal.schemas import (
    UGCAge,
    UGCBackground,
    UGCClothing,
    UGCEthnicity,
    UGCHairColor,
    UGCStyle,
    WorkflowInput,
    WorkflowStatus,
)
from app.temporal.workflows.base import (
    SLOW_RETRY,
    WorkflowContext,
    maybe_rewrite_image,
    maybe_rewrite_video,
    run_activity,
    upload_output,
)

# Activity imports - use pass_through to avoid sandbox restrictions on transitive deps
with workflow.unsafe.imports_passed_through():
    from app.core.ai_models.common import AspectRatio
    from app.core.services.ffmpeg.schemas import TextFont, TextPosition
    from app.temporal.activities import (
        UGCPersonInput,
        UGCVideoReactionInput,
        generate_image_with_model,
        generate_ugc_person,
        generate_ugc_video_reaction,
    )
    from app.temporal.activities.ffmpeg import (
        SlowDownVideoInput,
        TextOverlayActivityInput,
        add_text_overlay,
        slow_down_video,
    )
    from app.temporal.activities.video import generate_video_with_model


# Supported emotions for reaction videos
RubyEmotion = Literal[
    'shocked',
    'scared',
    'surprised',
    'worried',
    'crying',
    'excited',
    'confused',
    'disgusted',
    'amazed',
]


class RubyInput(WorkflowInput):
    """Input for Ruby generation."""

    # Core content
    additional_prompt: str | None = Field(
        None,
        description='Optional context or instructions for the AI generation. Guides both image and video creation.',
    )
    emotion: RubyEmotion | str = Field(
        'shocked',
        description='Emotion: shocked, scared, surprised, worried, excited, confused, disgusted, amazed',
    )
    text_overlay: str | None = Field(None, description='Optional text to display on video')

    # Person appearance
    gender: str = Field('female', description='Gender: female, male')
    age_range: UGCAge | str = Field(
        'early_20s',
        description='Age: teen, early_20s, mid_20s, early_30s, mid_30s, early_40s, mid_40s, mature',
    )
    ethnicity: UGCEthnicity | str = Field(
        'caucasian',
        description='Ethnicity: caucasian, black, asian, latino, middle_eastern, south_asian, southeast_asian, mixed',
    )
    hair_color: UGCHairColor | str = Field(
        'brown',
        description='Hair: black, brown, blonde, red, auburn, platinum, gray, pink, blue, purple, ombre',
    )

    # Style and setting
    style: UGCStyle | str = Field(
        'coquette',
        description='Style: coquette, clean_girl, dark_academia, cottagecore, streetwear, minimalist, y2k, soft_girl, grunge, preppy',
    )
    background: UGCBackground | str = Field(
        'bedroom',
        description='Background: bedroom, living_room, bathroom, kitchen, office, cafe, gym, park, beach, city_street, rooftop, car',
    )
    clothing: UGCClothing | str = Field(
        'casual',
        description='Clothing: casual, streetwear, formal, business, athletic, swimwear, sleepwear, dress, uniform, vintage, bohemian',
    )

    # Video settings
    aspect_ratio: str = Field('9:16', description='Aspect ratio: 9:16, 16:9, 1:1')
    video_duration: int = Field(5, ge=5, le=10, description='Video duration in seconds')
    slowed_video: bool = Field(True, description='Apply slow motion effect to video')

    # AI models (switch these to use different models from the registry)
    image_model: str = Field('nano-banana', description='Image model ID from registry')
    video_model: str = Field('kling-v2.6', description='Video model ID from registry')

    # Model-specific overrides (optional - merged with defaults)
    image_model_params: dict[str, Any] = Field(
        default_factory=dict,
        description='Override image model params (e.g., {"speed_mode": "Extra Juiced 🚀"})',
    )
    video_model_params: dict[str, Any] = Field(
        default_factory=dict,
        description='Override video model params (e.g., {"camera_fixed": False})',
    )


class RubyOutput(BaseModel):
    """Output from Ruby generation."""

    face_image_url: str = Field(..., description='URL of generated face image')
    raw_video_url: str = Field(..., description='URL of raw video before effects')
    final_video_url: str = Field(..., description='URL of final video with all effects')
    enhanced_image_prompt: str = Field(..., description='The enhanced prompt used for face generation')
    enhanced_video_prompt: str = Field(..., description='The enhanced prompt used for video generation')
    image_model: str = Field(..., description='Image model used')
    video_model: str = Field(..., description='Video model used')


@workflow.defn
class RubyWorkflow:
    """Creates Ruby-style AI influencer reaction videos.

    A reaction video where an AI person displays an emotion (shocked, scared, etc.)
    Perfect for viral content.
    """

    def __init__(self) -> None:
        self._ctx = WorkflowContext()

    @workflow.query
    def get_status(self) -> WorkflowStatus:
        return self._ctx.status

    @workflow.query
    def get_current_step(self):
        return self._ctx.current_step

    @workflow.run
    async def run(self, input: RubyInput) -> RubyOutput:
        self._ctx.start(input)

        aspect_ratio = AspectRatio(input.aspect_ratio)

        # Step 1: Generate UGC person prompt (image prompt first, then video prompt)
        async with self._ctx.step('prompts', 'Generate Prompts', 0):
            # First generate the UGC person prompt for the image
            ugc_result = await run_activity(
                generate_ugc_person,
                UGCPersonInput(
                    gender=input.gender,
                    age_range=input.age_range,
                    emotion=input.emotion,
                    style=input.style,
                    background=input.background,
                    hair_color=input.hair_color,
                    ethnicity=input.ethnicity,
                    clothing=input.clothing,
                    context=input.additional_prompt,
                ),
                timeout_minutes=2.0,
            )
            enhanced_image_prompt = ugc_result.text_prompt

            # Generate animation prompt - just the movements to bring the image to life
            video_result = await run_activity(
                generate_ugc_video_reaction,
                UGCVideoReactionInput(
                    emotion=input.emotion,
                    context=input.additional_prompt,
                    duration=input.video_duration,
                ),
                timeout_minutes=2.0,
            )
            enhanced_video_prompt = video_result.video_prompt

        # Step 2: Generate face image using UGC person prompt
        async with self._ctx.step('face', 'Generate Face', 10):
            image_params = {
                'prompt': enhanced_image_prompt,
                'aspect_ratio': aspect_ratio.value,
                **input.image_model_params,  # User overrides (model-specific)
            }
            face_result = await run_activity(
                generate_image_with_model,
                input.image_model,
                image_params,
                timeout_minutes=3.0,
                retry_policy=SLOW_RETRY,
            )
            face_image_url = face_result.output_url

        # Step 3: Generate video
        async with self._ctx.step('video', 'Generate Video', 30):
            video_params = {
                'prompt': enhanced_video_prompt,
                'image': face_image_url,
                'duration': input.video_duration,
                'aspect_ratio': aspect_ratio.value,
                'generate_audio': False,
                **input.video_model_params,  # User overrides (model-specific)
            }
            video_result = await run_activity(
                generate_video_with_model,
                input.video_model,
                video_params,
                timeout_minutes=10.0,
                retry_policy=SLOW_RETRY,
            )
            raw_video_url = video_result.output_url

        # Step 4: Apply slow motion (optional)
        if input.slowed_video:
            slowmo_folder = 'ruby/temp' if input.text_overlay else 'ruby/videos'
            async with self._ctx.step('slowmo', 'Apply Slow Motion', 60):
                slowed_result = await run_activity(
                    slow_down_video,
                    SlowDownVideoInput(
                        video_url=raw_video_url,
                        speed_factor=0.7,
                        preserve_audio=False,
                        output_folder=slowmo_folder,
                    ),
                    timeout_minutes=5.0,
                )
                final_video_url = slowed_result.output_url
        else:
            final_video_url = raw_video_url

        # Step 5: Add text overlay (optional)
        if input.text_overlay:
            async with self._ctx.step('text', 'Add Text', 80):
                text_result = await run_activity(
                    add_text_overlay,
                    TextOverlayActivityInput(
                        video_url=final_video_url,
                        text=input.text_overlay,
                        position=TextPosition.CENTER,
                        font=TextFont.IMPACT,
                        font_color='white',
                        font_scale_factor=28.0,
                        background_color=None,
                        padding=0,
                        border_width=4,
                        border_color='black',
                        max_chars_per_line=24,
                        output_folder='ruby/videos',
                    ),
                    timeout_minutes=5.0,
                )
                final_video_url = text_result.output_url

        # Step 6: Rewrite media (if enabled)
        if input.rewrite_enabled:
            async with self._ctx.step('rewrite', 'Rewrite Media', 85):
                face_image_url = await maybe_rewrite_image(face_image_url, input)
                final_video_url = await maybe_rewrite_video(final_video_url, input)

        # Step 7: Upload face image to storage
        async with self._ctx.step('upload', 'Upload', 90):
            face_url = await upload_output(face_image_url, 'ruby/faces')

        self._ctx.complete()

        return RubyOutput(
            face_image_url=face_url,
            raw_video_url=raw_video_url,
            final_video_url=final_video_url,
            enhanced_image_prompt=enhanced_image_prompt,
            enhanced_video_prompt=enhanced_video_prompt,
            image_model=input.image_model,
            video_model=input.video_model,
        )
