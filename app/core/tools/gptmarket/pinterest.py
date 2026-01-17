"""GPTMarket Pinterest pins scraper tool.

Scrapes Pinterest pins based on search queries.
Uses the GPTMarket.io /v1/pins/scrape endpoint.
"""

from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.ai_models.common import AspectRatio
from app.core.configs import app_config
from app.core.tools.base import ToolCategory, ToolDefinition, ToolInput, ToolOutput
from app.core.tools.registry import tool_registry


class GptMarketPinterestPin(BaseModel):
    """A single Pinterest pin from GPTMarket API."""

    id: str = Field(..., description='Pin ID')
    title: str | None = Field(None, description='Pin title')
    description: str | None = Field(None, description='Pin description')
    image_url: str = Field(..., description='Image URL')
    aspect_ratio: AspectRatio = Field(..., description='Aspect ratio')
    image_width: int | None = Field(None, description='Image width in pixels')
    image_height: int | None = Field(None, description='Image height in pixels')


class GptMarketPinterestScraperInput(ToolInput):
    """Input for GPTMarket Pinterest scraper."""

    search_query: str = Field(..., min_length=1, description='Search query for Pinterest')
    search_type: str = Field('social_media', description='Type of search')
    pages: int = Field(1, ge=1, le=10, description='Number of pages to scrape (1-10)')


class GptMarketPinterestScraperOutput(ToolOutput):
    """Output from GPTMarket Pinterest scraper."""

    pins: list[GptMarketPinterestPin] = Field(default_factory=list, description='List of scraped pins')
    total: int = Field(0, description='Total number of pins returned')
    query: str = Field('', description='The search query used')


class GptMarketPinterestScraperTool(ToolDefinition):
    """GPTMarket Pinterest pins scraper."""

    input_class = GptMarketPinterestScraperInput
    output_class = GptMarketPinterestScraperOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        """Execute the Pinterest scraping request.

        Args:
            input: Search query and parameters

        Returns:
            GptMarketPinterestScraperOutput with pins or error
        """
        assert isinstance(input, GptMarketPinterestScraperInput)
        api_key = app_config.GPTMARKET_API_KEY
        if not api_key:
            return GptMarketPinterestScraperOutput.failure(
                error='GPTMARKET_API_KEY is not configured',
                pins=[],
                total=0,
                query=input.search_query,
            )

        url = f'{app_config.GPTMARKET_API_URL}/v1/scraping/pins'

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key,
        }

        payload = {
            'search_query': input.search_query,
            'search_type': input.search_type,
            'pages': input.pages,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
            except httpx.TimeoutException:
                return GptMarketPinterestScraperOutput.failure(
                    error='Request timed out',
                    pins=[],
                    total=0,
                    query=input.search_query,
                )
            except httpx.HTTPStatusError as e:
                return GptMarketPinterestScraperOutput.failure(
                    error=f'API error: {e.response.status_code} - {e.response.text}',
                    pins=[],
                    total=0,
                    query=input.search_query,
                )
            except httpx.RequestError as e:
                return GptMarketPinterestScraperOutput.failure(
                    error=f'Request failed: {e}',
                    pins=[],
                    total=0,
                    query=input.search_query,
                )

            try:
                data: dict[str, Any] = response.json()
            except ValueError:
                return GptMarketPinterestScraperOutput.failure(
                    error='Invalid JSON response from API',
                    pins=[],
                    total=0,
                    query=input.search_query,
                )

        # Parse pins from response - structure is data.data.data.pins
        inner_data = data.get('data', {})
        pins_data = inner_data.get('data', {})
        metadata = inner_data.get('metadata', {})
        raw_pins = pins_data.get('pins', [])

        pins = []
        for pin_data in raw_pins:
            try:
                # Only include 9:16 aspect ratio pins
                aspect_ratio_str = pin_data.get('aspect_ratio', '')
                if aspect_ratio_str != AspectRatio.PORTRAIT_9_16.value:
                    continue

                pin = GptMarketPinterestPin(
                    id=str(pin_data.get('id', '')),
                    title=pin_data.get('title'),
                    description=pin_data.get('description'),
                    image_url=pin_data.get('image_url', ''),
                    aspect_ratio=AspectRatio.PORTRAIT_9_16,
                    image_width=pin_data.get('image_width'),
                    image_height=pin_data.get('image_height'),
                )
                pins.append(pin)
            except Exception:
                # Skip malformed pins (e.g., missing required fields)
                pass

        return GptMarketPinterestScraperOutput(
            success=True,
            pins=pins,
            total=metadata.get('total_pins', len(pins)),
            query=metadata.get('search_query', input.search_query),
        )


GptMarketPinterestScraper = GptMarketPinterestScraperTool(
    id='gptmarket-pinterest-scraper',
    name='GPTMarket Pinterest Scraper',
    category=ToolCategory.SCRAPER,
    description='Scrape Pinterest pins based on search queries via GPTMarket API.',
    version='1.0.0',
    avg_execution_time_seconds=5.0,
    rate_limit_per_minute=60,
    requires_api_key=True,
    timeout_seconds=30.0,
)

tool_registry.register(GptMarketPinterestScraper)
