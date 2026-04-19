"""
DocuMind AI — File Utilities
==============================
File validation, type detection, and safe filename generation.
"""

import uuid
from pathlib import Path

from app.config import settings


def validate_file_size(file_size: int) -> None:
    """Raise ValueError if file exceeds max allowed size."""
    if file_size > settings.MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
            f"the maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )


def validate_file_extension(filename: str) -> None:
    """Raise ValueError if file extension is not supported."""
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '{ext}' is not supported. "
            f"Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )


def generate_safe_filename(original_filename: str) -> str:
    """
    Generate a unique, safe filename for storage.

    Why not use the original filename?
    - Security: prevents path traversal attacks (../../etc/passwd)
    - Collisions: two files with the same name would overwrite each other
    - Special chars: spaces, unicode, etc. cause issues on some filesystems

    Result: "my document.pdf" → "a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf"
    """
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4()}{ext}"


def get_file_size_mb(file_path: Path) -> float:
    """Return file size in MB rounded to 2 decimal places."""
    return round(file_path.stat().st_size / 1024 / 1024, 2)


def delete_file_safely(file_path: Path) -> bool:
    """
    Delete a file without raising an exception if it doesn't exist.
    Returns True if deleted, False if file wasn't found.
    """
    try:
        file_path.unlink(missing_ok=True)
        return True
    except Exception:
        return False
