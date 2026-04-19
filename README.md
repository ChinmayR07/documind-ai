# DocuMind AI 🧠

> **Intelligent Document Analysis API** — Upload PDFs, Word docs, and images. Ask questions, get summaries, and compare documents side by side using Claude AI.

[![CI](https://github.com/ChinmayR07/documind-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/ChinmayR07/documind-ai/actions)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Claude AI](https://img.shields.io/badge/Claude-claude--sonnet--4--20250514-orange?logo=anthropic)](https://anthropic.com)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 Table of Contents

- [What it does](#-what-it-does)
- [Live Demo](#-live-demo)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Design Decisions](#-design-decisions)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Author](#-author)

---

## ✨ What it does

DocuMind AI is a production-grade REST API that extracts intelligence from documents using Claude AI (claude-sonnet-4-20250514).

### Supported Document Types

| Format | Extension                            | Method                                       |
| ------ | ------------------------------------ | -------------------------------------------- |
| PDF    | `.pdf`                               | PyMuPDF — page-by-page text extraction       |
| Word   | `.docx`                              | python-docx — paragraphs, tables, headers    |
| Text   | `.txt`                               | Built-in — with automatic encoding detection |
| Images | `.jpg` `.png` `.tiff` `.webp` `.bmp` | Tesseract OCR with preprocessing             |

### AI Capabilities

**📖 Document Q&A**
Ask any natural language question about an uploaded document. Claude analyzes the content and returns precise answers with page references.

```json
POST /api/v1/documents/{id}/ask
{
  "question": "What was the total revenue in Q3?"
}
→ "Based on page 4, Q3 revenue was $1.8M, exceeding targets by 15%."
```

**📝 Intelligent Summarization**
Generate structured summaries with executive overview, key points, entities, and recommended actions.

```json
POST /api/v1/documents/{id}/summarize
{
  "max_length": "medium",
  "focus_areas": ["financial data", "risks"]
}
→ {
    "executive_summary": "...",
    "key_points": ["...", "..."],
    "key_entities": ["Q3", "$1.8M", "Board"],
    "recommended_action": "..."
  }
```

**🔄 Multi-Document Comparison**
Compare 2–3 documents side by side. Find common themes, key differences, contradictions, and synthesize insights across all documents.

```json
POST /api/v1/documents/compare
{
  "document_ids": ["id-1", "id-2"],
  "comparison_focus": "financial performance"
}
→ {
    "common_themes": ["..."],
    "key_differences": ["..."],
    "contradictions": [],
    "synthesis": "..."
  }
```

---

## 🎬 Live Demo

> Try it yourself in 60 seconds — no sign-up required.

**Swagger UI (interactive API docs):**

```
http://localhost:8000/docs
```

### Demo Walkthrough

**1. Upload a document**

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@your_document.pdf"

# Response:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "document_type": "pdf",
  "word_count": 3420,
  "status": "ready"
}
```

**2. Ask a question**

```bash
curl -X POST http://localhost:8000/api/v1/documents/550e8400.../ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main risks identified?"}'

# Response:
{
  "answer": "The document identifies three main risks: ...",
  "context_chars_used": 12500,
  "tokens_used_approx": 3125
}
```

**3. Get a summary**

```bash
curl -X POST http://localhost:8000/api/v1/documents/550e8400.../summarize \
  -H "Content-Type: application/json" \
  -d '{"max_length": "medium"}'
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Client (curl / Swagger UI)          │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────┐
│                    FastAPI Application                   │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Routes    │  │  Middleware  │  │  Exception    │  │
│  │  /upload    │  │  RequestID   │  │  Handlers     │  │
│  │  /ask       │  │  CORS        │  │               │  │
│  │  /summarize │  │  Timing      │  │               │  │
│  │  /compare   │  │              │  │               │  │
│  └──────┬──────┘  └──────────────┘  └───────────────┘  │
│         │                                               │
│  ┌──────▼──────────────────────────────────────────┐   │
│  │              Service Layer (Facade)              │   │
│  │  DocumentService — orchestrates everything       │   │
│  └──────┬──────────────────┬────────────────────┬──┘   │
│         │                  │                    │       │
│  ┌──────▼──────┐  ┌────────▼───────┐  ┌────────▼──┐   │
│  │ParserService│  │ ClaudeService  │  │   Cache   │   │
│  │  Strategy   │  │  Retry + JSON  │  │  Service  │   │
│  │  Pattern    │  │  parsing       │  │  Redis    │   │
│  └──────┬──────┘  └────────┬───────┘  └───────────┘   │
│         │                  │                            │
│  ┌──────▼──────┐  ┌────────▼───────┐                  │
│  │  Parsers    │  │  Anthropic     │                  │
│  │ PDF  DOCX   │  │  Claude API    │                  │
│  │ TXT  Image  │  │                │                  │
│  └─────────────┘  └────────────────┘                  │
└─────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                     Infrastructure                       │
│          Redis (cache)    Local Filesystem (uploads)     │
└─────────────────────────────────────────────────────────┘
```

### Design Patterns Used

| Pattern              | Where             | Why                                                                             |
| -------------------- | ----------------- | ------------------------------------------------------------------------------- |
| **Strategy**         | `ParserService`   | Swappable parsers per file type — add new formats without changing callers      |
| **Facade**           | `DocumentService` | Single interface to complex subsystem (parsers + Claude + storage)              |
| **Template Method**  | `BaseParser`      | Common parse workflow (validate → extract → clean) with customizable extraction |
| **Singleton**        | All services      | One shared instance per service — avoids reconnecting on every request          |
| **12-Factor Config** | `config.py`       | All config from environment variables — works identically in dev, Docker, cloud |

---

## 🛠️ Tech Stack

### Core

| Technology      | Version | Purpose                                                           |
| --------------- | ------- | ----------------------------------------------------------------- |
| **Python**      | 3.11    | Language                                                          |
| **FastAPI**     | 0.111   | Async web framework — automatic OpenAPI docs, Pydantic validation |
| **Uvicorn**     | 0.29    | ASGI server                                                       |
| **Pydantic v2** | 2.7     | Request/response validation and settings management               |

### AI & Document Processing

| Technology           | Version                  | Purpose                                 |
| -------------------- | ------------------------ | --------------------------------------- |
| **Anthropic Claude** | claude-sonnet-4-20250514 | Q&A, summarization, comparison          |
| **PyMuPDF (fitz)**   | 1.24                     | PDF text extraction — industry standard |
| **python-docx**      | 1.1                      | Word document parsing including tables  |
| **Tesseract OCR**    | 5.x                      | Image-to-text extraction                |
| **Pillow**           | 10.3                     | Image preprocessing before OCR          |

### Infrastructure

| Technology         | Version | Purpose                                      |
| ------------------ | ------- | -------------------------------------------- |
| **Redis**          | 7       | Response caching — avoids duplicate AI calls |
| **Docker**         | 24+     | Containerization                             |
| **Docker Compose** | v2      | Multi-service orchestration                  |
| **GitHub Actions** | —       | CI/CD pipeline                               |

### Code Quality

| Tool           | Purpose                                            |
| -------------- | -------------------------------------------------- |
| **Ruff**       | Linting + import sorting (replaces flake8 + isort) |
| **Black**      | Code formatting                                    |
| **MyPy**       | Static type checking                               |
| **Pytest**     | Testing framework — 105 tests                      |
| **pytest-cov** | Coverage reports                                   |

---

## 🚀 Quick Start

### Option A — Docker Compose (Recommended)

The fastest way to run the full stack. Requires [Docker Desktop](https://docker.com/products/docker-desktop).

```bash
# 1. Clone the repo
git clone https://github.com/ChinmayR07/documind-ai.git
cd documind-ai

# 2. Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Start everything
make docker-up
# or: docker compose up

# 4. Open Swagger UI
open http://localhost:8000/docs
```

That's it. The API, Redis cache, and all dependencies start automatically.

### Option B — Local Development

```bash
# 1. Clone and enter repo
git clone https://github.com/ChinmayR07/documind-ai.git
cd documind-ai

# 2. Install system dependencies (Mac)
brew install tesseract python@3.11

# 3. Create virtual environment and install
make install
source venv/bin/activate

# 4. Set up environment
make setup-env
# Edit .env → add ANTHROPIC_API_KEY=sk-ant-...

# 5. Run development server (with hot reload)
make dev

# 6. Open Swagger UI
open http://localhost:8000/docs
```

### Getting an API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up → **API Keys** → **Create Key**
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
4. Add $5 credit in Billing (each document analysis costs ~$0.001)

---

## 📚 API Reference

### Base URL

```
http://localhost:8000/api/v1
```

### Endpoints

#### Document Management

| Method   | Endpoint                   | Description                    |
| -------- | -------------------------- | ------------------------------ |
| `POST`   | `/documents/upload`        | Upload a document for analysis |
| `GET`    | `/documents/`              | List all uploaded documents    |
| `GET`    | `/documents/{id}`          | Get document details           |
| `GET`    | `/documents/{id}/download` | Download original file         |
| `DELETE` | `/documents/{id}`          | Delete a document              |

#### AI Analysis

| Method | Endpoint                    | Description                     |
| ------ | --------------------------- | ------------------------------- |
| `POST` | `/documents/{id}/ask`       | Ask a question about a document |
| `POST` | `/documents/{id}/summarize` | Generate structured summary     |
| `POST` | `/documents/compare`        | Compare 2-3 documents           |

#### System

| Method | Endpoint  | Description             |
| ------ | --------- | ----------------------- |
| `GET`  | `/health` | Health check            |
| `GET`  | `/docs`   | Interactive Swagger UI  |
| `GET`  | `/redoc`  | ReDoc API documentation |

### Request / Response Examples

#### Upload

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

file: <binary>

Response 201:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "annual_report.pdf",
  "document_type": "pdf",
  "file_size_mb": 2.4,
  "status": "ready",
  "page_count": 48,
  "word_count": 12350,
  "char_count": 74200,
  "warnings": [],
  "message": "Document uploaded and processed successfully"
}
```

#### Ask

```http
POST /api/v1/documents/550e8400.../ask
Content-Type: application/json

{
  "question": "What were the three biggest risk factors?",
  "include_page_references": true
}

Response 200:
{
  "document_id": "550e8400-...",
  "question": "What were the three biggest risk factors?",
  "answer": "According to page 12, the three biggest risk factors are: 1) Market volatility...",
  "context_chars_used": 45000,
  "cached": false,
  "tokens_used_approx": 11250,
  "analysis_type": "qa"
}
```

#### Compare

```http
POST /api/v1/documents/compare
Content-Type: application/json

{
  "document_ids": ["id-one", "id-two"],
  "comparison_focus": "financial performance"
}

Response 200:
{
  "document_ids": ["id-one", "id-two"],
  "num_documents": 2,
  "overview": "Document 1 is Q2 report. Document 2 is Q3 report.",
  "common_themes": ["Revenue growth", "AI investment"],
  "key_differences": ["Q2 revenue $1.45M vs Q3 $1.8M"],
  "unique_insights": { "id-one": "...", "id-two": "..." },
  "contradictions": [],
  "synthesis": "Both quarters show positive trends with Q3 outperforming.",
  "analysis_type": "compare"
}
```

### Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Human-readable error message explaining what went wrong"
}
```

| Status Code | When                                   |
| ----------- | -------------------------------------- |
| `400`       | Invalid file type or malformed request |
| `404`       | Document ID not found                  |
| `413`       | File exceeds 20MB size limit           |
| `422`       | Request body validation failed         |
| `500`       | AI analysis or parsing error           |

---

## 📁 Project Structure

```
documind-ai/
├── app/
│   ├── main.py               # FastAPI app — middleware, routes, lifespan
│   ├── config.py             # Pydantic Settings — type-safe env var loading
│   ├── constants.py          # Enums, prompt templates, limits
│   │
│   ├── api/v1/
│   │   ├── router.py         # Combines all route groups
│   │   ├── documents.py      # Document CRUD endpoints
│   │   └── analysis.py       # AI analysis endpoints
│   │
│   ├── models/
│   │   └── schemas.py        # All Pydantic request/response models
│   │
│   ├── services/
│   │   ├── document_service.py   # Facade — orchestrates everything
│   │   ├── claude_service.py     # Claude AI — retry, JSON parsing, cost est.
│   │   ├── parser_service.py     # Strategy — routes files to correct parser
│   │   └── parsers/
│   │       ├── base_parser.py    # Abstract base + ParseResult dataclass
│   │       ├── pdf_parser.py     # PyMuPDF PDF extraction
│   │       ├── docx_parser.py    # python-docx Word extraction
│   │       ├── txt_parser.py     # Multi-encoding text extraction
│   │       └── ocr_parser.py     # Tesseract OCR with preprocessing
│   │
│   └── utils/
│       ├── text_utils.py     # Chunking, cleaning, token estimation
│       └── file_utils.py     # Validation, safe naming, size checks
│
├── tests/
│   ├── conftest.py           # Shared fixtures, mock Claude, test client
│   ├── test_parsers.py       # Parser unit tests (26 tests)
│   ├── test_documents.py     # Document API tests (21 tests)
│   ├── test_analysis.py      # Analysis API tests (37 tests)
│   └── test_utils.py         # Utility + config tests (21 tests)
│
├── Dockerfile                # Multi-stage build, non-root user
├── docker-compose.yml        # API + Redis orchestration
├── docker-compose.override.yml  # Dev overrides (hot reload)
├── .github/workflows/ci.yml  # Lint → Type check → Test → Docker build
├── Makefile                  # Developer commands (make dev, make test, etc.)
├── pyproject.toml            # Project metadata + tool config (Ruff, Black, MyPy, Pytest)
├── requirements.txt          # Production dependencies
└── requirements-dev.txt      # Dev/test dependencies
```

---

## 🧠 Design Decisions

### Why FastAPI over Flask or Django?

FastAPI gives automatic OpenAPI/Swagger documentation, native async support, and Pydantic validation with zero boilerplate. For an API-first project, it outperforms Flask (no auto-docs, no validation) and Django (too opinionated, heavyweight for a pure API).

### Why PyMuPDF over PyPDF2 or pdfminer?

PyMuPDF uses the same rendering engine as Adobe Acrobat. It correctly handles multi-column layouts, rotated text, embedded fonts, and password-protected PDFs — all of which PyPDF2 struggles with. It's also significantly faster (5-10x) on large documents.

### Why Strategy Pattern for parsers?

Adding support for a new file format (e.g., `.xlsx`, `.pptx`) requires creating one new class and registering it in `ParserService`. Zero changes to existing code — this is the Open/Closed Principle. Without this pattern, every new format would require modifying the central parsing logic.

### Why exponential backoff for Claude API calls?

Claude's API occasionally returns transient errors under load. A naive implementation that fails immediately creates poor UX. Exponential backoff with jitter (1s → 2s → 4s delay between retries, capped at 30s) handles these gracefully while not hammering a struggling API.

### Why structured JSON output from Claude?

Asking Claude to return JSON rather than free-form text gives us typed Python objects we can validate, transform, and display differently in UIs. If JSON parsing fails, we fall back to raw text — the API never crashes.

### Why in-memory storage instead of a database?

Deliberately chosen for demo simplicity. The `_document_store` dict in `document_service.py` can be swapped for any database (PostgreSQL, DynamoDB, MongoDB) without changing the API routes or service interface. The Facade pattern makes this migration trivial.

---

## 🧪 Testing

```bash
# Run all 105 tests
make test

# With coverage report
make test-cov
# Opens htmlcov/index.html with line-by-line coverage

# Run a specific test file
pytest tests/test_parsers.py -v

# Run tests matching a pattern
pytest tests/ -k "test_upload" -v
```

### Test Architecture

```
105 tests across 4 files

conftest.py         Shared fixtures
    ├── TestClient (session-scoped — created once)
    ├── Temp file fixtures (function-scoped — fresh each test)
    ├── Mock Claude responses (no real API calls)
    └── Auto-clear document store (prevents test pollution)

test_parsers.py     26 unit tests
    ├── ParseResult dataclass behaviour
    ├── TextParser — encoding, validation, edge cases
    └── ParserService — routing, hashing, chunking

test_documents.py   21 integration tests
    ├── Upload — valid files, empty, wrong type, too large
    ├── List — empty, after upload, filename preservation
    ├── Get — existing, non-existent (404)
    └── Delete — success, removes from list, 404

test_analysis.py    37 integration tests (mocked Claude)
    ├── Q&A — response shape, echo question, 404, validation
    ├── Summarize — response fields, invalid length, focus areas
    └── Compare — 2 docs, 4 docs (422), duplicates (422), focus

test_utils.py       21 unit tests
    ├── Text chunking, cleaning, truncation, token counting
    ├── File validation, safe naming, size calculation
    └── Config properties, constants, enums
```

---

## 🚢 Deployment

### Railway (Easiest — 2 minutes)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up

# Add environment variables
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set CACHE_ENABLED=false  # No Redis on free tier

# Your API is live at: https://documind-ai.up.railway.app
```

### Render (Also free)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your `documind-ai` repo
4. Runtime: **Docker**, Build: auto-detected
5. Add environment variables in the Render dashboard
6. Deploy → live URL in ~3 minutes

### AWS EC2 / DigitalOcean Droplet

```bash
# On your server (Ubuntu 22.04)
git clone https://github.com/ChinmayR07/documind-ai.git
cd documind-ai
cp .env.example .env && nano .env  # Add your API key

# Install Docker
curl -fsSL https://get.docker.com | sh

# Start
docker compose up -d

# Your API is live at: http://YOUR_SERVER_IP:8000
```

---

## 👤 Author

**Chinmay Raichur**
Full Stack Software Engineer · 4.5+ years experience

- 🌐 Portfolio: [chinmayraichur.me](https://chinmay-portfolio-seven.vercel.app/)
- 💼 LinkedIn: [linkedin.com/in/chinmay-raichur](https://linkedin.com/in/chinmay-raichur)
- 🐙 GitHub: [github.com/ChinmayR07](https://github.com/ChinmayR07)
- 📧 Email: chinmayraichur@gmail.com

### Related Projects

- [chinmay-portfolio](https://github.com/ChinmayR07/chinmay-portfolio) — Personal portfolio built with Next.js 14, React, TypeScript, and Claude API

---

## 📄 License

MIT — feel free to use this as a template or learning resource.

---

_Built with FastAPI, Claude AI, and a lot of coffee ☕_
