"""
DocuMind AI — Base Parser
==========================
Abstract base class that all document parsers must implement.
This enforces a consistent interface regardless of file type.

Design Pattern: Template Method + Strategy
- Template Method: parse() defines the skeleton (validate → extract → clean)
- Strategy: Each subclass implements extract_text() differently
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParseResult:
    """
    Standardized result returned by every parser.
    Using a dataclass gives us free __repr__, __eq__, and type hints.
    """

    # The extracted text content
    text: str

    # Document metadata
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    language: str = "unknown"

    # Per-page text (useful for citation tracking)
    pages: list[str] = field(default_factory=list)

    # Any warnings during parsing (e.g. "Page 3 had no text")
    warnings: list[str] = field(default_factory=list)

    # Parser that was used
    parser_used: str = ""

    def __post_init__(self) -> None:
        """Auto-calculate word and char counts after init."""
        if self.text and not self.word_count:
            self.word_count = len(self.text.split())
        if self.text and not self.char_count:
            self.char_count = len(self.text)

    @property
    def is_empty(self) -> bool:
        """True if no meaningful text was extracted."""
        return len(self.text.strip()) < 10

    @property
    def summary_stats(self) -> dict:
        """Quick stats dict for API responses."""
        return {
            "pages": self.page_count,
            "words": self.word_count,
            "characters": self.char_count,
            "parser": self.parser_used,
            "warnings": self.warnings,
        }


class BaseParser(ABC):
    """
    Abstract base class for all document parsers.

    Every parser MUST implement extract_text().
    The parse() method provides the common workflow:
    validate → extract → clean → return ParseResult
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """List of file extensions this parser handles e.g. ['.pdf']"""
        ...

    @property
    @abstractmethod
    def parser_name(self) -> str:
        """Human-readable name e.g. 'PDF Parser (PyMuPDF)'"""
        ...

    @abstractmethod
    def extract_text(self, file_path: Path) -> ParseResult:
        """
        Extract text from the document at file_path.
        Must return a ParseResult — never raise exceptions directly,
        instead add to ParseResult.warnings.
        """
        ...

    def parse(self, file_path: Path) -> ParseResult:
        """
        Template method — defines the parsing workflow.
        Subclasses implement extract_text(), not this method.
        """
        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Validate extension
        if file_path.suffix.lower() not in self.supported_extensions:
            raise ValueError(
                f"{self.parser_name} cannot handle {file_path.suffix} files. "
                f"Supported: {self.supported_extensions}"
            )

        # Extract text
        result = self.extract_text(file_path)

        # Set parser name
        result.parser_used = self.parser_name

        # Clean the text
        result.text = self._clean_text(result.text)

        return result

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text — remove excessive whitespace,
        fix encoding issues, normalize line breaks.
        Applied by all parsers automatically.
        """
        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines (more than 2 consecutive)
        import re

        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove null bytes and other control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def can_handle(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() in self.supported_extensions
