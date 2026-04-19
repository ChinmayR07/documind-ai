"""
DocuMind AI — Parser Service
==============================
Unified entry point for all document parsing.
Auto-selects the right parser based on file type.

Design Pattern: Strategy + Factory
"""

import hashlib
from pathlib import Path

from app.constants import DocumentType, Limits
from app.services.parsers.base_parser import BaseParser, ParseResult
from app.services.parsers.docx_parser import DocxParser
from app.services.parsers.ocr_parser import ImageParser
from app.services.parsers.pdf_parser import PDFParser
from app.services.parsers.txt_parser import TextParser
from app.utils.text_utils import chunk_text


class ParserService:
    """
    Unified document parsing service.
    Maintains a registry of parsers and routes files to the correct one.
    """

    def __init__(self) -> None:
        self._parsers: list[BaseParser] = [
            PDFParser(),
            DocxParser(),
            TextParser(),
            ImageParser(),
        ]
        self._extension_map: dict[str, BaseParser] = {}
        for parser in self._parsers:
            for ext in parser.supported_extensions:
                self._extension_map[ext.lower()] = parser

    def get_parser(self, file_path: Path) -> BaseParser:
        """Find the right parser for a given file."""
        ext = file_path.suffix.lower()
        parser = self._extension_map.get(ext)
        if not parser:
            supported = sorted(self._extension_map.keys())
            raise ValueError(
                f"No parser available for '{ext}' files. "
                f"Supported extensions: {', '.join(supported)}"
            )
        return parser

    def parse_document(self, file_path: Path) -> ParseResult:
        """
        Parse a document and return extracted text + metadata.
        Main method callers should use.
        """
        parser = self.get_parser(file_path)
        result = parser.parse(file_path)

        # Truncate if text exceeds Claude's context window
        if len(result.text) > Limits.MAX_TEXT_CHARS_FOR_CLAUDE:
            original_length = len(result.text)
            result.text = result.text[:Limits.MAX_TEXT_CHARS_FOR_CLAUDE]
            result.warnings.append(
                f"Document text was truncated from {original_length:,} to "
                f"{Limits.MAX_TEXT_CHARS_FOR_CLAUDE:,} characters "
                f"to fit within AI context limits."
            )
        return result

    def get_document_hash(self, file_path: Path) -> str:
        """
        Generate SHA-256 hash of file content.
        Used as cache key — same content = same hash = cached result.
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_document_type(self, file_path: Path) -> DocumentType:
        """Map file extension to DocumentType enum."""
        return DocumentType.from_extension(file_path.suffix)

    def is_supported(self, file_path: Path) -> bool:
        """Check if we have a parser for this file type."""
        return file_path.suffix.lower() in self._extension_map

    def get_chunks(
        self,
        text: str,
        chunk_size: int = 4000,
        overlap: int = 200,
    ) -> list[str]:
        """
        Split large text into overlapping chunks for large documents.
        Overlap ensures context is not lost at chunk boundaries.
        """
        return chunk_text(text, chunk_size=chunk_size, overlap=overlap)


# Singleton instance shared across the entire app
parser_service = ParserService()
