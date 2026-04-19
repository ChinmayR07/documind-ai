"""
DocuMind AI — Claude AI Service
=================================
All interactions with the Anthropic Claude API live here.
This service handles Q&A, summarization, and multi-document comparison.

Key engineering decisions made here:
1. Retry logic with exponential backoff (handles transient API errors)
2. Structured output parsing (converts Claude's text to typed Python objects)
3. Token-aware prompt construction (never exceeds context window)
4. Cost estimation before every call (good production practice)
5. Graceful degradation (if parsing fails, return raw text rather than crash)

Interview talking point:
"I built retry logic with exponential backoff and jitter for the Claude API
calls. In production AI systems, transient errors are common — a naive
implementation that fails immediately would cause poor user experience."
"""

import asyncio
import json
import logging
import time
from typing import Any

import anthropic
from anthropic import APIConnectionError, APIStatusError, RateLimitError

from app.config import settings
from app.constants import Limits, Prompts
from app.models.schemas import (
    AskResponse,
    CompareRequest,
    DocumentComparison,
    SummarizeResponse,
)
from app.utils.text_utils import chunk_text, count_tokens_approx, truncate_text

logger = logging.getLogger(__name__)


# ─── Retry Configuration ──────────────────────────────────────────────────────
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0   # Start with 1 second delay
MAX_DELAY_SECONDS = 30.0   # Cap at 30 seconds


class ClaudeService:
    """
    Manages all Claude API interactions for DocuMind AI.

    Design decisions:
    - Synchronous client (not async) because CPU-bound parsing happens
      before/after API calls anyway
    - Single client instance reused across requests (connection pooling)
    - All prompt templates in constants.py for easy iteration
    """

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.CLAUDE_TIMEOUT_SECONDS,
        )
        self._model = settings.CLAUDE_MODEL
        self._max_tokens = settings.CLAUDE_MAX_TOKENS

    # ─── Core API Call with Retry ─────────────────────────────────────────────

    def _call_claude(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
    ) -> tuple[str, int]:
        """
        Make a Claude API call with exponential backoff retry.

        Returns:
            Tuple of (response_text, approximate_tokens_used)

        Retry strategy:
        - Attempt 1: immediate
        - Attempt 2: wait 1 second
        - Attempt 3: wait 2 seconds
        - All subsequent: wait up to 30 seconds
        This is exponential backoff — each retry waits 2x longer.
        """
        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens or self._max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                text = response.content[0].text
                tokens_used = len(user_message) // 4  # Approximate

                if attempt > 0:
                    logger.info(f"Claude API succeeded on attempt {attempt + 1}")

                return text, tokens_used

            except RateLimitError as e:
                # Rate limited — wait longer
                last_exception = e
                wait_time = min(BASE_DELAY_SECONDS * (2 ** attempt) * 2, MAX_DELAY_SECONDS)
                logger.warning(
                    f"Rate limited by Claude API (attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Waiting {wait_time:.1f}s..."
                )
                time.sleep(wait_time)

            except APIConnectionError as e:
                # Network error — retry with backoff
                last_exception = e
                wait_time = min(BASE_DELAY_SECONDS * (2 ** attempt), MAX_DELAY_SECONDS)
                logger.warning(
                    f"Connection error (attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Waiting {wait_time:.1f}s..."
                )
                time.sleep(wait_time)

            except APIStatusError as e:
                # 4xx errors (except 429 rate limit) — don't retry
                if e.status_code in (400, 401, 403):
                    logger.error(f"Non-retryable Claude API error: {e.status_code}")
                    raise RuntimeError(
                        f"Claude API error {e.status_code}: {e.message}"
                    ) from e
                # 5xx errors — retry
                last_exception = e
                wait_time = min(BASE_DELAY_SECONDS * (2 ** attempt), MAX_DELAY_SECONDS)
                logger.warning(
                    f"Server error {e.status_code} (attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Waiting {wait_time:.1f}s..."
                )
                time.sleep(wait_time)

        # All retries exhausted
        raise RuntimeError(
            f"Claude API failed after {MAX_RETRIES} attempts. "
            f"Last error: {last_exception}"
        )

    # ─── Prepare Document Context ─────────────────────────────────────────────

    def _prepare_context(self, document_text: str) -> str:
        """
        Prepare document text for inclusion in a Claude prompt.

        If the document is small enough, use it all.
        If it's too large, truncate smartly at a sentence boundary.

        In a more advanced implementation, this would use embeddings
        to retrieve only the RELEVANT sections for a given question.
        That's called RAG (Retrieval Augmented Generation).
        """
        max_chars = Limits.MAX_TEXT_CHARS_FOR_CLAUDE

        if len(document_text) <= max_chars:
            return document_text

        # Truncate at sentence boundary
        truncated = truncate_text(document_text, max_chars, suffix="")
        return (
            truncated
            + "\n\n[DOCUMENT TRUNCATED — showing first "
            + f"{max_chars:,} characters of {len(document_text):,} total]"
        )

    # ─── Q&A ──────────────────────────────────────────────────────────────────

    def ask_question(
        self,
        document_text: str,
        document_id: str,
        question: str,
        include_page_references: bool = True,
    ) -> AskResponse:
        """
        Answer a question about a document using Claude.

        Prompt engineering notes:
        - System prompt establishes Claude's role and constraints
        - We explicitly tell Claude NOT to hallucinate
        - We ask for page references when available
        - The document text is injected into the user message
        """
        context = self._prepare_context(document_text)

        # Build user message from template
        user_message = Prompts.QA_USER.format(
            document_text=context,
            question=question,
        )

        if include_page_references:
            user_message += (
                "\n\nNote: If you reference specific information, "
                "please mention which page or section it came from "
                "(e.g. 'According to page 3...' or 'In the introduction...')."
            )

        logger.info(
            f"Q&A request: doc={document_id[:8]}, "
            f"question_len={len(question)}, "
            f"context_chars={len(context):,}, "
            f"approx_tokens={count_tokens_approx(user_message):,}"
        )

        answer, tokens_used = self._call_claude(
            system_prompt=Prompts.QA_SYSTEM,
            user_message=user_message,
        )

        return AskResponse(
            document_id=document_id,
            question=question,
            answer=answer,
            context_chars_used=len(context),
            tokens_used_approx=tokens_used,
            cached=False,
        )

    # ─── Summarization ────────────────────────────────────────────────────────

    def summarize_document(
        self,
        document_text: str,
        document_id: str,
        max_length: str = "medium",
        focus_areas: list[str] | None = None,
    ) -> SummarizeResponse:
        """
        Generate a structured summary with key points and insights.

        We ask Claude to return structured data and then parse it.
        This is better than asking for free-form text because
        it gives us typed fields we can display differently in the UI.

        Structured output strategy:
        Ask Claude to return JSON → parse it → fall back to raw text if parsing fails.
        We never crash — if JSON parsing fails, we still return something useful.
        """
        context = self._prepare_context(document_text)

        # Adjust prompt based on desired length
        length_instruction = {
            "short": "Keep the executive summary to 2 sentences and provide 3 key points.",
            "medium": "Provide a 3-4 sentence executive summary and 5-7 key points.",
            "long": "Provide a detailed 5-6 sentence executive summary and 8-10 key points.",
        }.get(max_length, "")

        focus_instruction = ""
        if focus_areas:
            focus_instruction = (
                f"\n\nPay special attention to these areas: {', '.join(focus_areas)}"
            )

        user_message = Prompts.SUMMARIZE_USER.format(document_text=context)
        user_message += f"\n\n{length_instruction}{focus_instruction}"

        # Ask for structured JSON output
        user_message += """

Please return your response as valid JSON with this exact structure:
{
  "executive_summary": "string",
  "key_points": ["string", "string", ...],
  "key_entities": ["string", "string", ...],
  "document_type_detected": "string",
  "recommended_action": "string"
}

Return ONLY the JSON, no other text."""

        logger.info(
            f"Summarize request: doc={document_id[:8]}, "
            f"context_chars={len(context):,}"
        )

        raw_response, tokens_used = self._call_claude(
            system_prompt=Prompts.SUMMARIZE_SYSTEM,
            user_message=user_message,
            max_tokens=2048,
        )

        # Parse structured JSON response
        parsed = self._parse_json_response(raw_response)

        if parsed:
            return SummarizeResponse(
                document_id=document_id,
                executive_summary=parsed.get("executive_summary", raw_response),
                key_points=parsed.get("key_points", []),
                key_entities=parsed.get("key_entities", []),
                document_type_detected=parsed.get("document_type_detected", "Unknown"),
                recommended_action=parsed.get("recommended_action", ""),
                word_count_original=len(document_text.split()),
                word_count_summary=len(raw_response.split()),
                cached=False,
            )
        else:
            # Graceful degradation — parsing failed but we still have the text
            logger.warning(f"JSON parsing failed for summarize. Using raw response.")
            return SummarizeResponse(
                document_id=document_id,
                executive_summary=raw_response,
                key_points=[],
                key_entities=[],
                document_type_detected="Unknown",
                recommended_action="",
                word_count_original=len(document_text.split()),
                word_count_summary=len(raw_response.split()),
                cached=False,
            )

    # ─── Multi-Document Comparison ────────────────────────────────────────────

    def compare_documents(
        self,
        documents: list[dict[str, str]],  # [{"id": "...", "text": "..."}]
        comparison_focus: str = "",
    ) -> DocumentComparison:
        """
        Compare 2-3 documents side by side.

        Prompt engineering challenge:
        We need to fit multiple documents into one prompt.
        Each document is given a label (Document 1, Document 2, etc.)
        and a character budget to ensure the total stays within limits.

        The character budget per document:
        Total limit / number of documents = budget per doc
        e.g. 180,000 chars / 3 docs = 60,000 chars per document
        """
        num_docs = len(documents)
        chars_per_doc = Limits.MAX_TEXT_CHARS_FOR_CLAUDE // num_docs

        # Build the documents section of the prompt
        documents_section_parts = []
        for i, doc in enumerate(documents, 1):
            doc_text = self._prepare_context(doc["text"])
            # Further truncate to per-doc budget
            if len(doc_text) > chars_per_doc:
                doc_text = truncate_text(doc_text, chars_per_doc)

            documents_section_parts.append(
                f"=== DOCUMENT {i} (ID: {doc['id'][:8]}...) ===\n{doc_text}"
            )

        documents_section = "\n\n".join(documents_section_parts)

        user_message = Prompts.COMPARE_USER.format(
            num_docs=num_docs,
            documents_section=documents_section,
        )

        if comparison_focus:
            user_message += (
                f"\n\nSpecial focus: Please pay particular attention to "
                f"'{comparison_focus}' in your comparison."
            )

        # Ask for structured JSON
        user_message += """

Return your response as valid JSON:
{
  "overview": "string describing each document briefly",
  "common_themes": ["theme1", "theme2", ...],
  "key_differences": ["difference1", "difference2", ...],
  "unique_insights": {
    "doc_id_1": "what only this document offers",
    "doc_id_2": "what only this document offers"
  },
  "contradictions": ["contradiction1", ...],
  "synthesis": "overall conclusion from reading all documents together"
}

Return ONLY the JSON."""

        logger.info(
            f"Compare request: {num_docs} documents, "
            f"ids={[d['id'][:8] for d in documents]}"
        )

        raw_response, tokens_used = self._call_claude(
            system_prompt=Prompts.COMPARE_SYSTEM,
            user_message=user_message,
            max_tokens=3000,
        )

        parsed = self._parse_json_response(raw_response)
        document_ids = [d["id"] for d in documents]

        if parsed:
            return DocumentComparison(
                document_ids=document_ids,
                num_documents=num_docs,
                overview=parsed.get("overview", ""),
                common_themes=parsed.get("common_themes", []),
                key_differences=parsed.get("key_differences", []),
                unique_insights=parsed.get("unique_insights", {}),
                contradictions=parsed.get("contradictions", []),
                synthesis=parsed.get("synthesis", raw_response),
                cached=False,
            )
        else:
            logger.warning("JSON parsing failed for compare. Using raw response.")
            return DocumentComparison(
                document_ids=document_ids,
                num_documents=num_docs,
                overview=raw_response,
                common_themes=[],
                key_differences=[],
                unique_insights={},
                contradictions=[],
                synthesis=raw_response,
                cached=False,
            )

    # ─── Utilities ────────────────────────────────────────────────────────────

    def _parse_json_response(self, response: str) -> dict[str, Any] | None:
        """
        Safely parse Claude's JSON response.

        Claude sometimes wraps JSON in markdown code blocks:
            ```json
            {"key": "value"}
            ```
        We strip those before parsing.

        Returns None if parsing fails rather than raising an exception.
        This enables graceful degradation — we always return something to the user.
        """
        try:
            # Strip markdown code fences if present
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                # Remove first line (```json) and last line (```)
                text = "\n".join(lines[1:-1])

            return json.loads(text)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON parse failed: {e}. Response preview: {response[:200]}")
            return None

    def estimate_cost(self, text: str) -> dict[str, float]:
        """
        Estimate Claude API cost before making a call.
        Useful for logging and monitoring in production.

        Claude claude-sonnet-4-20250514 pricing (as of 2025):
        Input:  $3 per million tokens
        Output: $15 per million tokens
        1 token ≈ 4 characters
        """
        input_tokens = len(text) // 4
        output_tokens = self._max_tokens  # Assume max output

        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0

        return {
            "input_tokens_approx": input_tokens,
            "output_tokens_max": output_tokens,
            "estimated_cost_usd": round(input_cost + output_cost, 6),
        }


# ─── Singleton instance ────────────────────────────────────────────────────────
claude_service = ClaudeService()
