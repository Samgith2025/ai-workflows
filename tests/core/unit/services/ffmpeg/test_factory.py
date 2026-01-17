"""Tests for FFmpeg service factory."""

from app.core.services.ffmpeg import FFmpegService, get_ffmpeg_service


class TestServiceFactory:
    """Tests for service factory function."""

    def test_get_ffmpeg_service_returns_instance(self):
        """Factory should return FFmpegService."""
        service = get_ffmpeg_service()
        assert isinstance(service, FFmpegService)
