"""
DocuMind AI — Analysis API Tests
===================================
Tests for AI analysis endpoints:
- POST /documents/{id}/ask
- POST /documents/{id}/summarize
- POST /documents/compare

Key technique: Mocking Claude API calls
We use unittest.mock.patch() to replace the _call_claude method
with a fake that returns instantly without hitting the real API.

This is critical for:
1. Speed — tests run in milliseconds, not seconds
2. Cost — no real API credits consumed
3. Reliability — no network dependency
4. Determinism — same input always gives same output

Interview talking point:
"I mocked external dependencies at the service boundary —
patching _call_claude rather than the entire Claude client
gives me control while still testing the real parsing,
prompt construction, and response handling logic."
"""

import io
import json
from unittest.mock import patch

import pytest


def upload_test_document(test_client, content: bytes, filename: str = "test.txt") -> str:
    """Helper: upload a document and return its ID."""
    response = test_client.post(
        "/api/v1/documents/upload",
        files={"file": (filename, io.BytesIO(content), "text/plain")},
    )
    assert response.status_code == 201, f"Upload failed: {response.json()}"
    return response.json()["id"]


# ─── Q&A Tests ────────────────────────────────────────────────────────────────

class TestAskQuestion:
    """Tests for POST /api/v1/documents/{id}/ask."""

    MOCK_ANSWER = (
        "Based on the document, the total revenue exceeded expectations by 15%.",
        400,
    )

    def test_ask_returns_200(self, test_client, sample_txt_bytes):
        """Asking a valid question should return 200."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_ANSWER,
        ):
            response = test_client.post(
                f"/api/v1/documents/{doc_id}/ask",
                json={"question": "What was the total revenue?"},
            )

        assert response.status_code == 200

    def test_ask_returns_answer(self, test_client, sample_txt_bytes):
        """Response should include an answer field with content."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_ANSWER,
        ):
            response = test_client.post(
                f"/api/v1/documents/{doc_id}/ask",
                json={"question": "What was the revenue?"},
            )

        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_ask_echoes_question(self, test_client, sample_txt_bytes):
        """Response should include the original question."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)
        question = "What is the main conclusion?"

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_ANSWER,
        ):
            response = test_client.post(
                f"/api/v1/documents/{doc_id}/ask",
                json={"question": question},
            )

        assert response.json()["question"] == question

    def test_ask_includes_document_id(self, test_client, sample_txt_bytes):
        """Response should include the document_id."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_ANSWER,
        ):
            response = test_client.post(
                f"/api/v1/documents/{doc_id}/ask",
                json={"question": "Test question?"},
            )

        assert response.json()["document_id"] == doc_id

    def test_ask_nonexistent_document_returns_404(self, test_client):
        """Asking about a non-existent document should return 404."""
        response = test_client.post(
            "/api/v1/documents/nonexistent-id/ask",
            json={"question": "What is this?"},
        )
        assert response.status_code == 404

    def test_ask_empty_question_returns_422(self, test_client, sample_txt_bytes):
        """Empty question should return 422 validation error."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        response = test_client.post(
            f"/api/v1/documents/{doc_id}/ask",
            json={"question": ""},
        )
        assert response.status_code == 422

    def test_ask_question_too_long_returns_422(self, test_client, sample_txt_bytes):
        """Question exceeding max length should return 422."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        response = test_client.post(
            f"/api/v1/documents/{doc_id}/ask",
            json={"question": "x" * 1001},  # Over 1000 char limit
        )
        assert response.status_code == 422

    def test_ask_without_page_references(self, test_client, sample_txt_bytes):
        """Should work with include_page_references=False."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_ANSWER,
        ):
            response = test_client.post(
                f"/api/v1/documents/{doc_id}/ask",
                json={
                    "question": "What happened?",
                    "include_page_references": False,
                },
            )

        assert response.status_code == 200


# ─── Summarization Tests ──────────────────────────────────────────────────────

class TestSummarize:
    """Tests for POST /api/v1/documents/{id}/summarize."""

    MOCK_SUMMARY_JSON = json.dumps({
        "executive_summary": "This is a financial document showing strong Q3 performance.",
        "key_points": ["Revenue up 15%", "AI investment recommended", "Q3 was best quarter"],
        "key_entities": ["Q3", "Board", "$1,800,000"],
        "document_type_detected": "Financial Report",
        "recommended_action": "Approve AI investment budget",
    })
    MOCK_RESPONSE = (MOCK_SUMMARY_JSON, 800)

    def test_summarize_returns_200(self, test_client, sample_txt_bytes):
        """Summarization should return 200."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_RESPONSE,
        ):
            response = test_client.post(
                f"/api/v1/documents/{doc_id}/summarize",
                json={"max_length": "medium"},
            )

        assert response.status_code == 200

    def test_summarize_returns_executive_summary(self, test_client, sample_txt_bytes):
        """Response should include executive_summary."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_RESPONSE,
        ):
            response = test_client.post(
                f"/api/v1/documents/{doc_id}/summarize",
                json={"max_length": "medium"},
            )

        data = response.json()
        assert "executive_summary" in data
        assert len(data["executive_summary"]) > 0

    def test_summarize_returns_key_points_list(self, test_client, sample_txt_bytes):
        """Response should include key_points as a list."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_RESPONSE,
        ):
            response = test_client.post(
                f"/api/v1/documents/{doc_id}/summarize",
                json={"max_length": "medium"},
            )

        data = response.json()
        assert "key_points" in data
        assert isinstance(data["key_points"], list)

    def test_summarize_invalid_length_returns_422(self, test_client, sample_txt_bytes):
        """Invalid max_length value should return 422."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        response = test_client.post(
            f"/api/v1/documents/{doc_id}/summarize",
            json={"max_length": "invalid_value"},
        )
        assert response.status_code == 422

    def test_summarize_with_focus_areas(self, test_client, sample_txt_bytes):
        """Should accept optional focus_areas parameter."""
        doc_id = upload_test_document(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_RESPONSE,
        ):
            response = test_client.post(
                f"/api/v1/documents/{doc_id}/summarize",
                json={
                    "max_length": "long",
                    "focus_areas": ["financial data", "risks"],
                },
            )

        assert response.status_code == 200


# ─── Comparison Tests ─────────────────────────────────────────────────────────

class TestCompare:
    """Tests for POST /api/v1/documents/compare."""

    MOCK_COMPARE_JSON = json.dumps({
        "overview": "Two financial documents covering different time periods.",
        "common_themes": ["Revenue", "AI investment", "Growth"],
        "key_differences": ["Different quarters", "Different revenue figures"],
        "unique_insights": {"doc1": "Q1-Q2 data", "doc2": "Q3 data"},
        "contradictions": [],
        "synthesis": "Both show positive trends.",
    })
    MOCK_RESPONSE = (MOCK_COMPARE_JSON, 1200)

    def _upload_two_docs(self, test_client, sample_txt_bytes) -> tuple[str, str]:
        """Helper: upload two documents and return their IDs."""
        id1 = upload_test_document(test_client, sample_txt_bytes, "doc1.txt")
        id2 = upload_test_document(test_client, sample_txt_bytes, "doc2.txt")
        return id1, id2

    def test_compare_two_documents_returns_200(self, test_client, sample_txt_bytes):
        """Comparing two documents should return 200."""
        id1, id2 = self._upload_two_docs(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_RESPONSE,
        ):
            response = test_client.post(
                "/api/v1/documents/compare",
                json={"document_ids": [id1, id2]},
            )

        assert response.status_code == 200

    def test_compare_returns_common_themes(self, test_client, sample_txt_bytes):
        """Comparison response should include common_themes list."""
        id1, id2 = self._upload_two_docs(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_RESPONSE,
        ):
            response = test_client.post(
                "/api/v1/documents/compare",
                json={"document_ids": [id1, id2]},
            )

        data = response.json()
        assert "common_themes" in data
        assert isinstance(data["common_themes"], list)

    def test_compare_returns_synthesis(self, test_client, sample_txt_bytes):
        """Response should include a synthesis."""
        id1, id2 = self._upload_two_docs(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_RESPONSE,
        ):
            response = test_client.post(
                "/api/v1/documents/compare",
                json={"document_ids": [id1, id2]},
            )

        assert len(response.json()["synthesis"]) > 0

    def test_compare_one_document_returns_422(self, test_client, sample_txt_bytes):
        """Comparing only one document should return 400."""
        id1 = upload_test_document(test_client, sample_txt_bytes)

        response = test_client.post(
            "/api/v1/documents/compare",
            json={"document_ids": [id1]},
        )
        assert response.status_code == 422  # Pydantic min_length validation

    def test_compare_four_documents_returns_422(self, test_client, sample_txt_bytes):
        """Comparing four documents should return 422 (max is 3)."""
        ids = [
            upload_test_document(test_client, sample_txt_bytes, f"doc{i}.txt")
            for i in range(4)
        ]
        response = test_client.post(
            "/api/v1/documents/compare",
            json={"document_ids": ids},
        )
        assert response.status_code == 422

    def test_compare_duplicate_ids_returns_422(self, test_client, sample_txt_bytes):
        """Using the same document ID twice should return 422."""
        id1 = upload_test_document(test_client, sample_txt_bytes)

        response = test_client.post(
            "/api/v1/documents/compare",
            json={"document_ids": [id1, id1]},  # Same ID twice
        )
        assert response.status_code == 422

    def test_compare_with_focus(self, test_client, sample_txt_bytes):
        """Should accept optional comparison_focus parameter."""
        id1, id2 = self._upload_two_docs(test_client, sample_txt_bytes)

        with patch(
            "app.services.claude_service.ClaudeService._call_claude",
            return_value=self.MOCK_RESPONSE,
        ):
            response = test_client.post(
                "/api/v1/documents/compare",
                json={
                    "document_ids": [id1, id2],
                    "comparison_focus": "financial performance",
                },
            )

        assert response.status_code == 200
