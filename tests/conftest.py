"""
DocuMind AI — Test Configuration and Fixtures
===============================================
conftest.py is Pytest's special file for shared fixtures.
Fixtures defined here are automatically available to ALL test files
without needing to import them.

What is a fixture?
A fixture is a reusable piece of test setup. Instead of repeating
"create a temp file, create a test client, set up mock Claude..."
in every test, you define it once as a fixture and Pytest injects it.

Interview talking point:
"I used Pytest fixtures with appropriate scopes — function-scoped
fixtures reset between each test (clean state), session-scoped
fixtures are created once and shared (expensive setup like clients)."
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Set test environment BEFORE importing app modules
# This prevents the real settings from loading during tests
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing-only")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("CACHE_ENABLED", "false")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")


# ─── App Client ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_client():
    """
    FastAPI TestClient — used to make HTTP requests in tests.

    scope="session" means this client is created ONCE per test session
    and reused across all test files. Creating it is slightly expensive
    (app startup) so we don't want to recreate it for every test.

    TestClient from FastAPI wraps the app in a way that:
    - No real HTTP server is started
    - Requests are handled in-process (fast)
    - Works synchronously even with async routes
    """
    from app.main import app
    with TestClient(app) as client:
        yield client


# ─── Temporary Files ──────────────────────────────────────────────────────────

@pytest.fixture
def temp_dir():
    """
    Create a temporary directory that's automatically cleaned up after each test.
    scope="function" (default) = new temp dir for every test.
    """
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_txt_file(temp_dir):
    """A real .txt file for testing the text parser."""
    content = """DocuMind AI Test Document
==========================

This is a sample text document used for testing.

Section 1: Introduction
The quick brown fox jumps over the lazy dog.
This sentence contains every letter of the alphabet.

Section 2: Data
Revenue Q1: $1,200,000
Revenue Q2: $1,450,000
Revenue Q3: $1,800,000

Section 3: Conclusion
Total revenue for the year exceeded expectations by 15%.
The board recommends continued investment in AI initiatives.
"""
    file_path = temp_dir / "test_document.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_txt_bytes():
    """Raw bytes of a text document — for upload endpoint tests."""
    content = """Test Document for Upload
=========================
This document is used to test the upload endpoint.

Key facts:
- Created for testing purposes
- Contains multiple paragraphs
- Has structured content

The API should extract this text successfully.
"""
    return content.encode("utf-8")


@pytest.fixture
def sample_pdf_bytes():
    """
    Minimal valid PDF bytes.
    This is the smallest valid PDF possible — just enough to not be rejected
    by file type validation. PyMuPDF can open it, but it has no text.

    In a real project you'd use a fixture PDF file in tests/fixtures/
    """
    # Minimal PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
    return pdf_content


# ─── Mock Claude Responses ────────────────────────────────────────────────────

@pytest.fixture
def mock_claude_qa_response():
    """Fake Claude Q&A response — avoids real API calls."""
    return (
        "Based on the document, the main conclusion is that revenue exceeded "
        "expectations by 15% in Q3. The board recommends continued investment "
        "in AI initiatives as stated in Section 3.",
        500,  # approximate tokens
    )


@pytest.fixture
def mock_claude_summarize_response():
    """Fake Claude summarization response as JSON string."""
    import json
    return (
        json.dumps({
            "executive_summary": "This document reports strong financial performance with revenue exceeding targets by 15%.",
            "key_points": [
                "Q1 revenue: $1,200,000",
                "Q2 revenue: $1,450,000",
                "Q3 revenue: $1,800,000",
                "Total exceeded expectations by 15%",
                "Board recommends AI investment",
            ],
            "key_entities": ["Q1", "Q2", "Q3", "$1,200,000", "$1,800,000"],
            "document_type_detected": "Financial Report",
            "recommended_action": "Review AI investment strategy for next fiscal year",
        }),
        800,
    )


@pytest.fixture
def mock_claude_compare_response():
    """Fake Claude comparison response as JSON string."""
    import json
    return (
        json.dumps({
            "overview": "Document 1 is a financial report. Document 2 is a strategic plan.",
            "common_themes": ["Revenue growth", "AI investment", "Q3 performance"],
            "key_differences": [
                "Document 1 focuses on historical data",
                "Document 2 focuses on future strategy",
            ],
            "unique_insights": {
                "doc1": "Specific revenue figures by quarter",
                "doc2": "Strategic recommendations for next year",
            },
            "contradictions": [],
            "synthesis": "Both documents align on the importance of AI investment.",
        }),
        1200,
    )


@pytest.fixture
def mock_claude_service(
    mock_claude_qa_response,
    mock_claude_summarize_response,
    mock_claude_compare_response,
):
    """
    Patch the Claude service's _call_claude method.

    This is the key mock — instead of making real API calls,
    _call_claude returns our fake responses instantly.

    Using patch() as a context manager ensures the mock is
    removed after each test — no test pollution.
    """
    with patch(
        "app.services.claude_service.ClaudeService._call_claude"
    ) as mock_call:
        # Configure return values based on what was most recently called
        # We'll set specific return values in individual tests
        mock_call.return_value = mock_claude_qa_response
        yield mock_call


# ─── Document Store Helpers ───────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_document_store():
    """
    Clear the in-memory document store before each test.

    autouse=True means this fixture runs for EVERY test automatically
    without needing to be listed as a parameter.

    This prevents test pollution — one test's uploaded documents
    shouldn't affect another test's assertions.
    """
    from app.services import document_service as ds_module
    # Clear the store before test
    ds_module._document_store.clear()
    yield
    # Clear after test too (cleanup)
    ds_module._document_store.clear()
