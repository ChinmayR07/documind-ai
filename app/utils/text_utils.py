"""
DocuMind AI — Text Utilities
==============================
Shared text processing functions used across the app.
"""

import re


def chunk_text(
    text: str,
    chunk_size: int = 4000,
    overlap: int = 200,
) -> list[str]:
    """
    Split text into overlapping chunks for large document processing.

    Why overlap? If a sentence spans a chunk boundary, we'd lose context.
    Overlap ensures each chunk shares 200 chars with the previous one.

    Args:
        text:       The full document text
        chunk_size: Maximum characters per chunk
        overlap:    Characters to repeat between adjacent chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            # Find a natural break point (sentence or paragraph end)
            # to avoid splitting mid-sentence
            for break_char in ["\n\n", "\n", ". ", " "]:
                break_pos = text.rfind(break_char, start, end)
                if break_pos > start:
                    end = break_pos + len(break_char)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move forward by chunk_size - overlap
        start = max(start + 1, end - overlap)

    return chunks


def clean_text(text: str) -> str:
    """Remove noise and normalize whitespace."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def truncate_text(text: str, max_chars: int, suffix: str = "...") -> str:
    """Truncate text to max_chars, breaking at a word boundary."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars - len(suffix)]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + suffix


def count_tokens_approx(text: str) -> int:
    """
    Approximate token count (1 token ≈ 4 characters for English).
    Used to estimate Claude API costs before making calls.
    """
    return len(text) // 4
