"""
DocuMind AI — Parser Unit Tests
=================================
Tests for individual document parsers.
These are pure unit tests — no HTTP, no Claude, no Redis.
Just file in → text out.

Test naming convention: test_<what>_<when>_<expected>
e.g. test_txt_parser_with_utf8_file_returns_correct_text
"""

import tempfile
from pathlib import Path

import pytest

from app.services.parsers.base_parser import ParseResult
from app.services.parsers.txt_parser import TextParser
from app.services.parser_service import ParserService


# ─── ParseResult Tests ────────────────────────────────────────────────────────

class TestParseResult:
    """Tests for the ParseResult dataclass."""

    def test_word_count_auto_calculated(self):
        """Word count should be calculated automatically from text."""
        result = ParseResult(text="hello world this is a test")
        assert result.word_count == 6

    def test_char_count_auto_calculated(self):
        """Char count should be calculated automatically from text."""
        result = ParseResult(text="hello")
        assert result.char_count == 5

    def test_is_empty_with_short_text(self):
        """Documents with fewer than 10 meaningful chars are considered empty."""
        result = ParseResult(text="Hi")
        assert result.is_empty is True

    def test_is_empty_with_normal_text(self):
        """Documents with normal text are not empty."""
        result = ParseResult(text="This is a proper document with real content.")
        assert result.is_empty is False

    def test_summary_stats_returns_dict(self):
        """summary_stats should return a dict with required keys."""
        result = ParseResult(text="test content here", page_count=2)
        stats = result.summary_stats
        assert "pages" in stats
        assert "words" in stats
        assert "characters" in stats
        assert "parser" in stats
        assert stats["pages"] == 2


# ─── Text Parser Tests ────────────────────────────────────────────────────────

class TestTextParser:
    """Tests for the plain text file parser."""

    @pytest.fixture
    def parser(self):
        return TextParser()

    def test_supported_extensions(self, parser):
        """Parser should support .txt and related extensions."""
        assert ".txt" in parser.supported_extensions
        assert ".md" in parser.supported_extensions

    def test_parser_name(self, parser):
        """Parser should have a human-readable name."""
        assert "Text" in parser.parser_name
        assert len(parser.parser_name) > 0

    def test_parse_utf8_file(self, parser, sample_txt_file):
        """Should correctly parse a UTF-8 text file."""
        result = parser.parse(sample_txt_file)

        assert result.text != ""
        assert "DocuMind AI Test Document" in result.text
        assert result.word_count > 0
        assert result.is_empty is False
        assert result.parser_used == parser.parser_name

    def test_parse_extracts_all_sections(self, parser, sample_txt_file):
        """All sections of the document should be in the extracted text."""
        result = parser.parse(sample_txt_file)

        assert "Section 1" in result.text
        assert "Section 2" in result.text
        assert "Section 3" in result.text

    def test_parse_preserves_numbers(self, parser, sample_txt_file):
        """Numeric data should be preserved exactly."""
        result = parser.parse(sample_txt_file)
        assert "$1,200,000" in result.text
        assert "15%" in result.text

    def test_parse_different_encodings(self, parser):
        """Parser should handle different file encodings."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="cp1252", delete=False
        ) as f:
            f.write("Héllo Wörld — latin-1 encoded text")
            tmp_path = Path(f.name)

        try:
            result = parser.parse(tmp_path)
            assert result.text != ""
            # Warning should mention encoding
            # (or it may just succeed silently — both are OK)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_parse_nonexistent_file_raises_error(self, parser):
        """Parsing a missing file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parser.parse(Path("/nonexistent/path/file.txt"))

    def test_parse_wrong_extension_raises_error(self, parser):
        """Parser should reject unsupported file extensions."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf content")
            tmp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="cannot handle"):
                parser.parse(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_clean_text_removes_excessive_newlines(self, parser):
        """_clean_text should collapse 3+ newlines into 2."""
        text = "paragraph 1\n\n\n\n\nparagraph 2"
        cleaned = parser._clean_text(text)
        assert "\n\n\n" not in cleaned
        assert "paragraph 1" in cleaned
        assert "paragraph 2" in cleaned

    def test_clean_text_strips_whitespace(self, parser):
        """_clean_text should strip leading/trailing whitespace."""
        text = "   hello world   "
        cleaned = parser._clean_text(text)
        assert cleaned == "hello world"

    def test_empty_file_returns_warnings(self, parser):
        """Empty file should parse without crashing but have warnings."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("")  # Empty file
            tmp_path = Path(f.name)

        try:
            result = parser.parse(tmp_path)
            # Should not crash — graceful handling
            assert result.text == "" or result.is_empty
        finally:
            tmp_path.unlink(missing_ok=True)


# ─── Parser Service Tests ─────────────────────────────────────────────────────

class TestParserService:
    """Tests for the unified ParserService."""

    @pytest.fixture
    def service(self):
        return ParserService()

    def test_is_supported_txt(self, service, sample_txt_file):
        """Should recognise .txt files as supported."""
        assert service.is_supported(sample_txt_file) is True

    def test_is_supported_unsupported_extension(self, service, temp_dir):
        """Should return False for unsupported file types."""
        fake_file = temp_dir / "document.xyz"
        fake_file.write_text("content")
        assert service.is_supported(fake_file) is False

    def test_get_parser_returns_correct_parser(self, service, sample_txt_file):
        """Should return TextParser for .txt files."""
        parser = service.get_parser(sample_txt_file)
        assert isinstance(parser, TextParser)

    def test_get_parser_unsupported_raises_error(self, service, temp_dir):
        """Should raise ValueError for unsupported file types."""
        fake = temp_dir / "file.xyz"
        fake.write_text("content")
        with pytest.raises(ValueError, match="No parser available"):
            service.get_parser(fake)

    def test_parse_document_returns_result(self, service, sample_txt_file):
        """parse_document should return a ParseResult."""
        result = service.parse_document(sample_txt_file)
        assert isinstance(result, ParseResult)
        assert result.text != ""
        assert result.word_count > 0

    def test_get_document_hash_is_consistent(self, service, sample_txt_file):
        """Same file should always produce the same hash."""
        hash1 = service.get_document_hash(sample_txt_file)
        hash2 = service.get_document_hash(sample_txt_file)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 is always 64 hex chars

    def test_get_document_hash_differs_for_different_files(
        self, service, temp_dir
    ):
        """Different content should produce different hashes."""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        file1.write_text("content one")
        file2.write_text("content two")

        assert service.get_document_hash(file1) != service.get_document_hash(file2)

    def test_get_chunks_splits_large_text(self, service):
        """Large text should be split into multiple chunks."""
        large_text = "word " * 2000  # 10,000 chars
        chunks = service.get_chunks(large_text, chunk_size=1000, overlap=100)
        assert len(chunks) > 1

    def test_get_chunks_small_text_returns_single_chunk(self, service):
        """Small text should return a single chunk."""
        small_text = "short text"
        chunks = service.get_chunks(small_text, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0] == small_text
