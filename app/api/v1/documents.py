"""
DocuMind AI — Document Routes
===============================
Handles document upload, listing, retrieval, and deletion.

FastAPI concepts used here:
- UploadFile: FastAPI's file upload handler
- Depends(): dependency injection for shared resources
- HTTPException: raises proper HTTP error responses
- status codes: 200, 201, 404, 413, 422, 500
- Response model: ensures response shape matches schema exactly

Interview talking point:
"I used FastAPI's dependency injection system to share service
instances across routes — it's cleaner than global imports and
makes unit testing much easier since you can inject mock services."
"""

import logging
from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.config import Settings, get_settings
from app.constants import Messages
from app.models.schemas import (
    DeleteResponse,
    DocumentListResponse,
    DocumentRecord,
    DocumentUploadResponse,
)
from app.services.document_service import document_service

logger = logging.getLogger(__name__)

# Create router — all routes here get /api/v1/documents prefix
router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description="""
Upload a document for AI analysis. Supported formats:
- **PDF** (.pdf) — text-based and mixed PDFs
- **Word** (.docx) — including tables, headings, headers/footers
- **Text** (.txt) — with automatic encoding detection
- **Images** (.jpg, .png, .tiff, .webp, .bmp) — OCR text extraction

The document is processed immediately and text is extracted.
Returns a `document_id` to use for subsequent analysis requests.
    """,
    responses={
        201: {"description": "Document uploaded and processed successfully"},
        400: {"description": "Invalid file type"},
        413: {"description": "File too large"},
        422: {"description": "Validation error"},
        500: {"description": "Processing failed"},
    },
)
async def upload_document(
    file: UploadFile = File(
        ...,
        description="Document file to upload and analyze",
    ),
    settings: Settings = Depends(get_settings),
) -> DocumentUploadResponse:
    """
    Upload and process a document.

    FastAPI's UploadFile gives us:
    - file.filename: original filename
    - file.content_type: MIME type
    - file.read(): async file content reading
    - file.size: file size in bytes (may be None for some clients)
    """
    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate before processing
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if file_size > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
                f"maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
            ),
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    try:
        result = document_service.upload_document(
            file_content=content,
            original_filename=file.filename,
            file_size=file_size,
        )
        return result

    except ValueError as e:
        # Validation errors (bad file type, size, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        # Processing errors (parse failed, etc.)
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


# ─── List Documents ───────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List all documents",
    description="Returns all uploaded documents sorted by most recent first.",
)
async def list_documents() -> DocumentListResponse:
    """List all uploaded documents."""
    docs = document_service.list_documents()

    # Convert internal dicts to response models
    # Filter out internal fields (prefixed with _)
    document_records = [
        DocumentRecord(
            id=doc["id"],
            original_filename=doc["original_filename"],
            document_type=doc["document_type"],
            file_size_mb=doc["file_size_mb"],
            status=doc["status"],
            created_at=cast(datetime, doc.get("created_at") or datetime.utcnow()),
            page_count=doc.get("page_count", 0),
            word_count=doc.get("word_count", 0),
            char_count=doc.get("char_count", 0),
            warnings=doc.get("warnings", []),
        )
        for doc in docs
    ]

    return DocumentListResponse(
        documents=document_records,
        total=len(document_records),
    )


# ─── Get Single Document ──────────────────────────────────────────────────────

@router.get(
    "/{document_id}",
    response_model=DocumentRecord,
    summary="Get document details",
    description="Returns metadata for a specific document by ID.",
    responses={
        404: {"description": "Document not found"},
    },
)
async def get_document(document_id: str) -> DocumentRecord:
    """Get a single document's metadata by ID."""
    try:
        doc = document_service.get_document(document_id)
        return DocumentRecord(
            id=doc["id"],
            original_filename=doc["original_filename"],
            document_type=doc["document_type"],
            file_size_mb=doc["file_size_mb"],
            status=doc["status"],
            created_at=cast(datetime, doc.get("created_at") or datetime.utcnow()),
            page_count=doc.get("page_count", 0),
            word_count=doc.get("word_count", 0),
            char_count=doc.get("char_count", 0),
            warnings=doc.get("warnings", []),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        ) from e


# ─── Download Document ────────────────────────────────────────────────────────

@router.get(
    "/{document_id}/download",
    summary="Download original document",
    description="Download the original uploaded document file.",
    responses={
        200: {"description": "File download"},
        404: {"description": "Document not found"},
    },
)
async def download_document(document_id: str) -> FileResponse:
    """Download the original uploaded document."""
    try:
        doc = document_service.get_document(document_id)
        from pathlib import Path
        file_path = Path(doc["file_path"])

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk.",
            )

        return FileResponse(
            path=str(file_path),
            filename=doc["original_filename"],
            media_type="application/octet-stream",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        ) from e


# ─── Delete Document ──────────────────────────────────────────────────────────

@router.delete(
    "/{document_id}",
    response_model=DeleteResponse,
    summary="Delete a document",
    description="Permanently deletes a document and its extracted text.",
    responses={
        200: {"description": "Document deleted successfully"},
        404: {"description": "Document not found"},
    },
)
async def delete_document(document_id: str) -> DeleteResponse:
    """Delete a document by ID."""
    try:
        document_service.delete_document(document_id)
        return DeleteResponse(
            id=document_id,
            message=Messages.DOCUMENT_DELETED,
            deleted=True,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        ) from e
