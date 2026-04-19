"""
DocuMind AI — Document Service
================================
Orchestrates the full document lifecycle:
  Upload → Validate → Store → Parse → Cache → Serve

This is the "use case" layer — it coordinates between
the parser service, claude service, and cache service.
Think of it as the conductor of an orchestra.

Design Pattern: Facade
- Provides a simple interface to a complex subsystem
- Callers (API routes) don't need to know about parsers, caching,
  file storage — they just call document_service.upload() and get a result
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.constants import DocumentStatus, Messages
from app.models.schemas import (
    AskResponse,
    DocumentComparison,
    DocumentUploadResponse,
    SummarizeResponse,
)
from app.services.claude_service import claude_service
from app.services.parser_service import parser_service
from app.utils.file_utils import (
    delete_file_safely,
    generate_safe_filename,
    get_file_size_mb,
    validate_file_extension,
    validate_file_size,
)

logger = logging.getLogger(__name__)

# In-memory document store
# In production: replace with PostgreSQL / DynamoDB / MongoDB
# Using a dict here keeps the project dependency-free for demos
_document_store: dict[str, dict] = {}


class DocumentService:
    """
    Orchestrates document upload, storage, parsing, and AI analysis.
    Acts as the single entry point for all document operations.
    """

    # ─── Upload & Process ─────────────────────────────────────────────────────

    def upload_document(
        self,
        file_content: bytes,
        original_filename: str,
        file_size: int,
    ) -> DocumentUploadResponse:
        """
        Handle a document upload end-to-end:
        1. Validate file (size, type)
        2. Generate safe filename and store to disk
        3. Parse document (extract text)
        4. Store metadata in memory
        5. Return response

        Raises:
            ValueError: If file validation fails (size, type)
            RuntimeError: If parsing fails
        """
        # ── Step 1: Validate ───────────────────────────────────────────────
        validate_file_size(file_size)
        validate_file_extension(original_filename)

        # ── Step 2: Store file ─────────────────────────────────────────────
        document_id = str(uuid.uuid4())
        safe_filename = generate_safe_filename(original_filename)
        file_path = settings.UPLOAD_PATH / safe_filename

        # Write file to disk
        file_path.write_bytes(file_content)
        logger.info(f"File stored: {safe_filename} ({file_size / 1024:.1f}KB)")

        try:
            # ── Step 3: Parse document ─────────────────────────────────────
            parse_result = parser_service.parse_document(file_path)
            doc_type = parser_service.get_document_type(file_path)

            if parse_result.is_empty:
                logger.warning(f"Empty document: {original_filename}")

            # ── Step 4: Store metadata ─────────────────────────────────────
            _document_store[document_id] = {
                "id": document_id,
                "original_filename": original_filename,
                "stored_filename": safe_filename,
                "file_path": str(file_path),
                "document_type": doc_type,
                "file_size_mb": get_file_size_mb(file_path),
                "status": DocumentStatus.READY,
                "created_at": datetime.utcnow(),
                "page_count": parse_result.page_count,
                "word_count": parse_result.word_count,
                "char_count": parse_result.char_count,
                "warnings": parse_result.warnings,
                # Store extracted text for AI analysis
                "_extracted_text": parse_result.text,
            }

            logger.info(
                f"Document processed: id={document_id[:8]}, "
                f"type={doc_type}, "
                f"words={parse_result.word_count:,}"
            )

            # ── Step 5: Return response ────────────────────────────────────
            return DocumentUploadResponse(
                id=document_id,
                filename=original_filename,
                document_type=doc_type,
                file_size_mb=get_file_size_mb(file_path),
                status=DocumentStatus.READY,
                page_count=parse_result.page_count,
                word_count=parse_result.word_count,
                char_count=parse_result.char_count,
                warnings=parse_result.warnings,
                message=Messages.DOCUMENT_UPLOADED,
            )

        except Exception as e:
            # Clean up stored file if processing fails
            delete_file_safely(file_path)
            logger.error(f"Document processing failed: {e}")
            raise RuntimeError(f"Failed to process document: {e}") from e

    # ─── Retrieval ────────────────────────────────────────────────────────────

    def get_document(self, document_id: str) -> dict:
        """
        Retrieve a document record by ID.
        Raises ValueError if not found.
        """
        doc = _document_store.get(document_id)
        if not doc:
            raise ValueError(f"{Messages.DOCUMENT_NOT_FOUND}: {document_id}")
        return doc

    def list_documents(self) -> list[dict]:
        """Return all documents sorted by most recently added."""
        return list(reversed(list(_document_store.values())))

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document record and its file from disk.
        Returns True if deleted successfully.
        """
        doc = self.get_document(document_id)

        # Delete file from disk
        file_path = Path(doc["file_path"])
        delete_file_safely(file_path)

        # Remove from store
        del _document_store[document_id]

        logger.info(f"Document deleted: id={document_id[:8]}")
        return True

    def get_document_text(self, document_id: str) -> str:
        """
        Get extracted text for a document.
        Used by analysis methods.
        """
        doc = self.get_document(document_id)
        text = doc.get("_extracted_text", "")

        if not text:
            raise ValueError(
                f"No text available for document {document_id}. "
                "The document may be empty or failed to parse."
            )
        return text

    # ─── AI Analysis ─────────────────────────────────────────────────────────

    def ask_question(
        self,
        document_id: str,
        question: str,
        include_page_references: bool = True,
    ) -> AskResponse:
        """
        Answer a question about a specific document.
        Retrieves text → calls Claude → returns structured response.
        """
        text = self.get_document_text(document_id)

        logger.info(f"Q&A: doc={document_id[:8]}, " f"q='{question[:50]}...'")

        return claude_service.ask_question(
            document_text=text,
            document_id=document_id,
            question=question,
            include_page_references=include_page_references,
        )

    def summarize_document(
        self,
        document_id: str,
        max_length: str = "medium",
        focus_areas: list[str] | None = None,
    ) -> SummarizeResponse:
        """Generate an AI summary of a document."""
        text = self.get_document_text(document_id)

        logger.info(f"Summarize: doc={document_id[:8]}, length={max_length}")

        return claude_service.summarize_document(
            document_text=text,
            document_id=document_id,
            max_length=max_length,
            focus_areas=focus_areas or [],
        )

    def compare_documents(
        self,
        document_ids: list[str],
        comparison_focus: str = "",
    ) -> DocumentComparison:
        """
        Compare 2-3 documents side by side using Claude.
        Fetches text for each document, then calls Claude comparison.
        """
        # Fetch text for all documents
        documents = []
        for doc_id in document_ids:
            text = self.get_document_text(doc_id)
            doc_meta = self.get_document(doc_id)
            documents.append(
                {
                    "id": doc_id,
                    "text": text,
                    "filename": doc_meta["original_filename"],
                }
            )

        logger.info(
            f"Compare: {len(documents)} documents, " f"ids={[d['id'][:8] for d in documents]}"
        )

        return claude_service.compare_documents(
            documents=documents,
            comparison_focus=comparison_focus,
        )


# ─── Singleton instance ────────────────────────────────────────────────────────
document_service = DocumentService()
