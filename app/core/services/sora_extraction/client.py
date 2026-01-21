"""HTTP client for Sora video extraction."""

import asyncio
import re
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger(__name__)


class SoraClient:
    """Client for extracting MP4 URLs from Sora share links."""

    # Common MP4 CDN patterns used by OpenAI
    MP4_PATTERNS = [
        r'https?://[^\s"\'<>]+\.mp4(?:\?[^\s"\'<>]*)?',  # Direct MP4 URLs
    ]

    TIMEOUT = aiohttp.ClientTimeout(total=30)
    MAX_REDIRECTS = 5

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize Sora client.

        Args:
            session: Optional aiohttp session. If not provided, one will be created per request.
        """
        self.session = session
        self._owns_session = session is None

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def close(self):
        """Close the client session if owned."""
        if self._owns_session and self.session:
            await self.session.close()

    async def get_mp4_url(self, sora_share_url: str) -> str:
        """Extract MP4 URL from a Sora share link.

        Args:
            sora_share_url: The Sora share URL (e.g., https://sora.chatgpt.com/share/xxxx)

        Returns:
            The direct MP4 URL

        Raises:
            ValueError: If the URL is invalid or MP4 cannot be extracted
            aiohttp.ClientError: If the HTTP request fails
        """
        # Validate URL format
        parsed = urlparse(sora_share_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f'Invalid URL format: {sora_share_url}')

        if 'sora.chatgpt.com' not in parsed.netloc.lower():
            raise ValueError(f'URL must be from sora.chatgpt.com, got: {parsed.netloc}')

        logger.info('Extracting MP4 from Sora URL', url=sora_share_url)

        # Fetch the share page
        html_content = await self._fetch_page(sora_share_url)

        # Try to extract MP4 URL from HTML
        mp4_url = self._extract_mp4_from_html(html_content)

        if mp4_url:
            logger.info('Found MP4 URL', mp4_url=mp4_url)
            return mp4_url

        # Try to extract from JSON embedded in page
        mp4_url = self._extract_mp4_from_json(html_content)

        if mp4_url:
            logger.info('Found MP4 URL in JSON', mp4_url=mp4_url)
            return mp4_url

        raise ValueError('Could not find MP4 URL in Sora share page')

    async def _fetch_page(self, url: str) -> str:
        """Fetch HTML content from a URL.

        Args:
            url: URL to fetch

        Returns:
            HTML content

        Raises:
            aiohttp.ClientError: If the request fails
        """
        session = self.session or aiohttp.ClientSession(timeout=self.TIMEOUT)

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://sora.chatgpt.com/',
            }

            async with session.get(
                url,
                allow_redirects=True,
                headers=headers,
            ) as response:
                response.raise_for_status()
                return await response.text()
        finally:
            if not self.session:
                await session.close()

    @staticmethod
    def _extract_mp4_from_html(html_content: str) -> Optional[str]:
        """Extract MP4 URL from HTML content.

        Looks for:
        - <video> src attribute
        - <source> tag with src attribute
        - <meta> tags with video URL

        Args:
            html_content: HTML content to parse

        Returns:
            MP4 URL if found, None otherwise
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Look for video tag with src
        video_tag = soup.find('video')
        if video_tag and video_tag.get('src'):
            url = video_tag.get('src')
            if url.endswith('.mp4') or '.mp4' in url:
                return url

        # Look for source tag inside video
        source_tag = soup.find('source', {'type': 'video/mp4'})
        if source_tag and source_tag.get('src'):
            url = source_tag.get('src')
            if url.endswith('.mp4') or '.mp4' in url:
                return url

        # Look for meta og:video tags
        meta_tags = soup.find_all('meta', {'property': 'og:video'})
        for meta in meta_tags:
            url = meta.get('content')
            if url and ('.mp4' in url.lower()):
                return url

        return None

    @staticmethod
    def _extract_mp4_from_json(html_content: str) -> Optional[str]:
        """Extract MP4 URL from embedded JSON in HTML.

        Looks for JSON-LD, window.__INITIAL_STATE__, or other common patterns.

        Args:
            html_content: HTML content to parse

        Returns:
            MP4 URL if found, None otherwise
        """
        # Find all MP4 URLs using regex pattern
        for pattern in SoraClient.MP4_PATTERNS:
            matches = re.findall(pattern, html_content)
            if matches:
                # Return the first valid MP4 URL found
                for url in matches:
                    if url.startswith('http'):
                        return url

        return None
