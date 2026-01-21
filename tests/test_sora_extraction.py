"""Tests for Sora video extraction service."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.services.sora_extraction.client import SoraClient
from app.core.services.sora_extraction.downloader import VideoDownloader
from app.core.services.sora_extraction.service import SoraExtractionService


class TestSoraClient:
    """Tests for SoraClient."""

    def test_extract_mp4_from_html_video_tag(self):
        """Test extracting MP4 from <video> src attribute."""
        html = '''
            <video src="https://video-cdn.openai.com/example.mp4"></video>
        '''
        url = SoraClient._extract_mp4_from_html(html)
        assert url == "https://video-cdn.openai.com/example.mp4"

    def test_extract_mp4_from_html_source_tag(self):
        """Test extracting MP4 from <source> tag."""
        html = '''
            <video>
                <source type="video/mp4" src="https://video-cdn.openai.com/video.mp4">
            </video>
        '''
        url = SoraClient._extract_mp4_from_html(html)
        assert url == "https://video-cdn.openai.com/video.mp4"

    def test_extract_mp4_from_html_meta_tag(self):
        """Test extracting MP4 from og:video meta tag."""
        html = '''
            <head>
                <meta property="og:video" content="https://video-cdn.openai.com/og-video.mp4">
            </head>
        '''
        url = SoraClient._extract_mp4_from_html(html)
        assert url == "https://video-cdn.openai.com/og-video.mp4"

    def test_extract_mp4_from_html_no_video(self):
        """Test when no video found."""
        html = '<html><body>No video here</body></html>'
        url = SoraClient._extract_mp4_from_html(html)
        assert url is None

    def test_extract_mp4_from_json_regex(self):
        """Test extracting MP4 from JSON using regex."""
        html = '''
            <script>
                {"videoUrl": "https://video-cdn.openai.com/data.mp4?token=abc123"}
            </script>
        '''
        url = SoraClient._extract_mp4_from_json(html)
        assert "https://video-cdn.openai.com/data.mp4" in url

    @pytest.mark.asyncio
    async def test_invalid_url_format(self):
        """Test that invalid URL raises ValueError."""
        client = SoraClient()
        with pytest.raises(ValueError, match="Invalid URL format"):
            await client.get_mp4_url("not-a-url")

    @pytest.mark.asyncio
    async def test_wrong_domain(self):
        """Test that non-sora.chatgpt.com URLs raise ValueError."""
        client = SoraClient()
        with pytest.raises(ValueError, match="must be from sora.chatgpt.com"):
            await client.get_mp4_url("https://example.com/share/xxxx")

    @pytest.mark.asyncio
    async def test_get_mp4_url_success(self):
        """Test successful MP4 URL extraction."""
        html = '<video src="https://video-cdn.openai.com/test.mp4"></video>'

        with patch.object(SoraClient, '_fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = html

            client = SoraClient()
            url = await client.get_mp4_url("https://sora.chatgpt.com/share/test123")

            assert "video-cdn.openai.com" in url
            assert url.endswith("test.mp4")


class TestVideoDownloader:
    """Tests for VideoDownloader."""

    @pytest.mark.asyncio
    async def test_download_to_temp(self):
        """Test downloading to temp directory."""
        mock_response = MagicMock()
        mock_response.content = MagicMock()
        mock_response.content_length = 1024
        mock_response.content.iter_chunked = AsyncMock(
            return_value=[b'test_chunk']
        )
        mock_response.raise_for_status = MagicMock()

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            downloader = VideoDownloader()
            path = await downloader.download_to_temp(
                "https://video-cdn.openai.com/test.mp4"
            )

            assert path.exists()
            assert path.suffix == ".mp4"
            # Clean up
            path.unlink(missing_ok=True)
            path.parent.rmdir()


class TestSoraExtractionService:
    """Tests for SoraExtractionService."""

    @pytest.mark.asyncio
    async def test_extract_and_download_with_output_path(self):
        """Test extract_and_download with explicit output path."""
        with patch.object(
            SoraClient, 'get_mp4_url', new_callable=AsyncMock
        ) as mock_get_url, patch.object(
            VideoDownloader, 'download', new_callable=AsyncMock
        ) as mock_download:
            mock_get_url.return_value = "https://video-cdn.openai.com/test.mp4"
            output_path = Path("/tmp/test_video.mp4")
            mock_download.return_value = output_path

            service = SoraExtractionService()
            result = await service.extract_and_download(
                "https://sora.chatgpt.com/share/test",
                output_path=output_path,
            )

            assert result == output_path
            mock_download.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_and_download_error_handling(self):
        """Test error handling in extraction."""
        with patch.object(SoraClient, 'get_mp4_url', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ValueError("Cannot extract MP4")

            service = SoraExtractionService()
            with pytest.raises(ValueError):
                await service.extract_and_download("https://sora.chatgpt.com/share/test")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
