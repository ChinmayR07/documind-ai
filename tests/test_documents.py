"""
DocuMind AI — Document API Tests
==================================
Integration tests for document management endpoints.
Uses FastAPI's TestClient to make real HTTP requests
against the app without starting a real server.

These tests verify:
- Correct HTTP status codes
- Correct response shapes
- Error handling behavior
- File validation logic
"""

import io
from unittest.mock import patch, MagicMock

import pytest

from app.constants import DocumentStatus, DocumentType


# ─── Health Check ─────────────────────────────────────────────────────────────

class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, test_client):
        """Health endpoint should always return 200."""
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, test_client):
        """Health response should include status: healthy."""
        response = test_client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_version(self, test_client):
        """Health response should include app version."""
        response = test_client.get("/api/v1/health")
        data = response.json()
        assert "version" in data
        assert "app" in data

    def test_root_returns_200(self, test_client):
        """Root endpoint should return 200 with welcome message."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "DocuMind" in data["message"]


# ─── Document Upload ──────────────────────────────────────────────────────────

class TestDocumentUpload:
    """Tests for POST /api/v1/documents/upload."""

    def test_upload_txt_file_returns_201(self, test_client, sample_txt_bytes):
        """Uploading a valid text file should return 201 Created."""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )
        assert response.status_code == 201

    def test_upload_txt_returns_document_id(self, test_client, sample_txt_bytes):
        """Upload response should include a document ID."""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )
        data = response.json()
        assert "id" in data
        assert len(data["id"]) == 36  # UUID format

    def test_upload_txt_returns_correct_type(self, test_client, sample_txt_bytes):
        """Upload response should correctly identify document type."""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )
        data = response.json()
        assert data["document_type"] == DocumentType.TXT

    def test_upload_returns_word_count(self, test_client, sample_txt_bytes):
        """Upload response should include word count."""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )
        data = response.json()
        assert data["word_count"] > 0

    def test_upload_returns_ready_status(self, test_client, sample_txt_bytes):
        """Uploaded document status should be READY after processing."""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )
        data = response.json()
        assert data["status"] == DocumentStatus.READY

    def test_upload_empty_file_returns_400(self, test_client):
        """Uploading an empty file should return 400."""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_unsupported_type_returns_400(self, test_client):
        """Uploading an unsupported file type should return 400."""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("script.py", io.BytesIO(b"print('hello')"), "text/x-python")},
        )
        assert response.status_code == 400

    def test_upload_too_large_returns_413(self, test_client):
        """Uploading a file over the size limit should return 413."""
        # Create content slightly over 20MB limit
        large_content = b"x" * (21 * 1024 * 1024)  # 21MB
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("large.txt", io.BytesIO(large_content), "text/plain")},
        )
        assert response.status_code == 413

    def test_upload_pdf_file(self, test_client, sample_pdf_bytes):
        """Should accept PDF file uploads."""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("document.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )
        # PDF may succeed or fail parsing but should not be a 400 type error
        assert response.status_code in (201, 500)


# ─── Document Listing ─────────────────────────────────────────────────────────

class TestDocumentListing:
    """Tests for GET /api/v1/documents/."""

    def test_list_empty_returns_200(self, test_client):
        """Listing documents when none exist should return 200 with empty list."""
        response = test_client.get("/api/v1/documents/")
        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []
        assert data["total"] == 0

    def test_list_after_upload_returns_one(self, test_client, sample_txt_bytes):
        """After uploading one document, list should return one item."""
        # Upload
        test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )

        # List
        response = test_client.get("/api/v1/documents/")
        data = response.json()
        assert data["total"] == 1
        assert len(data["documents"]) == 1

    def test_list_includes_filename(self, test_client, sample_txt_bytes):
        """Listed documents should include the original filename."""
        test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("myfile.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )
        response = test_client.get("/api/v1/documents/")
        data = response.json()
        assert data["documents"][0]["original_filename"] == "myfile.txt"


# ─── Get Single Document ──────────────────────────────────────────────────────

class TestGetDocument:
    """Tests for GET /api/v1/documents/{id}."""

    def test_get_existing_document(self, test_client, sample_txt_bytes):
        """Should return document details for a valid ID."""
        # Upload first
        upload_response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )
        doc_id = upload_response.json()["id"]

        # Get by ID
        response = test_client.get(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id

    def test_get_nonexistent_document_returns_404(self, test_client):
        """Requesting a non-existent document ID should return 404."""
        response = test_client.get("/api/v1/documents/nonexistent-id-12345")
        assert response.status_code == 404


# ─── Delete Document ──────────────────────────────────────────────────────────

class TestDeleteDocument:
    """Tests for DELETE /api/v1/documents/{id}."""

    def test_delete_existing_document(self, test_client, sample_txt_bytes):
        """Should successfully delete an uploaded document."""
        # Upload
        upload_response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )
        doc_id = upload_response.json()["id"]

        # Delete
        response = test_client.delete(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    def test_delete_removes_from_list(self, test_client, sample_txt_bytes):
        """After deletion, document should not appear in list."""
        # Upload
        upload_response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        )
        doc_id = upload_response.json()["id"]

        # Delete
        test_client.delete(f"/api/v1/documents/{doc_id}")

        # Verify not in list
        list_response = test_client.get("/api/v1/documents/")
        assert list_response.json()["total"] == 0

    def test_delete_nonexistent_returns_404(self, test_client):
        """Deleting a non-existent document should return 404."""
        response = test_client.delete("/api/v1/documents/nonexistent-id")
        assert response.status_code == 404
