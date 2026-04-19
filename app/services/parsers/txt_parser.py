"""
DocuMind AI — Text File Parser
================================
Handles plain text (.txt) files with automatic encoding detection.

Why encoding detection matters:
Files created on Windows use UTF-16 or CP1252.
Files from Linux use UTF-8.
Files from older systems might use ASCII or Latin-1.
Opening a UTF-16 file as UTF-8 produces garbage characters (mojibake).
We try multiple encodings and use the one that works.
"""

from pathlib import Path

from app.services.parsers.base_parser import BaseParser, ParseResult

# Encodings to try in order of likelihood
ENCODINGS_TO_TRY = ["utf-8", "utf-16", "latin-1", "cp1252", "ascii"]


class TextParser(BaseParser):
    """Parses plain text files with automatic encoding detection."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".txt", ".text", ".md", ".markdown", ".csv", ".log"]

    @property
    def parser_name(self) -> str:
        return "Text Parser (built-in)"

    def extract_text(self, file_path: Path) -> ParseResult:
        warnings: list[str] = []
        text = ""
        encoding_used = "utf-8"

        # Try each encoding until one works
        for encoding in ENCODINGS_TO_TRY:
            try:
                text = file_path.read_text(encoding=encoding)
                encoding_used = encoding
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                raise RuntimeError(f"Failed to read text file: {e}") from e

        if not text:
            warnings.append(
                f"Could not decode file with any known encoding "
                f"({', '.join(ENCODINGS_TO_TRY)}). File may be binary."
            )

        if encoding_used != "utf-8":
            warnings.append(f"File decoded using {encoding_used} encoding.")

        # Split into "pages" by double newlines for consistency
        # (text files don't have real pages)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        return ParseResult(
            text=text,
            page_count=1,
            pages=[text],
            warnings=warnings,
        )
