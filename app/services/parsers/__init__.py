from app.services.parsers.base_parser import BaseParser, ParseResult
from app.services.parsers.docx_parser import DocxParser
from app.services.parsers.ocr_parser import ImageParser
from app.services.parsers.pdf_parser import PDFParser
from app.services.parsers.txt_parser import TextParser

# Backwards-compatible aliases for older import paths.
DOCXParser = DocxParser
TXTParser = TextParser
OCRParser = ImageParser

__all__ = [
    "BaseParser",
    "ParseResult",
    "PDFParser",
    "DocxParser",
    "TextParser",
    "ImageParser",
    "DOCXParser",
    "TXTParser",
    "OCRParser",
]
