"""Video downloader for streaming MP4 from CDN to local storage."""

import asyncio
from pathlib import Path
from typing import Optional

import aiohttp
import structlog

logger = structlog.get_logger(__name__)

# Chunk size for streaming downloads (10 MB)
CHUNK_SIZE = 10 * 1024 * 1024


class VideoDownloader:
    """Async downloader for streaming videos to local storage."""

    TIMEOUT = aiohttp.ClientTimeout(total=300)  # 5 minutes for large videos

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize downloader.

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
        """Close the session if owned."""
        if self._owns_session and self.session:
            await self.session.close()

    async def download(
        self,
        url: str,
        output_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> Path:
        """Download video from URL to local file.

        Args:
            url: Direct MP4 URL to download
            output_path: Path to save the video file
            progress_callback: Optional callback for progress updates (bytes_downloaded, total_bytes)

        Returns:
            Path to the downloaded file

        Raises:
            aiohttp.ClientError: If download fails
            IOError: If file write fails
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        session = self.session or aiohttp.ClientSession(timeout=self.TIMEOUT)

        try:
            async with session.get(
                url,
                allow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0 (Sora Video Extractor)'},
            ) as response:
                response.raise_for_status()

                total_size = response.content_length or 0
                downloaded = 0

                logger.info('Starting video download', url=url, size_bytes=total_size)

                with open(output_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if progress_callback:
                                progress_callback(downloaded, total_size)

                            logger.debug(
                                'Download progress',
                                downloaded=downloaded,
                                total=total_size,
                                percent=int((downloaded / total_size * 100) if total_size else 0),
                            )

                logger.info('Download complete', output_path=str(output_path), size_bytes=downloaded)
                return output_path

        except Exception as e:
            # Clean up partial file on error
            if output_path.exists():
                output_path.unlink()
            logger.error('Download failed', url=url, error=str(e))
            raise
        finally:
            if not self.session:
                await session.close()

    async def download_to_temp(
        self,
        url: str,
        temp_dir: Optional[Path] = None,
        filename: str = 'video.mp4',
    ) -> Path:
        """Download video to temp directory.

        Args:
            url: Direct MP4 URL to download
            temp_dir: Temp directory to use (defaults to /tmp)
            filename: Filename for the video

        Returns:
            Path to the downloaded file in temp directory
        """
        if temp_dir is None:
            temp_dir = Path('/tmp/sora_videos')

        temp_dir = Path(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        output_path = temp_dir / filename

        return await self.download(url, output_path)
