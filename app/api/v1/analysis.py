"""
DocuMind AI — Analysis Routes
===============================
AI-powered analysis endpoints:
- POST /documents/{id}/ask       — Q&A on a document
- POST /documents/{id}/summarize — Summarize a document
- POST /documents/compare        — Compare multiple documents

These are the most interesting endpoints — they call Claude and
return structured AI responses.

FastAPI patterns used:
- Path parameters: /documents/{document_id}/ask
- Request body: validated via Pydantic models
- Background tasks: could be used for async processing
- Response models: typed responses with auto Swagger docs
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.constants import Limits, Messages
from app.models.schemas import (
    AskRequest,
    AskResponse,
    CompareRequest,
    DocumentComparison,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services.document_service import document_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Analysis"],
)


# ─── Q&A ──────────────────────────────────────────────────────────────────────


@router.post(
    "/{document_id}/ask",
    response_model=AskResponse,
    summary="Ask a question about a document",
    description="""
Ask any natural language question about an uploaded document.
Claude AI will analyze the document content and provide a precise answer.

Examples:
- "What are the main conclusions of this report?"
- "Who are the key stakeholders mentioned?"
- "What is the total revenue for Q3?"
- "Summarize the risks identified in section 3"

The answer includes page references when available.
    """,
    responses={
        200: {"description": "Question answered successfully"},
        404: {"description": "Document not found"},
        422: {"description": "Invalid request"},
        500: {"description": "AI analysis failed"},
    },
)
async def ask_question(
    document_id: str,
    request: AskRequest,
) -> AskResponse:
    """
    Answer a question about a specific document using Claude AI.

    The document must be uploaded first via POST /documents/upload.
    Use the document_id returned from the upload endpoint.
    """
    try:
        result = document_service.ask_question(
            document_id=document_id,
            question=request.question,
            include_page_references=request.include_page_references,
        )
        return result

    except ValueError as e:
        error_msg = str(e)
        # Document not found
        if Messages.DOCUMENT_NOT_FOUND in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        # Empty document
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg,
        ) from e
    except RuntimeError as e:
        logger.error(f"Q&A failed for doc {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{Messages.AI_ERROR}: {e}",
        ) from e


# ─── Summarize ────────────────────────────────────────────────────────────────


@router.post(
    "/{document_id}/summarize",
    response_model=SummarizeResponse,
    summary="Summarize a document",
    description="""
Generate a structured AI summary of an uploaded document.

Returns:
- **Executive summary** — 2-5 sentence overview
- **Key points** — 5-10 most important bullet points
- **Key entities** — people, organizations, dates, numbers mentioned
- **Document type** — what kind of document it is
- **Recommended action** — what the reader should do next

Use `max_length` to control summary detail level:
- `short` — 2 sentences + 3 key points
- `medium` — 3-4 sentences + 5-7 key points (default)
- `long` — 5-6 sentences + 8-10 key points
    """,
    responses={
        200: {"description": "Summary generated successfully"},
        404: {"description": "Document not found"},
        500: {"description": "AI analysis failed"},
    },
)
async def summarize_document(
    document_id: str,
    request: SummarizeRequest,
) -> SummarizeResponse:
    """Generate a structured AI summary of a document."""
    try:
        result = document_service.summarize_document(
            document_id=document_id,
            max_length=request.max_length,
            focus_areas=request.focus_areas,
        )
        return result

    except ValueError as e:
        error_msg = str(e)
        if Messages.DOCUMENT_NOT_FOUND in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg,
        ) from e
    except RuntimeError as e:
        logger.error(f"Summarize failed for doc {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{Messages.AI_ERROR}: {e}",
        ) from e


# ─── Compare ──────────────────────────────────────────────────────────────────


@router.post(
    "/compare",
    response_model=DocumentComparison,
    summary="Compare multiple documents",
    description=f"""
Compare 2-3 uploaded documents side by side using Claude AI.

Provides:
- **Overview** — brief description of each document
- **Common themes** — topics appearing across all documents
- **Key differences** — most significant differences
- **Unique insights** — what each document uniquely offers
- **Contradictions** — conflicting information between documents
- **Synthesis** — overall conclusion from reading all together

Limits:
- Minimum: {Limits.MIN_DOCUMENTS_TO_COMPARE} documents
- Maximum: {Limits.MAX_DOCUMENTS_TO_COMPARE} documents
- All documents must be uploaded first

Use `comparison_focus` to direct the analysis:
e.g. "financial performance", "risk factors", "technical approach"
    """,
    responses={
        200: {"description": "Comparison completed successfully"},
        400: {"description": "Invalid document IDs or comparison request"},
        404: {"description": "One or more documents not found"},
        500: {"description": "AI analysis failed"},
    },
)
async def compare_documents(
    request: CompareRequest,
) -> DocumentComparison:
    """
    Compare 2-3 documents using Claude AI.

    Note: This endpoint does NOT have a document_id path parameter
    because it operates on multiple documents.
    The document IDs are passed in the request body.
    """
    # Validate document count
    if len(request.document_ids) < Limits.MIN_DOCUMENTS_TO_COMPARE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Messages.COMPARE_MIN_DOCS,
        )
    if len(request.document_ids) > Limits.MAX_DOCUMENTS_TO_COMPARE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Messages.COMPARE_MAX_DOCS,
        )

    try:
        result = document_service.compare_documents(
            document_ids=request.document_ids,
            comparison_focus=request.comparison_focus,
        )
        return result

    except ValueError as e:
        error_msg = str(e)
        if Messages.DOCUMENT_NOT_FOUND in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        ) from e
    except RuntimeError as e:
        logger.error(f"Compare failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{Messages.AI_ERROR}: {e}",
        ) from e
