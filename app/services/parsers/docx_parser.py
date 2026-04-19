"""
DocuMind AI — DOCX Parser
==========================
Extracts text from Microsoft Word (.docx) files using python-docx.

Fun fact: A .docx file is actually a ZIP archive containing XML files.
python-docx unpacks that ZIP and parses the XML for us.

Interview talking point:
"I extract text from both paragraphs AND tables in Word documents —
most parsers only handle paragraphs, which means they miss all the
structured data that lives in tables like financial reports or resumes."
"""

from pathlib import Path
from typing import Any

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.services.parsers.base_parser import BaseParser, ParseResult


class DocxParser(BaseParser):
    """
    Extracts text from Word documents.
    Handles: paragraphs, headings, tables, lists, headers, footers.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".docx", ".doc"]

    @property
    def parser_name(self) -> str:
        return "DOCX Parser (python-docx)"

    def extract_text(self, file_path: Path) -> ParseResult:
        """
        Extract all text from a Word document in reading order.

        Word documents have a concept of "body elements" which include
        both paragraphs and tables in the order they appear in the doc.
        We iterate these in order to preserve document structure.
        """
        warnings: list[str] = []
        text_parts: list[str] = []

        try:
            doc = Document(str(file_path))

            # ── Extract document properties (metadata) ──────────────────────
            props = doc.core_properties
            if props.title:
                text_parts.append(f"Title: {props.title}\n")
            if props.author:
                text_parts.append(f"Author: {props.author}\n")

            # ── Extract body content in reading order ───────────────────────
            # doc.element.body contains both paragraphs and tables
            # iterating it gives us elements in document order
            for element in doc.element.body:
                tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

                if tag == "p":
                    # It's a paragraph
                    para = Paragraph(element, doc)
                    para_text = para.text.strip()
                    if para_text:
                        # Detect headings and format them
                        if para.style.name.startswith("Heading"):
                            level = para.style.name.replace("Heading ", "")
                            prefix = "#" * int(level) if level.isdigit() else "##"
                            text_parts.append(f"\n{prefix} {para_text}\n")
                        else:
                            text_parts.append(para_text)

                elif tag == "tbl":
                    # It's a table — extract as formatted text
                    table = Table(element, doc)
                    table_text = self._extract_table(table)
                    if table_text:
                        text_parts.append(f"\n[TABLE]\n{table_text}\n[/TABLE]\n")

            # ── Extract headers and footers ─────────────────────────────────
            for section in doc.sections:
                header_text = self._extract_header_footer(section.header)
                footer_text = self._extract_header_footer(section.footer)
                if header_text:
                    text_parts.insert(0, f"[HEADER: {header_text}]\n")
                if footer_text:
                    text_parts.append(f"\n[FOOTER: {footer_text}]")

            full_text = "\n".join(text_parts)

            if not full_text.strip():
                warnings.append("No text found in this Word document.")

            return ParseResult(
                text=full_text,
                page_count=0,  # python-docx doesn't give page count easily
                pages=[full_text],  # Treat as single "page"
                warnings=warnings,
            )

        except Exception as e:
            raise RuntimeError(f"DOCX parsing failed: {e}") from e

    def _extract_table(self, table: Table) -> str:
        """
        Convert a Word table to a readable text format.
        Each row becomes a line, cells separated by ' | '.
        First row is treated as header.
        """
        rows = []
        for i, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]
            # Remove duplicate cells (Word sometimes merges cells)
            cells = list(dict.fromkeys(cells))
            row_text = " | ".join(cells)
            rows.append(row_text)
            # Add separator after header row
            if i == 0:
                rows.append("-" * len(row_text))
        return "\n".join(rows)

    def _extract_header_footer(self, header_footer: Any) -> str:
        """Extract text from a document header or footer."""
        try:
            texts = [para.text.strip() for para in header_footer.paragraphs]
            return " ".join(t for t in texts if t)
        except Exception:
            return ""
