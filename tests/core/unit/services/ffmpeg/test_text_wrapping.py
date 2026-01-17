"""Tests for text wrapping function."""

from app.core.services.ffmpeg import _wrap_text


class TestTextWrapping:
    """Tests for text wrapping function."""

    def test_short_text_no_wrap(self):
        """Short text should not be wrapped."""
        result = _wrap_text('Hello world', max_chars_per_line=30)
        assert result == 'Hello world'

    def test_long_text_wraps(self):
        """Long text should be wrapped at word boundaries."""
        text = 'This is a very long sentence that should be wrapped'
        result = _wrap_text(text, max_chars_per_line=20)
        lines = result.split('\n')
        assert len(lines) > 1
        for line in lines:
            assert len(line) <= 25  # Allow some overflow for long words

    def test_single_word_exceeds_limit(self):
        """Single word longer than limit should remain intact."""
        result = _wrap_text('Supercalifragilisticexpialidocious', max_chars_per_line=10)
        assert result == 'Supercalifragilisticexpialidocious'

    def test_empty_string(self):
        """Empty string should return empty string."""
        result = _wrap_text('', max_chars_per_line=30)
        assert result == ''

    def test_multiple_spaces(self):
        """Multiple spaces between words should be normalized."""
        result = _wrap_text('Hello   world', max_chars_per_line=30)
        assert result == 'Hello world'
