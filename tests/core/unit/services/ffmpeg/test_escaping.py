"""Tests for FFmpeg drawtext value escaping."""

from app.core.services.ffmpeg import _escape_drawtext_value


class TestDrawtextEscaping:
    """Tests for FFmpeg drawtext value escaping."""

    def test_plain_text_unchanged(self):
        """Plain text without special chars should be unchanged."""
        result = _escape_drawtext_value('Hello world')
        assert result == 'Hello world'

    def test_escapes_single_quote(self):
        """Single quotes use close-escape-reopen pattern for shell safety."""
        result = _escape_drawtext_value("You won't believe this")
        assert result == "You won'\\''t believe this"

    def test_escapes_colon(self):
        """Colons should be escaped."""
        result = _escape_drawtext_value('Time: 12:30')
        assert result == 'Time\\: 12\\:30'

    def test_escapes_percent(self):
        """Percent signs are doubled in drawtext (not backslash-escaped)."""
        result = _escape_drawtext_value('100% complete')
        assert result == '100%% complete'

    def test_escapes_backslash(self):
        """Backslashes should be escaped for FFmpeg."""
        result = _escape_drawtext_value('path\\to\\file')
        assert result == 'path\\\\to\\\\file'

    def test_escapes_comma(self):
        """Commas must be escaped to prevent breaking filter chains."""
        result = _escape_drawtext_value('Hello, world')
        assert result == 'Hello\\, world'

    def test_complex_text(self):
        """Complex text with multiple special chars should be properly escaped."""
        result = _escape_drawtext_value("It's 100% done: yes!")
        assert "'\\''s" in result  # Single quote escaped
        assert '%%' in result  # Percent doubled
        assert '\\:' in result  # Colon escaped
