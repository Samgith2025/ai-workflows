"""Pinterest Slideshow Generator.

Takes user text input, generates diverse Pinterest search queries using Gemini,
scrapes Pinterest for aesthetic images, and returns the best 10 images.

Flow: Parse text → Generate diverse queries → Scrape Pinterest → Score & select best images
"""

import asyncio
import hashlib

from pydantic import BaseModel, Field
from temporalio import workflow

# Activity imports - use pass_through to avoid sandbox restrictions
with workflow.unsafe.imports_passed_through():
    from app.core.ai_models.common import AspectRatio
    from app.core.providers.litellm.schemas import CompletionRequest, Message, MessageRole
    from app.temporal.activities import ExecuteToolInput, execute_tool, generate_json, upload_to_storage

from temporalio.exceptions import ApplicationError

from app.temporal.schemas import StorageUploadInput, WorkflowInput, WorkflowStatus
from app.temporal.workflows.base import FAST_RETRY, WorkflowContext, maybe_rewrite_images, run_activity

# Internal constants - not exposed to users
_NUM_QUERIES = 5
_PAGES_PER_QUERY = 2
_NUM_IMAGES_TO_RETURN = 25

# Keywords that suggest text-heavy, watermarked, or collage images
_UNWANTED_IMAGE_KEYWORDS = frozenset(
    {
        # Text-heavy content
        'infographic',
        'template',
        'printable',
        'checklist',
        'worksheet',
        'quote',
        'quotes',
        'tips',
        'tutorial',
        'how to',
        'howto',
        'step by step',
        'guide',
        'cheat sheet',
        'cheatsheet',
        'recipe',
        'ingredients',
        'instructions',
        'diy',
        'download',
        'free',
        'pdf',
        'ebook',
        'chart',
        'diagram',
        'graph',
        'statistics',
        # Watermarks and stock
        'logo',
        'watermark',
        'stock',
        'shutterstock',
        'getty',
        'adobe stock',
        'pin this',
        'save this',
        'click',
        'link in bio',
        # Grid/collage images
        'collage',
        'grid',
        'mood board',
        'moodboard',
        'collection',
        'compilation',
        'roundup',
        'round up',
        'best of',
        '3x3',
        '2x2',
        '4x4',
        'photo dump',
        'photodump',
    }
)


class PinterestImage(BaseModel):
    """A single Pinterest image result."""

    id: str = Field(..., description='Pin ID')
    title: str | None = Field(None, description='Pin title')
    description: str | None = Field(None, description='Pin description')
    image_url: str = Field(..., description='Image URL')
    aspect_ratio: str = Field(..., description='Aspect ratio (e.g., 9:16)')
    image_width: int | None = Field(None, description='Image width in pixels')
    image_height: int | None = Field(None, description='Image height in pixels')


class SlideshowsPinterestInput(WorkflowInput):
    """Input for Pinterest slideshow generation."""

    prompt: str = Field(..., description='User text describing what kind of images they want')


class SlideshowsPinterestOutput(BaseModel):
    """Output from Pinterest slideshow generation."""

    images: list[PinterestImage] = Field(default_factory=list, description='List of Pinterest images')
    queries_used: list[str] = Field(default_factory=list, description='Search queries that were used')
    total_scraped: int = Field(0, description='Total pins scraped before filtering')


@workflow.defn
class SlideshowsPinterestWorkflow:
    """Generates a slideshow from Pinterest images based on user text.

    Uses Gemini to understand the user's text and generate relevant
    Pinterest search queries, then scrapes and returns aesthetic images.
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
    async def run(self, input: SlideshowsPinterestInput) -> SlideshowsPinterestOutput:
        self._ctx.start(input)

        # Step 1: Generate diverse Pinterest search queries from user text
        async with self._ctx.step('generate_queries', 'Generate Search Queries', 10):
            queries = await self._generate_queries(input.prompt)

        # Step 2: Scrape Pinterest with all queries in parallel
        async with self._ctx.step('scrape', 'Collecting Images', 50):
            all_pins = await self._scrape_pinterest(queries)

        # Step 3: Score and select best images
        async with self._ctx.step('select', 'Select Best Images', 70):
            images = self._select_best_images(all_pins)

        # Step 4: Rewrite images (if enabled)
        if input.rewrite_enabled:
            async with self._ctx.step('rewrite', 'Rewrite Images', 80):
                image_urls = [img.image_url for img in images]
                rewritten_urls = await maybe_rewrite_images(image_urls, input)
                # Update images with rewritten URLs
                images = [
                    PinterestImage(
                        id=img.id,
                        title=img.title,
                        description=img.description,
                        image_url=rewritten_urls[i],
                        aspect_ratio=img.aspect_ratio,
                        image_width=img.image_width,
                        image_height=img.image_height,
                    )
                    for i, img in enumerate(images)
                ]

        # Step 5: Upload images to R2 storage
        async with self._ctx.step('upload', 'Save Images', 90):
            images = await self._upload_images(images)

        self._ctx.complete()

        return SlideshowsPinterestOutput(
            images=images,
            queries_used=queries,
            total_scraped=len(all_pins),
        )

    async def _generate_queries(self, prompt: str) -> list[str]:
        """Use Gemini to generate diverse Pinterest search queries from user text.

        Balances diversity with Pinterest-effectiveness by:
        1. Understanding what makes queries work on Pinterest (aesthetic terms, moods, styles)
        2. Generating queries that approach the topic from different angles
        3. Ensuring each query will return visually distinct results
        """
        system_prompt = """You generate Pinterest search queries that find beautiful, aesthetic images.

Pinterest is a visual discovery platform. Effective queries combine:
- Subject matter (what's in the image)
- Visual style (photography, illustration, minimalist, editorial, etc.)
- Mood/atmosphere (cozy, dramatic, serene, moody, vibrant, etc.)
- Aesthetic category (cottagecore, dark academia, coastal grandmother, etc.)

Your goal: Generate queries that are BOTH effective on Pinterest AND diverse from each other.

Each query should find a completely different SET of images - vary the style, mood, color palette, or interpretation.

Output ONLY valid JSON."""

        user_prompt = f"""User wants images about: {prompt}

Generate {_NUM_QUERIES} Pinterest search queries. Requirements:

1. Each query must find DIFFERENT images (vary style, mood, aesthetic, or angle)
2. Use 3-5 words per query - specific enough to find good results
3. Include at least one style/mood/aesthetic term in each query
4. Think about different visual interpretations:
   - Different color palettes (warm vs cool, bright vs muted)
   - Different styles (photography vs illustration, minimal vs maximal)
   - Different moods (cozy vs dramatic, peaceful vs energetic)
   - Different contexts or settings

JSON format:
{{"queries": ["query1", "query2", "query3", "query4", "query5"]}}"""

        request = CompletionRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content=system_prompt),
                Message(role=MessageRole.USER, content=user_prompt),
            ],
            model='gemini/gemini-2.0-flash-lite',
            temperature=0.9,  # High creativity, still coherent
            max_tokens=512,
            json_mode=True,
        )

        response = await run_activity(
            generate_json,
            request,
            timeout_minutes=1.0,
            retry_policy=FAST_RETRY,
        )

        # Parse queries from response
        if response.parsed and isinstance(response.parsed, dict):
            queries = response.parsed.get('queries', [])
            if queries:
                queries = queries[:_NUM_QUERIES]
                workflow.logger.info(f'Generated Pinterest queries for "{prompt}":')
                for i, query in enumerate(queries, 1):
                    workflow.logger.info(f'  Query {i}: {query}')
                return queries

        # Fallback: use the prompt directly
        workflow.logger.warning(f'Failed to generate queries, using prompt directly: "{prompt}"')
        return [prompt]

    async def _scrape_pinterest(self, queries: list[str]) -> list[dict]:
        """Scrape Pinterest for all queries in parallel."""
        tasks = []
        for query in queries:
            task = run_activity(
                execute_tool,
                ExecuteToolInput(
                    tool_id='gptmarket-pinterest-scraper',
                    params={
                        'search_query': query,
                        'search_type': 'social_media',
                        'pages': _PAGES_PER_QUERY,
                    },
                ),
                timeout_minutes=2.0,
                retry_policy=FAST_RETRY,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect all pins from successful results and track errors
        all_pins: list[dict] = []
        errors: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                errors.append(f'Query "{queries[i]}": {result}')
                workflow.logger.warning(f'Query "{queries[i]}" failed: {result}')
                continue
            if not result.success:
                errors.append(f'Query "{queries[i]}": {result.error}')
                workflow.logger.warning(f'Query "{queries[i]}" failed: {result.error}')
                continue
            if result.output:
                pins = result.output.get('pins', [])
                workflow.logger.info(f'Query "{queries[i]}" returned {len(pins)} pins')
                all_pins.extend(pins)

        # If all queries failed, raise a non-retryable error
        if not all_pins and errors:
            raise ApplicationError(
                f'All Pinterest queries failed: {"; ".join(errors)}',
                non_retryable=True,
            )

        workflow.logger.info(f'Total pins scraped: {len(all_pins)}')
        return all_pins

    def _select_best_images(self, pins: list[dict]) -> list[PinterestImage]:
        """Score and select the best images from scraped pins.

        Scoring criteria:
        - Resolution: Higher resolution = better quality
        - Metadata: Has title/description = more curated content
        - Aspect ratio: Prefer portrait (9:16, 2:3, 3:4) for slideshows
        - Diversity: Penalize images too similar to already selected ones
        """
        # First, deduplicate and score all images
        seen_urls: set[str] = set()
        scored_pins: list[tuple[float, dict]] = []

        for pin in pins:
            image_url = pin.get('image_url', '')
            if not image_url or image_url in seen_urls:
                continue
            seen_urls.add(image_url)

            score = self._score_pin(pin)
            scored_pins.append((score, pin))

        # Sort by score (highest first)
        scored_pins.sort(key=lambda x: x[0], reverse=True)

        # Log scoring stats
        workflow.logger.info(f'Unique images after dedup: {len(scored_pins)}')
        if scored_pins:
            top_score = scored_pins[0][0]
            bottom_score = scored_pins[-1][0]
            penalized_count = sum(1 for score, _ in scored_pins if score < 0)
            workflow.logger.info(f'Score range: {bottom_score:.1f} to {top_score:.1f}, penalized: {penalized_count}')

        # Select top images while ensuring diversity
        selected: list[PinterestImage] = []
        selected_hashes: list[str] = []
        skipped_similar = 0

        for _score, pin in scored_pins:
            if len(selected) >= _NUM_IMAGES_TO_RETURN:
                break

            # Check diversity - skip if too similar to already selected
            pin_hash = self._compute_image_hash(pin)
            if self._is_too_similar(pin_hash, selected_hashes):
                skipped_similar += 1
                continue

            selected_hashes.append(pin_hash)
            selected.append(
                PinterestImage(
                    id=str(pin.get('id', '')),
                    title=pin.get('title'),
                    description=pin.get('description'),
                    image_url=pin.get('image_url', ''),
                    aspect_ratio=pin.get('aspect_ratio', AspectRatio.PORTRAIT_9_16.value),
                    image_width=pin.get('image_width'),
                    image_height=pin.get('image_height'),
                )
            )

        workflow.logger.info(f'Selected {len(selected)} images (skipped {skipped_similar} similar)')
        return selected

    def _score_pin(self, pin: dict) -> float:
        """Calculate quality score for a pin (0-100, can go negative for bad pins)."""
        score = 0.0

        # Resolution score (0-40 points)
        width = pin.get('image_width') or 0
        height = pin.get('image_height') or 0
        if width and height:
            pixels = width * height
            # Scale: 500K pixels = 20 points, 1M+ pixels = 40 points
            score += min(40, pixels / 25000)

        # Metadata completeness (0-20 points)
        if pin.get('title'):
            score += 10
        if pin.get('description'):
            score += 10

        # Aspect ratio preference for slideshows (0-30 points)
        aspect = pin.get('aspect_ratio', '')
        if aspect in (AspectRatio.PORTRAIT_9_16.value, '9:16'):
            score += 30  # Perfect for vertical video
        elif aspect in (AspectRatio.PORTRAIT_2_3.value, '2:3', AspectRatio.PORTRAIT_3_4.value, '3:4'):
            score += 25  # Good portrait
        elif aspect in (AspectRatio.SQUARE.value, '1:1'):
            score += 15  # Acceptable
        elif width and height and height > width:
            score += 20  # Any portrait orientation

        # ID presence (0-10 points) - indicates properly indexed content
        if pin.get('id'):
            score += 10

        # Text/watermark penalty (-50 points per keyword found)
        # Check title and description for keywords suggesting text-heavy images
        text_penalty = self._calculate_text_penalty(pin)
        score -= text_penalty

        return score

    def _calculate_text_penalty(self, pin: dict) -> float:
        """Calculate penalty for unwanted images (text-heavy, watermarked, collages).

        Returns penalty points (0-100) based on keywords found in metadata.
        """
        title = (pin.get('title') or '').lower()
        description = (pin.get('description') or '').lower()
        combined_text = f'{title} {description}'

        penalty = 0.0
        keywords_found = 0

        for keyword in _UNWANTED_IMAGE_KEYWORDS:
            if keyword in combined_text:
                keywords_found += 1
                # First keyword: big penalty, subsequent: smaller
                if keywords_found == 1:
                    penalty += 50
                else:
                    penalty += 15

        # Cap penalty at 100
        return min(100, penalty)

    def _compute_image_hash(self, pin: dict) -> str:
        """Compute a simple hash for diversity checking.

        Uses URL path components and dimensions to detect similar images.
        """
        url = pin.get('image_url', '')
        width = pin.get('image_width') or 0
        height = pin.get('image_height') or 0

        # Extract meaningful parts from URL (skip CDN prefixes)
        url_parts = url.split('/')[-3:]  # Last 3 path components
        hash_input = f'{"-".join(url_parts)}:{width}:{height}'

        return hashlib.md5(hash_input.encode()).hexdigest()[:8]

    def _is_too_similar(self, pin_hash: str, selected_hashes: list[str]) -> bool:
        """Check if a pin is too similar to already selected ones.

        Uses hash prefix matching to detect potential duplicates or variants.
        """
        # If hashes share first 4 chars, likely same source image
        return any(pin_hash[:4] == existing_hash[:4] for existing_hash in selected_hashes)

    async def _upload_images(self, images: list[PinterestImage]) -> list[PinterestImage]:
        """Upload all images to R2 storage in parallel."""
        if not images:
            return images

        # Create upload tasks for all images (same pattern as _scrape_pinterest)
        tasks = []
        for image in images:
            task = run_activity(
                upload_to_storage,
                StorageUploadInput(url=image.image_url, folder='pinterest/images'),
                timeout_minutes=2.0,
                retry_policy=FAST_RETRY,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build new images with R2 URLs, skip failed uploads
        uploaded_images: list[PinterestImage] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                workflow.logger.warning(f'Failed to upload image {images[i].id}: {result}')
                continue
            # Create new PinterestImage with R2 URL
            uploaded_images.append(
                PinterestImage(
                    id=images[i].id,
                    title=images[i].title,
                    description=images[i].description,
                    image_url=result.url,
                    aspect_ratio=images[i].aspect_ratio,
                    image_width=images[i].image_width,
                    image_height=images[i].image_height,
                )
            )

        return uploaded_images
