"""
DocuMind AI — Utility and Config Tests
========================================
Unit tests for utility functions and configuration.
These are the fastest tests — pure Python, no I/O, no HTTP.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# ─── Text Utility Tests ───────────────────────────────────────────────────────

class TestChunkText:
    """Tests for the text chunking utility."""

    from app.utils.text_utils import chunk_text

    def test_small_text_returns_single_chunk(self):
        from app.utils.text_utils import chunk_text
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_large_text_splits_into_multiple_chunks(self):
        from app.utils.text_utils import chunk_text
        text = "word " * 500  # 2500 chars
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) > 1

    def test_empty_text_returns_empty_list(self):
        from app.utils.text_utils import chunk_text
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_chunks_cover_all_content(self):
        from app.utils.text_utils import chunk_text
        text = "The quick brown fox. " * 100
        chunks = chunk_text(text, chunk_size=200, overlap=20)
        # All chunks together should contain all unique words
        combined = " ".join(chunks)
        assert "quick" in combined
        assert "brown" in combined

    def test_chunk_size_respected(self):
        from app.utils.text_utils import chunk_text
        text = "x" * 10000
        chunks = chunk_text(text, chunk_size=1000, overlap=0)
        for chunk in chunks:
            # Each chunk should be at most chunk_size + a little for overlap
            assert len(chunk) <= 1100  # Allow some tolerance for word boundaries


class TestCleanText:
    """Tests for text cleaning utility."""

    def test_removes_excessive_newlines(self):
        from app.utils.text_utils import clean_text
        text = "para 1\n\n\n\n\npara 2"
        result = clean_text(text)
        assert "\n\n\n" not in result

    def test_normalizes_windows_line_endings(self):
        from app.utils.text_utils import clean_text
        text = "line 1\r\nline 2\r\nline 3"
        result = clean_text(text)
        assert "\r\n" not in result
        assert "line 1" in result
        assert "line 2" in result

    def test_strips_leading_trailing_whitespace(self):
        from app.utils.text_utils import clean_text
        result = clean_text("   hello world   ")
        assert result == "hello world"

    def test_empty_string_returns_empty(self):
        from app.utils.text_utils import clean_text
        assert clean_text("") == ""
        assert clean_text(None) == ""  # type: ignore


class TestTruncateText:
    """Tests for text truncation utility."""

    def test_short_text_unchanged(self):
        from app.utils.text_utils import truncate_text
        text = "short text"
        assert truncate_text(text, max_chars=100) == text

    def test_long_text_is_truncated(self):
        from app.utils.text_utils import truncate_text
        text = "word " * 100
        result = truncate_text(text, max_chars=50)
        assert len(result) <= 55  # 50 + suffix length

    def test_truncation_adds_suffix(self):
        from app.utils.text_utils import truncate_text
        text = "word " * 100
        result = truncate_text(text, max_chars=50, suffix="...")
        assert result.endswith("...")

    def test_truncation_at_word_boundary(self):
        from app.utils.text_utils import truncate_text
        text = "the quick brown fox jumped"
        result = truncate_text(text, max_chars=15)
        # Should not cut mid-word
        words = result.replace("...", "").strip().split()
        for word in words:
            assert word in ["the", "quick", "brown", "fox", "jumped"]


class TestCountTokens:
    """Tests for token counting approximation."""

    def test_empty_string_is_zero(self):
        from app.utils.text_utils import count_tokens_approx
        assert count_tokens_approx("") == 0

    def test_approximation_is_reasonable(self):
        from app.utils.text_utils import count_tokens_approx
        # 1000 chars of English ≈ 250 tokens (1 token ≈ 4 chars)
        text = "a" * 1000
        tokens = count_tokens_approx(text)
        assert 200 <= tokens <= 300


# ─── File Utility Tests ───────────────────────────────────────────────────────

class TestFileUtils:
    """Tests for file validation utilities."""

    def test_validate_file_size_passes_small_file(self):
        from app.utils.file_utils import validate_file_size
        # Should not raise for a small file
        validate_file_size(1024)  # 1KB

    def test_validate_file_size_raises_for_large_file(self):
        from app.utils.file_utils import validate_file_size
        with pytest.raises(ValueError, match="size"):
            validate_file_size(25 * 1024 * 1024)  # 25MB over 20MB limit

    def test_validate_extension_passes_pdf(self):
        from app.utils.file_utils import validate_file_extension
        validate_file_extension("document.pdf")  # Should not raise

    def test_validate_extension_passes_txt(self):
        from app.utils.file_utils import validate_file_extension
        validate_file_extension("document.txt")  # Should not raise

    def test_validate_extension_raises_for_exe(self):
        from app.utils.file_utils import validate_file_extension
        with pytest.raises(ValueError, match="not supported"):
            validate_file_extension("malware.exe")

    def test_generate_safe_filename_is_uuid(self):
        from app.utils.file_utils import generate_safe_filename
        result = generate_safe_filename("my document.pdf")
        # Should be UUID + .pdf
        assert result.endswith(".pdf")
        assert len(result) == 40  # 36 UUID + 4 ".pdf"
        assert " " not in result

    def test_generate_safe_filename_preserves_extension(self):
        from app.utils.file_utils import generate_safe_filename
        assert generate_safe_filename("file.docx").endswith(".docx")
        assert generate_safe_filename("image.PNG").endswith(".png")

    def test_generate_safe_filename_unique(self):
        from app.utils.file_utils import generate_safe_filename
        names = {generate_safe_filename("test.txt") for _ in range(100)}
        assert len(names) == 100  # All should be unique

    def test_get_file_size_mb(self, tmp_path):
        from app.utils.file_utils import get_file_size_mb
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"x" * 1024 * 1024)  # 1MB exactly
        size = get_file_size_mb(test_file)
        assert 0.9 <= size <= 1.1

    def test_delete_file_safely_nonexistent(self, tmp_path):
        from app.utils.file_utils import delete_file_safely
        fake = tmp_path / "nonexistent.txt"
        # Should not raise even for missing file
        result = delete_file_safely(fake)
        assert result is True  # missing_ok=True means it "succeeded"

    def test_delete_file_safely_real_file(self, tmp_path):
        from app.utils.file_utils import delete_file_safely
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")
        result = delete_file_safely(real_file)
        assert result is True
        assert not real_file.exists()


# ─── Configuration Tests ──────────────────────────────────────────────────────

class TestConfig:
    """Tests for application configuration."""

    def test_settings_loads_successfully(self):
        """Settings should load without raising errors."""
        from app.config import settings
        assert settings is not None

    def test_max_file_size_bytes_computed(self):
        """MAX_FILE_SIZE_BYTES should be MB * 1024 * 1024."""
        from app.config import settings
        expected = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        assert settings.MAX_FILE_SIZE_BYTES == expected

    def test_upload_path_is_path_object(self):
        """UPLOAD_PATH should be a Path object."""
        from app.config import settings
        assert isinstance(settings.UPLOAD_PATH, Path)

    def test_is_production_false_in_test(self):
        """IS_PRODUCTION should be False in test environment."""
        from app.config import settings
        assert settings.IS_PRODUCTION is False

    def test_allowed_extensions_includes_pdf(self):
        """PDF should be in allowed extensions."""
        from app.config import settings
        assert ".pdf" in settings.ALLOWED_EXTENSIONS

    def test_allowed_extensions_includes_images(self):
        """Image extensions should be in allowed list."""
        from app.config import settings
        assert ".jpg" in settings.ALLOWED_EXTENSIONS
        assert ".png" in settings.ALLOWED_EXTENSIONS


# ─── Constants Tests ──────────────────────────────────────────────────────────

class TestConstants:
    """Tests for enum constants and limits."""

    def test_document_type_from_extension_pdf(self):
        from app.constants import DocumentType
        assert DocumentType.from_extension(".pdf") == DocumentType.PDF

    def test_document_type_from_extension_docx(self):
        from app.constants import DocumentType
        assert DocumentType.from_extension(".docx") == DocumentType.DOCX

    def test_document_type_from_extension_image(self):
        from app.constants import DocumentType
        assert DocumentType.from_extension(".jpg") == DocumentType.IMAGE
        assert DocumentType.from_extension(".png") == DocumentType.IMAGE

    def test_document_type_unsupported_raises(self):
        from app.constants import DocumentType
        with pytest.raises(ValueError):
            DocumentType.from_extension(".xyz")

    def test_document_type_case_insensitive(self):
        from app.constants import DocumentType
        assert DocumentType.from_extension(".PDF") == DocumentType.PDF
        assert DocumentType.from_extension(".DOCX") == DocumentType.DOCX

    def test_limits_are_positive(self):
        from app.constants import Limits
        assert Limits.MAX_TEXT_CHARS_FOR_CLAUDE > 0
        assert Limits.MAX_QUESTION_LENGTH > 0
        assert Limits.MIN_DOCUMENTS_TO_COMPARE >= 2
        assert Limits.MAX_DOCUMENTS_TO_COMPARE <= 5
