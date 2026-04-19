"""
DocuMind AI — API v1 Router
=============================
Combines all route groups into a single router.
This is imported by main.py and mounted at /api/v1.

Why a separate router file?
As the API grows, you add more route files (auth.py, webhooks.py, etc.)
and register them here — main.py never needs to change.
This is the same pattern used by FastAPI's own documentation.

Full API surface:
  GET    /api/v1/health
  GET    /api/v1/

  POST   /api/v1/documents/upload
  GET    /api/v1/documents/
  GET    /api/v1/documents/{id}
  GET    /api/v1/documents/{id}/download
  DELETE /api/v1/documents/{id}

  POST   /api/v1/documents/{id}/ask
  POST   /api/v1/documents/{id}/summarize
  POST   /api/v1/documents/compare
"""

from fastapi import APIRouter

from app.api.v1 import analysis, documents

# Parent router for all v1 endpoints
api_router = APIRouter()

# Register document management routes
api_router.include_router(documents.router)

# Register analysis routes
# Note: same prefix "/documents" but different tags in Swagger
api_router.include_router(analysis.router)
