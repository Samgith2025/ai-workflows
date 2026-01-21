"""Sora extraction service - main service interface."""

from pathlib import Path
from typing import Optional

import aiohttp
import structlog

from app.core.services.sora_extraction.browser_client import SoraBrowserClient
from app.core.services.sora_extraction.downloader import VideoDownloader

logger = structlog.get_logger(__name__)


class SoraExtractionService:
    """Service for extracting and downloading videos from Sora share links.

    Uses browser automation to reliably extract MP4 URLs from Sora share pages.
    """

    def __init__(self, session: Optional[aiohttp.ClientSession] = None, headless: bool = True):
        """Initialize extraction service.

        Args:
            session: Optional aiohttp session for video downloads
            headless: Run browser in headless mode
        """
        self.session = session
        self._owns_session = session is None
        self.browser_client = SoraBrowserClient(headless=headless)
        self.downloader = VideoDownloader(session)

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def close(self):
        """Close all resources."""
        await self.browser_client.close()
        await self.downloader.close()

    async def extract_and_download(
        self,
        sora_share_url: str,
        output_path: Optional[Path] = None,
        temp_dir: Optional[Path] = None,
    ) -> Path:
        """Extract MP4 from Sora share link and download it.

        Complete flow:
        1. Fetch the Sora share page
        2. Parse HTML/JSON to find MP4 URL
        3. Stream download the MP4 to local storage

        Args:
            sora_share_url: The Sora share URL (e.g., https://sora.chatgpt.com/share/xxxx)
            output_path: Explicit output path. If provided, uses this instead of temp_dir
            temp_dir: Temp directory for downloads (defaults to /tmp/sora_videos)

        Returns:
            Path to the downloaded MP4 file

        Raises:
            ValueError: If the URL is invalid or MP4 cannot be extracted
            aiohttp.ClientError: If HTTP requests fail
            IOError: If file operations fail
        """
        logger.info('Starting Sora extraction', url=sora_share_url)

        try:
            # Step 1: Launch browser if needed
            if not self.browser_client.browser:
                await self.browser_client.launch()

            # Step 2: Extract MP4 URL from Sora share page using browser
            mp4_url = await self.browser_client.get_mp4_url(sora_share_url)
            logger.info('Extracted MP4 URL', mp4_url=mp4_url)

            # Step 3: Download the video
            if output_path:
                result_path = await self.downloader.download(mp4_url, output_path)
            else:
                result_path = await self.downloader.download_to_temp(mp4_url, temp_dir=temp_dir)

            logger.info('Extraction and download complete', output_path=str(result_path))
            return result_path

        except Exception as e:
            logger.error('Extraction failed', url=sora_share_url, error=str(e))
            raise


# Singleton instance
_service_instance: Optional[SoraExtractionService] = None


def get_sora_service() -> SoraExtractionService:
    """Get the Sora extraction service (singleton).

    Returns:
        SoraExtractionService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = SoraExtractionService()
    return _service_instance


def reset_sora_service():
    """Reset the singleton service (useful for testing)."""
    global _service_instance
    _service_instance = None
