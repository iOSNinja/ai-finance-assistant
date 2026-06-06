"""
src/guardrails/input_guard.py — Pre-orchestrator input safety.

Three guards, cheapest first:
  1. Length bounds (~0ms)
  2. Prompt-injection regex (~1ms)
  3. OpenAI Moderation API (~100ms, free)
"""
from dataclasses import dataclass
from typing import Literal

from openai import OpenAI

from src.guardrails.patterns import (
    INJECTION_PATTERNS, MAX_QUERY_LEN, MIN_QUERY_LEN,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_openai_client = OpenAI()


@dataclass
class InputGuardResult:
    is_safe: bool
    reason: str   # for AUDIT log only; never shown to user
    category: Literal["ok", "too_long", "too_short", "prompt_injection", "moderation_flagged"]


def check_input(query: str) -> InputGuardResult:
    logger.info(f"check_input: input_query: {query}")
    """Run all input guards in cost-ascending order. First failure wins."""
    # Guard 1 — length
    if len(query) < MIN_QUERY_LEN:
        logger.info("Input blocked",
                    extra={"guard_type": "length", "category": "too_short"})
        return InputGuardResult(False, "Query is empty.", "too_short")
    if len(query) > MAX_QUERY_LEN:
        logger.info("Input blocked",
                    extra={"guard_type": "length", "category": "too_long",
                           "query_len": len(query)})
        return InputGuardResult(False, "Query exceeds maximum length.", "too_long")

    # Guard 2 — prompt-injection regex
    logger.info("Checking for prompt-injection regex...")
    for pat in INJECTION_PATTERNS:
        match = pat.search(query)
        if match:
            logger.info("Input blocked",
                        extra={"guard_type": "regex",
                               "category": "prompt_injection",
                               "pattern_matched": match.group(0)[:60]})
            return InputGuardResult(
                False, "Prompt-injection pattern detected.", "prompt_injection"
            )
        else:
            logger.info("prompt-injection regex check passed!")

    # Guard 3 — OpenAI Moderation API (fail-open on error)
    try:
        logger.info("Checking for OpenAI Moderation API...")
        response = _openai_client.moderations.create(
            model="omni-moderation-latest", input=query
        )
        result = response.results[0]
        if result.flagged:
            flagged = [k for k, v in result.categories.model_dump().items() if v]
            logger.info("Input blocked",
                        extra={"guard_type": "moderation",
                               "category": "moderation_flagged",
                               "flagged_categories": flagged})
            return InputGuardResult(
                False, f"Moderation flagged: {', '.join(flagged)}", "moderation_flagged"
            )
        else:
            logger.info("OpenAI Moderation API check passed!")
    except Exception as e:
        # Fail-open: don't block legitimate users on a transient API error.
        # Regex layer above still catches obvious attacks.
        logger.warning("Moderation API error — failing open",
                       extra={"error_type": type(e).__name__, "error": str(e)})

    logger.debug("Input passed all guards")
    return InputGuardResult(True, "ok", "ok")