"""
src/guardrails/input_guard.py — Layered input safety (cheapest first).
"""
from dataclasses import dataclass, field
from typing import Literal

from openai import OpenAI

from src.guardrails.injection_classifier import is_injection
from src.guardrails.patterns import (
    INJECTION_PATTERNS, MAX_QUERY_LEN, MIN_QUERY_LEN,
)
from src.guardrails.pii import redact_pii
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_openai_client = OpenAI()


@dataclass
class InputGuardResult:
    is_safe: bool
    reason: str
    category: Literal[
        "ok", "too_long", "too_short", "prompt_injection",
        "moderation_flagged", "llm_classifier_flagged",
    ]
    # NEW: cleaned query (post-Presidio) and audit of what was redacted
    cleaned_query: str = ""
    input_redactions: list[dict] = field(default_factory=list)


def check_input(query: str) -> InputGuardResult:
    """Run all input guards in cost-ascending order. Returns blocked OR redacted result."""

    # Step 1 — length
    if len(query) < MIN_QUERY_LEN:
        logger.info("Input blocked", extra={
            "guard_type": "length", "category": "too_short"})
        return InputGuardResult(False, "Query too short", "too_short")
    if len(query) > MAX_QUERY_LEN:
        logger.info("Input blocked", extra={
            "guard_type": "length", "category": "too_long",
            "query_len": len(query)})
        return InputGuardResult(False, "Query too long", "too_long")

    # Step 2 — regex injection patterns
    for pat in INJECTION_PATTERNS:
        match = pat.search(query)
        if match:
            logger.info("Input blocked", extra={
                "guard_type": "regex",
                "category": "prompt_injection",
                "pattern_matched": match.group(0)[:60]})
            return InputGuardResult(
                False, "Regex injection match", "prompt_injection")

    # Step 3 — OpenAI Moderation (fail-open)
    try:
        response = _openai_client.moderations.create(
            model="omni-moderation-latest", input=query)
        result = response.results[0]
        if result.flagged:
            flagged = [k for k, v in result.categories.model_dump().items() if v]
            logger.info("Input blocked", extra={
                "guard_type": "moderation",
                "category": "moderation_flagged",
                "flagged_categories": flagged})
            return InputGuardResult(
                False, f"Moderation: {','.join(flagged)}", "moderation_flagged")
    except Exception as e:
        logger.warning("Moderation API error — failing open", extra={
            "error_type": type(e).__name__, "error": str(e)[:200]})

    # Step 4 — LLM injection classifier (fail-open)
    injected, _ = is_injection(query)
    if injected:
        logger.info("Input blocked", extra={
            "guard_type": "llm_classifier",
            "category": "llm_classifier_flagged"})
        return InputGuardResult(
            False, "LLM classifier flagged injection", "llm_classifier_flagged")

    # Step 5 — Presidio PII redaction (REDACT, don't block)
    cleaned, redactions = redact_pii(query)
    if redactions:
        logger.info("Input PII redacted", extra={
            "guard_type": "presidio",
            "redaction_count": len(redactions),
            "entity_types": [r["type"] for r in redactions]})

    return InputGuardResult(
        is_safe=True, reason="ok", category="ok",
        cleaned_query=cleaned, input_redactions=redactions,
    )