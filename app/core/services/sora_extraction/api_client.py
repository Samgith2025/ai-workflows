"""Sora API client - extracts video URLs via the public API endpoint."""

import re
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import structlog

logger = structlog.get_logger(__name__)


class SoraAPIClient:
    """Extract video URLs from Sora using the public API endpoint."""

    API_BASE = "https://sora.chatgpt.com/backend/public/generations/"

    TIMEOUT = aiohttp.ClientTimeout(total=30)

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize API client."""
        self.session = session
        self._owns_session = session is None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        pass  # Session managed externally or per-request

    def extract_video_id(self, url: str) -> str:
        """Extract video ID from Sora URL.

        Supports formats:
        - https://sora.chatgpt.com/g/gen_xxxxx
        - https://sora.chatgpt.com/p/s_xxxxx?psh=...
        - Just the ID: gen_xxxxx or s_xxxxx

        Args:
            url: Sora URL or video ID

        Returns:
            The video ID
        """
        # If it's already just an ID
        if url.startswith("gen_") or url.startswith("s_"):
            return url

        # Parse URL
        parsed = urlparse(url)
        path = parsed.path

        # Extract ID from path
        # /g/gen_xxxxx or /p/s_xxxxx
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[-1]  # Last part is the ID

        # Fallback: try regex
        match = re.search(r"(gen_[a-zA-Z0-9]+|s_[a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)

        raise ValueError(f"Could not extract video ID from URL: {url}")

    async def get_video_data(self, url: str) -> dict:
        """Fetch video metadata from Sora API.

        Args:
            url: Sora URL or video ID

        Returns:
            Video metadata dict

        Raises:
            ValueError: If video not found or API error
        """
        video_id = self.extract_video_id(url)
        endpoint = f"{self.API_BASE}{video_id}"

        logger.info("Fetching Sora video data", video_id=video_id, endpoint=endpoint)

        session = self.session or aiohttp.ClientSession(timeout=self.TIMEOUT)

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json",
            }

            async with session.get(endpoint, headers=headers) as response:
                if response.status == 404:
                    raise ValueError(f"Video not found: {video_id}")
                if response.status == 403:
                    raise ValueError(f"Access denied for video: {video_id}")

                response.raise_for_status()
                data = await response.json()

                logger.info("Got video data", video_id=video_id, has_encodings="encodings" in data)
                return data

        finally:
            if not self.session:
                await session.close()

    async def get_mp4_url(self, url: str, quality: str = "source") -> str:
        """Get direct MP4 download URL.

        Args:
            url: Sora URL or video ID
            quality: Quality level - "source" (highest), "md" (medium), "ld" (low)

        Returns:
            Direct MP4 URL (no watermark for source quality)
        """
        data = await self.get_video_data(url)

        if "encodings" not in data:
            raise ValueError("No video encodings found in response")

        encodings = data["encodings"]

        if quality not in encodings:
            available = list(encodings.keys())
            raise ValueError(f"Quality '{quality}' not available. Options: {available}")

        mp4_path = encodings[quality].get("path")
        if not mp4_path:
            raise ValueError(f"No path found for quality '{quality}'")

        logger.info("Extracted MP4 URL", quality=quality, url=mp4_path[:80])
        return mp4_path

    async def get_video_info(self, url: str) -> dict:
        """Get video metadata.

        Args:
            url: Sora URL or video ID

        Returns:
            Dict with video info (title, dimensions, duration, etc.)
        """
        data = await self.get_video_data(url)

        return {
            "id": data.get("id"),
            "title": data.get("title", "Untitled"),
            "width": data.get("width"),
            "height": data.get("height"),
            "duration": data.get("encodings", {}).get("source", {}).get("duration_secs"),
            "created_at": data.get("created_at"),
            "available_qualities": list(data.get("encodings", {}).keys()),
        }
