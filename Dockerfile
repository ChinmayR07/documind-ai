# ─── DocuMind AI — Dockerfile ─────────────────────────────────────────────────
#
# Multi-stage build:
# Stage 1 (builder): Install dependencies
# Stage 2 (runtime): Copy only what's needed to run
#
# Why multi-stage?
# The builder stage has pip, build tools, and compiler headers — all needed
# to install packages but not to RUN the app. The final image only contains
# the runtime, making it significantly smaller and more secure.
#
# Result: ~400MB instead of ~1.2GB for a single-stage build
#
# Interview talking point:
# "I used a multi-stage Docker build to minimize the final image size.
# The builder stage compiles dependencies, the runtime stage only
# copies what's needed — no build tools, no pip, no unnecessary files."

# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install system build dependencies
# These are needed to compile some Python packages (like hiredis)
# but won't be in the final image
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching optimization)
# If requirements.txt doesn't change, this layer is cached
# and pip install doesn't re-run on every build
COPY requirements.txt .

# Install Python dependencies into a separate directory
# --prefix=/install means they go to /install, not system Python
# This makes copying them to the final stage clean and explicit
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Install RUNTIME system dependencies only
# - tesseract-ocr: OCR engine for image parsing
# - libmagic1: file type detection (python-magic)
# - libgl1: required by PyMuPDF for PDF rendering
# - These must be in the final image since the app uses them at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
    # rm -rf /var/lib/apt/lists/* reduces image size by removing apt cache

# Create non-root user for security
# Never run production containers as root — it's a security vulnerability
# If the app is compromised, the attacker only gets 'appuser' permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/

# Create uploads directory with correct permissions
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check — Docker will mark the container unhealthy if this fails
# --interval: check every 30 seconds
# --timeout: fail if no response in 10 seconds
# --start-period: wait 10 seconds before first check (app startup time)
# --retries: mark unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health').raise_for_status()"

# Start the application
# - Use uvicorn directly (not python -m app.main) for Docker
# - --host 0.0.0.0: accept connections from outside the container
# - --workers 1: 1 worker process (adjust based on CPU cores)
# - --no-access-log: reduce log noise (logs go to app logger instead)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1"]
