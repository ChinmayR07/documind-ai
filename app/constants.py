"""
DocuMind AI — Application Constants
=====================================
All magic strings, error messages, and fixed values live here.
Never scatter string literals through your codebase — if you need
to change an error message, you change it in ONE place.
"""

from enum import Enum


# ─── Document Types ───────────────────────────────────────────────────────────
class DocumentType(str, Enum):
    """
    Supported document types.
    Inherits from str so it serializes cleanly to JSON.
    """

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    IMAGE = "image"

    @classmethod
    def from_extension(cls, ext: str) -> "DocumentType":
        """Map a file extension to a DocumentType."""
        ext = ext.lower().lstrip(".")
        mapping = {
            "pdf": cls.PDF,
            "docx": cls.DOCX,
            "doc": cls.DOCX,
            "txt": cls.TXT,
            "jpg": cls.IMAGE,
            "jpeg": cls.IMAGE,
            "png": cls.IMAGE,
            "tiff": cls.IMAGE,
            "tif": cls.IMAGE,
            "webp": cls.IMAGE,
            "bmp": cls.IMAGE,
        }
        if ext not in mapping:
            raise ValueError(f"Unsupported file extension: .{ext}")
        return mapping[ext]


# ─── Analysis Types ───────────────────────────────────────────────────────────
class AnalysisType(str, Enum):
    """Types of AI analysis DocuMind can perform."""

    QA = "qa"  # Question & Answer
    SUMMARIZE = "summarize"  # Document summarization
    COMPARE = "compare"  # Multi-document comparison
    INSIGHTS = "insights"  # Key insights extraction


# ─── Document Status ──────────────────────────────────────────────────────────
class DocumentStatus(str, Enum):
    """Lifecycle status of an uploaded document."""

    PROCESSING = "processing"  # Being parsed / text extracted
    READY = "ready"  # Parsed successfully, ready for AI analysis
    FAILED = "failed"  # Parsing failed


# ─── Cache Key Prefixes ───────────────────────────────────────────────────────
# Using prefixes prevents key collisions in Redis
class CacheKeys:
    DOCUMENT = "doc:"  # doc:{document_id} → document metadata
    DOCUMENT_TEXT = "doc:text:"  # doc:text:{document_id} → extracted text
    ANALYSIS = "analysis:"  # analysis:{doc_id}:{hash} → AI response


# ─── API Response Messages ────────────────────────────────────────────────────
class Messages:
    # Success
    DOCUMENT_UPLOADED = "Document uploaded and processed successfully"
    DOCUMENT_DELETED = "Document deleted successfully"
    ANALYSIS_COMPLETE = "Analysis completed successfully"

    # Errors
    DOCUMENT_NOT_FOUND = "Document not found"
    FILE_TOO_LARGE = "File size exceeds the maximum allowed limit"
    UNSUPPORTED_TYPE = "File type not supported"
    PARSE_FAILED = "Failed to extract text from document"
    AI_ERROR = "AI analysis failed. Please try again"
    CACHE_ERROR = "Cache error — proceeding without cache"
    COMPARE_MIN_DOCS = "At least 2 documents are required for comparison"
    COMPARE_MAX_DOCS = "Maximum 3 documents can be compared at once"
    EMPTY_DOCUMENT = "No text could be extracted from this document"


# ─── Claude Prompt Templates ──────────────────────────────────────────────────
# Keeping prompts here makes them easy to iterate and version control
class Prompts:
    QA_SYSTEM = """You are DocuMind AI, an expert document analyst.
You answer questions based ONLY on the content of the provided document.
Be precise, cite relevant sections, and indicate page numbers when available.
If the answer cannot be found in the document, say so clearly — do not hallucinate."""

    QA_USER = """Document content:
{document_text}

---
Question: {question}

Please answer based on the document content above. If you reference specific
sections, mention where in the document you found the information."""

    SUMMARIZE_SYSTEM = """You are DocuMind AI, an expert document analyst.
Create comprehensive yet concise summaries that capture the essential information."""

    SUMMARIZE_USER = """Please analyze this document and provide:

1. **Executive Summary** (2-3 sentences capturing the core message)
2. **Key Points** (5-7 most important points as bullet points)
3. **Key Entities** (important people, organizations, dates, numbers mentioned)
4. **Document Type** (what kind of document is this — report, contract, article, etc.)
5. **Recommended Action** (what should the reader do with this information?)

Document content:
{document_text}"""

    COMPARE_SYSTEM = """You are DocuMind AI, an expert document analyst specializing
in comparative analysis. Provide structured, objective comparisons."""

    COMPARE_USER = """Compare the following {num_docs} documents:

{documents_section}

Provide a detailed comparison covering:

1. **Overview** — Brief description of each document
2. **Common Themes** — What topics/themes appear across all documents?
3. **Key Differences** — Most significant differences between the documents
4. **Unique Insights** — What does each document offer that the others don't?
5. **Contradictions** — Any conflicting information between documents?
6. **Synthesis** — What conclusions can be drawn from reading all documents together?"""


# ─── Limits ───────────────────────────────────────────────────────────────────
class Limits:
    # Text limits — Claude has a context window, so we chunk large documents
    MAX_TEXT_CHARS_FOR_CLAUDE = 180_000  # ~45K tokens — safe limit for claude-sonnet-4-20250514
    MAX_QUESTION_LENGTH = 1_000  # Characters
    MAX_DOCUMENTS_TO_COMPARE = 3
    MIN_DOCUMENTS_TO_COMPARE = 2

    # API limits
    MAX_DOCUMENTS_PER_USER = 50  # Max stored documents
    MAX_REQUESTS_PER_MINUTE = 20  # Rate limiting (future)
