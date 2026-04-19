"""
DocuMind AI — PDF Parser
=========================
Extracts text from PDF files using PyMuPDF (fitz).

Why PyMuPDF over alternatives?
- PyPDF2: Struggles with complex layouts, scanned PDFs
- pdfminer: Slow, complex API
- PyMuPDF: Fast, handles complex layouts, rotated text,
  multi-column documents, and provides page-level access
"""

from pathlib import Path

import fitz  # PyMuPDF

from app.services.parsers.base_parser import BaseParser, ParseResult


class PDFParser(BaseParser):
    """Extracts text from PDF documents page by page."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    @property
    def parser_name(self) -> str:
        return "PDF Parser (PyMuPDF)"

    def extract_text(self, file_path: Path) -> ParseResult:
        pages: list[str] = []
        warnings: list[str] = []
        full_text_parts: list[str] = []

        try:
            doc = fitz.open(str(file_path))
            page_count = len(doc)

            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text("text")

                if not page_text.strip():
                    warnings.append(
                        f"Page {page_num + 1} appears to be scanned "
                        f"(no text extracted). Consider OCR for this page."
                    )
                    pages.append("")
                else:
                    pages.append(page_text)
                    full_text_parts.append(f"[Page {page_num + 1}]\n{page_text}")

            doc.close()
            full_text = "\n\n".join(full_text_parts)

            if not full_text.strip():
                warnings.append(
                    "No text could be extracted from this PDF. "
                    "It may be a fully scanned document."
                )

            return ParseResult(
                text=full_text,
                page_count=page_count,
                pages=pages,
                warnings=warnings,
            )

        except fitz.FileDataError as e:
            raise ValueError(f"Invalid or corrupted PDF file: {e}") from e
        except Exception as e:
            raise RuntimeError(f"PDF parsing failed: {e}") from e

    def extract_page(self, file_path: Path, page_number: int) -> str:
        """Extract text from a single page (1-indexed)."""
        try:
            doc = fitz.open(str(file_path))
            if page_number < 1 or page_number > len(doc):
                raise ValueError(
                    f"Page {page_number} does not exist. "
                    f"Document has {len(doc)} pages."
                )
            page = doc[page_number - 1]
            text = page.get_text("text")
            doc.close()
            return text
        except Exception as e:
            raise RuntimeError(f"Failed to extract page {page_number}: {e}") from e

    def get_metadata(self, file_path: Path) -> dict:
        """Extract PDF metadata — title, author, creation date, etc."""
        try:
            doc = fitz.open(str(file_path))
            metadata = doc.metadata
            page_count = len(doc)
            doc.close()
            return {
                "title":   metadata.get("title", ""),
                "author":  metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "pages":   page_count,
            }
        except Exception:
            return {}
