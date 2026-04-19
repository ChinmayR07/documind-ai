"""
DocuMind AI — FastAPI Application Entry Point
==============================================
This is where the FastAPI app is created and configured.
All middleware, exception handlers, and routers are registered here.
"""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings


# ─── Lifespan (startup + shutdown) ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Runs on startup and shutdown.
    - Startup: verify connections, create directories
    - Shutdown: close connections cleanly
    """
    # ── Startup ──
    print(f"\n🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"   Environment: {settings.APP_ENV}")
    print(f"   Claude Model: {settings.CLAUDE_MODEL}")
    print(f"   Max File Size: {settings.MAX_FILE_SIZE_MB}MB")

    # Ensure upload directory exists
    settings.UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
    print(f"   Upload directory: {settings.UPLOAD_PATH}")

    # Test Redis connection
    if settings.CACHE_ENABLED:
        try:
            client = aioredis.from_url(settings.REDIS_URL)
            await client.ping()
            await client.aclose()
            print("   Redis: ✅ Connected")
        except Exception:
            print("   Redis: ⚠️  Not available — running without cache")

    print(f"\n📚 API Docs: http://{settings.APP_HOST}:{settings.APP_PORT}/docs\n")

    yield  # App runs here

    # ── Shutdown ──
    print(f"\n👋 Shutting down {settings.APP_NAME}...")


# ─── Create FastAPI App ───────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",           # Swagger UI at /docs
    redoc_url="/redoc",         # ReDoc UI at /redoc
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ─── CORS Middleware ──────────────────────────────────────────────────────────
# Allows browsers to make requests to this API from different origins
# In production, replace "*" with your actual frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.IS_DEVELOPMENT else [
        "https://chinmayraichur.me",
        "https://chinmayraichur.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request ID Middleware ────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """
    Adds a unique ID to every request for tracing/debugging.
    Also logs request timing.
    If something goes wrong, you can search logs by request ID.
    """
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration_ms}ms"

    # Log each request in development
    if settings.IS_DEVELOPMENT:
        print(
            f"[{request_id}] {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms}ms)"
        )

    return response


# ─── Global Exception Handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches any unhandled exception and returns a clean JSON error.
    Prevents stack traces leaking to clients in production.
    """
    if settings.IS_DEVELOPMENT:
        # In development, show the actual error
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )
    # In production, hide error details
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.
    Used by Docker, Kubernetes, and load balancers to verify the app is running.
    Returns 200 if healthy.
    """
    redis_status = "disabled"
    if settings.CACHE_ENABLED:
        try:
            client = aioredis.from_url(settings.REDIS_URL)
            await client.ping()
            await client.aclose()
            redis_status = "connected"
        except Exception:
            redis_status = "unavailable"

    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "model": settings.CLAUDE_MODEL,
        "redis": redis_status,
    }


# ─── Root Endpoint ────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root() -> dict:
    """Welcome message with links to docs."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
        "github": "https://github.com/ChinmayR07/documind-ai",
    }


# ─── Register API Routers ─────────────────────────────────────────────────────
# Import here (not at top) to avoid circular imports
from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")


# ─── Run directly (for development) ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
        log_level="debug" if settings.DEBUG else "info",
    )
