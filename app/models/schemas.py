"""
DocuMind AI — Data Models
===========================
All Pydantic models for API requests and responses.

Why Pydantic?
- Automatic validation: if a field is wrong type, FastAPI returns a clear 422 error
- Automatic serialization: models serialize to/from JSON automatically
- Self-documenting: FastAPI uses these to generate the Swagger UI automatically
- Type safety: mypy can catch bugs at development time, not runtime

Interview talking point:
"I used Pydantic v2 models throughout — they give me runtime type validation,
automatic OpenAPI schema generation, and serve as living documentation
for the API contract."
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.constants import AnalysisType, DocumentStatus, DocumentType

# ─── Document Models ──────────────────────────────────────────────────────────


class DocumentBase(BaseModel):
    """Shared fields across document models."""

    original_filename: str
    document_type: DocumentType
    file_size_mb: float


class DocumentCreate(DocumentBase):
    """Internal model used when creating a document record."""

    id: str
    stored_filename: str
    file_path: str
    status: DocumentStatus = DocumentStatus.PROCESSING
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentRecord(DocumentBase):
    """
    Full document record returned by the API.
    This is what clients see when they list or get a document.
    """

    id: str
    status: DocumentStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Extracted content stats
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    warnings: list[str] = []

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Response for listing all documents."""

    documents: list[DocumentRecord]
    total: int


class DocumentUploadResponse(BaseModel):
    """Response immediately after a successful upload."""

    id: str
    filename: str
    document_type: DocumentType
    file_size_mb: float
    status: DocumentStatus
    page_count: int
    word_count: int
    char_count: int
    warnings: list[str] = []
    message: str


class DeleteResponse(BaseModel):
    """Response for document deletion."""

    id: str
    message: str
    deleted: bool


# ─── Analysis Request Models ──────────────────────────────────────────────────


class AskRequest(BaseModel):
    """
    Request body for asking a question about a document.
    The document_id comes from the URL path, not the body.
    """

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The question to ask about the document",
        examples=["What are the main conclusions of this report?"],
    )
    # Optional: include page context in the answer
    include_page_references: bool = Field(
        default=True,
        description="Whether to include page number references in the answer",
    )

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question cannot be empty or only whitespace")
        return v.strip()


class SummarizeRequest(BaseModel):
    """Request body for document summarization."""

    max_length: str = Field(
        default="medium",
        description="Summary length: 'short' (1 para), 'medium' (5-7 points), 'long' (detailed)",
        pattern="^(short|medium|long)$",
    )
    focus_areas: list[str] = Field(
        default=[],
        max_length=5,
        description="Optional: specific areas to focus on e.g. ['financial data', 'risks']",
    )


class CompareRequest(BaseModel):
    """
    Request body for comparing multiple documents.
    Document IDs to compare are passed in the body.
    """

    document_ids: list[str] = Field(
        ...,
        min_length=2,
        max_length=3,
        description="List of 2-3 document IDs to compare",
    )
    comparison_focus: str = Field(
        default="",
        max_length=500,
        description="Optional: specific aspect to focus comparison on",
    )

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("Document IDs must be unique — cannot compare a document with itself")
        return v


# ─── Analysis Response Models ─────────────────────────────────────────────────


class AskResponse(BaseModel):
    """Response from Q&A analysis."""

    document_id: str
    question: str
    answer: str
    # How many characters of the document were used as context
    context_chars_used: int
    # Whether this result came from cache
    cached: bool = False
    # Approximate tokens used (for cost awareness)
    tokens_used_approx: int = 0
    analysis_type: AnalysisType = AnalysisType.QA


class KeyInsight(BaseModel):
    """A single key insight extracted from a document."""

    insight: str
    category: str = ""  # e.g. "Financial", "Risk", "Recommendation"
    importance: str = "medium"  # "high", "medium", "low"


class SummarizeResponse(BaseModel):
    """Response from summarization analysis."""

    document_id: str
    executive_summary: str
    key_points: list[str]
    key_entities: list[str]
    document_type_detected: str
    recommended_action: str
    word_count_original: int
    word_count_summary: int
    cached: bool = False
    analysis_type: AnalysisType = AnalysisType.SUMMARIZE


class DocumentComparison(BaseModel):
    """Result of comparing multiple documents."""

    document_ids: list[str]
    num_documents: int
    overview: str
    common_themes: list[str]
    key_differences: list[str]
    unique_insights: dict[str, str]  # document_id → unique insight
    contradictions: list[str]
    synthesis: str
    cached: bool = False
    analysis_type: AnalysisType = AnalysisType.COMPARE


# ─── Error Models ─────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standard error response shape."""

    error: str
    detail: str = ""
    code: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    app: str
    version: str
    environment: str
    model: str
    redis: str
