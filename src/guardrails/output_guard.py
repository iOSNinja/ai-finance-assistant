"""
src/guardrails/output_guard.py — Post-synthesizer output safety.

Three checks:
  1. Advice-violation regex — MOST CRITICAL: protects regulatory line
     between education and personalized advice
  2. Disclaimer presence — verify synthesizer's disclaimer wasn't stripped
  3. PII safety net — defensive regex against training-data leakage

Fail-CLOSED — if anything looks unsafe, redact or replace before user sees.
"""
from dataclasses import dataclass, field

from src.guardrails.patterns import (
    ADVICE_VIOLATION_PATTERNS, DISCLAIMER_MARKERS, PII_PATTERNS,
)
from src.guardrails.pii import redact_pii_output
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class OutputGuardResult:
    text: str                                              # possibly transformed
    advice_violations: list[str] = field(default_factory=list)
    pii_redactions: list[dict] = field(default_factory=list)
    disclaimer_missing: bool = False
    modified: bool = False


def _redact_pii_regex(text: str) -> tuple[str, list[dict]]:
    """Defensive regex PII scrubbing (fast path before Presidio)."""
    redactions = []
    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            redactions.append({"type": pii_type, "count": len(matches)})
            text = pattern.sub(f"[REDACTED_{pii_type}]", text)
    return text, redactions


def _check_advice_violations(text: str) -> list[str]:
    """Find advice-violation pattern matches. Returns snippets for audit."""
    violations = []
    for pat in ADVICE_VIOLATION_PATTERNS:
        match = pat.search(text)
        if match:
            violations.append(match.group(0)[:60])
    return violations


def _has_disclaimer(text: str) -> bool:
    """At least one disclaimer marker must appear in finance responses."""
    text_lower = text.lower()
    return any(marker in text_lower for marker in DISCLAIMER_MARKERS)


def scrub_output(text: str, is_finance_query: bool = True) -> OutputGuardResult:
    """Run all output guards. Returns transformed text + audit fields."""
    if not text:
        return OutputGuardResult(text="")

    original = text

    # Step 1 — regex PII safety net (fast)
    text, regex_redactions = _redact_pii_regex(text)

    # Step 2 — Presidio (high-stakes entities only — SSN/CC/email/phone/bank/IBAN).
    # Drops ambiguous types (PERSON, LOCATION, DATE_TIME) to avoid false positives
    # on finance content (e.g., "Bitcoin"→PERSON, "Frisco"→LOCATION).
    # Input layer is responsible for those — output layer is precision-first.
    text, presidio_redactions = redact_pii_output(text)

    # Combine audit logs
    all_redactions = regex_redactions + [
        {"type": r["type"], "score": r["score"], "via": "presidio"}
        for r in presidio_redactions
    ]

    # Step 3 — advice-violation check
    violations = _check_advice_violations(text)

    # Step 4 — disclaimer presence
    disclaimer_missing = is_finance_query and not _has_disclaimer(text)

    if violations:
        logger.warning("Output guard: advice-violation pattern", extra={
            "guard_type": "advice_violation", "violations": violations})
    if all_redactions:
        logger.info("Output guard: PII redacted", extra={
            "guard_type": "pii_safety_net", "redactions": all_redactions})
    if disclaimer_missing:
        logger.warning("Output guard: disclaimer missing", extra={
            "guard_type": "disclaimer_presence"})

    return OutputGuardResult(
        text=text,
        advice_violations=violations,
        pii_redactions=all_redactions,
        disclaimer_missing=disclaimer_missing,
        modified=(text != original),
    )