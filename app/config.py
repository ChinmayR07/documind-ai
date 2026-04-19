"""
DocuMind AI — Application Configuration
========================================
Uses Pydantic Settings to load and validate all configuration
from environment variables. Fails fast on startup if required
values are missing — much better than failing mid-request.

Usage:
    from app.config import settings
    print(settings.ANTHROPIC_API_KEY)
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings loaded from environment variables.
    Pydantic validates types automatically — if ANTHROPIC_API_KEY
    is missing, the app refuses to start with a clear error message.
    """

    model_config = SettingsConfigDict(
        # Load from .env file in development
        env_file=".env",
        env_file_encoding="utf-8",
        # Ignore extra fields in .env that aren't defined here
        extra="ignore",
        # Case insensitive — MY_VAR and my_var are treated the same
        case_sensitive=False,
    )

    # ─── App Settings ─────────────────────────────────────────────────────────
    APP_NAME: str = "DocuMind AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Intelligent Document Analysis API powered by Claude AI"
    APP_ENV: Literal["development", "production", "test"] = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # ─── Claude AI ────────────────────────────────────────────────────────────
    # Required — app will not start without this
    ANTHROPIC_API_KEY: str = Field(..., description="Anthropic Claude API key")
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TIMEOUT_SECONDS: int = 60

    # ─── Redis Cache ──────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_SECONDS: int = 3600   # 1 hour default
    CACHE_ENABLED: bool = True

    # ─── File Upload ──────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 20
    UPLOAD_DIR: str = "uploads"

    # Supported MIME types — what file types we accept
    ALLOWED_MIME_TYPES: list[str] = [
        # PDF
        "application/pdf",
        # Word documents
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        # Plain text
        "text/plain",
        # Images (for OCR)
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/webp",
        "image/bmp",
    ]

    # Human-readable file extensions (for error messages)
    ALLOWED_EXTENSIONS: list[str] = [
        ".pdf", ".docx", ".doc", ".txt",
        ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp",
    ]

    # ─── Computed Properties ──────────────────────────────────────────────────
    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        """Convert MB to bytes for file size validation."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def UPLOAD_PATH(self) -> Path:
        """Return upload directory as a Path object and ensure it exists."""
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def IS_PRODUCTION(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def IS_DEVELOPMENT(self) -> bool:
        return self.APP_ENV == "development"

    # ─── Validators ───────────────────────────────────────────────────────────
    @field_validator("ANTHROPIC_API_KEY")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """
        Ensure the API key looks valid.
        Anthropic keys always start with 'sk-ant-'
        """
        if not v or v == "sk-ant-your-key-here":
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Get your key from console.anthropic.com"
            )
        if not v.startswith("sk-ant-"):
            raise ValueError(
                "ANTHROPIC_API_KEY looks invalid — it should start with 'sk-ant-'"
            )
        return v

    @field_validator("MAX_FILE_SIZE_MB")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Cap file size between 1MB and 100MB."""
        if v < 1:
            raise ValueError("MAX_FILE_SIZE_MB must be at least 1")
        if v > 100:
            raise ValueError("MAX_FILE_SIZE_MB cannot exceed 100")
        return v

    @field_validator("CLAUDE_MAX_TOKENS")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Claude claude-sonnet-4-20250514 supports up to 8192 output tokens."""
        if v < 100:
            raise ValueError("CLAUDE_MAX_TOKENS must be at least 100")
        if v > 8192:
            raise ValueError("CLAUDE_MAX_TOKENS cannot exceed 8192 for Claude claude-sonnet-4-20250514")
        return v


# ─── Singleton Pattern ────────────────────────────────────────────────────────
@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    @lru_cache means this function only runs ONCE — the Settings object
    is created on first call and reused for every subsequent call.
    This is important because reading env vars and validating them
    on every request would be wasteful.

    Usage in FastAPI dependency injection:
        from fastapi import Depends
        from app.config import get_settings, Settings

        @router.get("/something")
        def my_route(settings: Settings = Depends(get_settings)):
            ...
    """
    return Settings()


# ─── Module-level settings instance ──────────────────────────────────────────
# Import this directly in most places:
#   from app.config import settings
settings = get_settings()
