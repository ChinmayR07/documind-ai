# ─── DocuMind AI — Makefile ───────────────────────────────────────────────────
# Common development commands.
# Usage: make <target>
# e.g.:  make dev        → start dev server
#        make test       → run tests
#        make docker-up  → start with Docker Compose
#
# Why a Makefile?
# Self-documenting project commands. Any engineer who clones this
# repo can run 'make help' and immediately know how to use it.
# This is expected at any serious engineering team.

.PHONY: help install dev test lint format type-check clean \
        docker-up docker-down docker-build docker-logs docker-shell

# Default target — show help
.DEFAULT_GOAL := help

# ─── Help ─────────────────────────────────────────────────────────────────────
help:  ## Show this help message
	@echo "DocuMind AI — Available Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Setup ────────────────────────────────────────────────────────────────────
install:  ## Install all dependencies (creates venv)
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r requirements-dev.txt
	@echo "✅ Dependencies installed. Activate with: source venv/bin/activate"

setup-env:  ## Copy .env.example to .env
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env — add your ANTHROPIC_API_KEY"; \
	else \
		echo "⚠️  .env already exists — not overwriting"; \
	fi

# ─── Development ──────────────────────────────────────────────────────────────
dev:  ## Start development server with hot reload
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

start:  ## Start production server
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# ─── Code Quality ─────────────────────────────────────────────────────────────
lint:  ## Run Ruff linter
	ruff check app/ tests/

lint-fix:  ## Run Ruff linter and auto-fix issues
	ruff check --fix app/ tests/

format:  ## Format code with Ruff
	ruff format app/ tests/

format-check:  ## Check code formatting without changing files
	ruff format --check app/ tests/

type-check:  ## Run MyPy type checker
	mypy app/ --ignore-missing-imports

check: lint format-check type-check  ## Run all quality checks

# ─── Testing ──────────────────────────────────────────────────────────────────
test:  ## Run all tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage report
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
	@echo "📊 Coverage report: htmlcov/index.html"

test-fast:  ## Run tests without coverage (faster)
	pytest tests/ -v --no-cov -x
	# -x = stop on first failure

# ─── Docker ───────────────────────────────────────────────────────────────────
docker-build:  ## Build Docker image
	docker compose build

docker-up:  ## Start all services with Docker Compose
	docker compose up

docker-up-d:  ## Start all services in background
	docker compose up -d
	@echo "✅ Services started. Swagger UI: http://localhost:8000/docs"

docker-down:  ## Stop all services
	docker compose down

docker-down-v:  ## Stop all services and remove volumes
	docker compose down -v

docker-logs:  ## Follow logs from all services
	docker compose logs -f

docker-logs-api:  ## Follow logs from API service only
	docker compose logs -f api

docker-shell:  ## Open shell inside running API container
	docker compose exec api bash

docker-redis:  ## Open Redis CLI inside running Redis container
	docker compose exec redis redis-cli

# ─── Utilities ────────────────────────────────────────────────────────────────
clean:  ## Remove Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	find . -type d -name ".ruff_cache" -delete
	find . -type d -name "htmlcov" -delete
	find . -name ".coverage" -delete
	@echo "✅ Cache files removed"

clean-uploads:  ## Remove all uploaded files (keeps .gitkeep)
	find uploads/ -type f ! -name ".gitkeep" -delete
	@echo "✅ Uploads cleared"

health:  ## Check API health
	curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
