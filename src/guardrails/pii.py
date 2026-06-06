"""
src/guardrails/pii.py — Presidio-based PII detection and redaction.

Catches what regex misses: person names, addresses, emails, phones,
SSNs, US driver's license, and dates of birth.

DATE_TIME entity is filtered post-detection to ONLY redact when context
suggests a date of birth — preventing false positives on legitimate
tax-year / contribution-year references ("for 2024 the limit is...").

Initialized lazily so import doesn't pay the spaCy load cost unless
guards actually fire.
"""
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Lazy singletons — Presidio engines are expensive to construct
_analyzer = None
_anonymizer = None

ENTITY_TYPES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "CREDIT_CARD",
    "US_BANK_NUMBER",
    "US_DRIVER_LICENSE",
    "LOCATION",
    "DATE_TIME",        # kept; filtered post-hoc to DOB-context-only
    "IP_ADDRESS",
    "IBAN_CODE",
]

# Phrases that, when found IMMEDIATELY BEFORE a DATE_TIME match,
# indicate the date is a date-of-birth (worth redacting) rather than
# a tax year / contribution year / general date reference (not PII).
DOB_CONTEXT_MARKERS = [
    "born on", "born in", "born:",
    "dob", "d.o.b",
    "date of birth", "birth date", "birthdate",
    "birthday",
    "my birth",
]


def _get_engines():
    """Lazy-init Presidio engines on first use."""
    global _analyzer, _anonymizer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        logger.info("Initializing Presidio engines (one-time cost)")
        _analyzer = AnalyzerEngine()
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer


def _is_dob_context(text: str, match_start: int, window: int = 30) -> bool:
    """True if the DATE_TIME match has a DOB marker within `window` chars before it.

    Example matches (REDACT):
        "I was born on March 15, 1990"        → "born on" in preceding text
        "DOB: 03/15/1990"                     → "DOB" in preceding text
        "My birthday is January 1"            → "birthday" in preceding text

    Example non-matches (KEEP — not PII for tax tutor):
        "For 2024 the contribution limit is..."
        "Tax year 2023 returns"
        "What's the limit for 2024?"
        "March 15, 2024 deadline"
    """
    pre = text[max(0, match_start - window):match_start].lower()
    return any(marker in pre for marker in DOB_CONTEXT_MARKERS)


def redact_pii(text: str, score_threshold: float = 0.5) -> tuple[str, list[dict]]:
    """Run Presidio on text, return (anonymized_text, audit_list).

    DATE_TIME entities are kept ONLY if preceded by DOB context — keeps
    Presidio from incorrectly redacting tax years and contribution years
    that legitimately appear in finance education answers.
    """
    if not text:
        return text, []

    try:
        analyzer, anonymizer = _get_engines()
        results = analyzer.analyze(
            text=text,
            language="en",
            entities=ENTITY_TYPES,
            score_threshold=score_threshold,
        )
        if not results:
            return text, []

        # Filter: drop DATE_TIME matches that aren't in DOB context
        filtered = []
        for r in results:
            if r.entity_type == "DATE_TIME" and not _is_dob_context(text, r.start):
                logger.debug("DATE_TIME match dropped — no DOB context",
                             extra={"snippet": text[r.start:r.end][:30]})
                continue
            filtered.append(r)

        if not filtered:
            return text, []

        audit = [
            {
                "type": r.entity_type,
                "score": round(r.score, 3),
                "snippet": text[r.start:r.end][:40],
            }
            for r in filtered
        ]

        anonymized = anonymizer.anonymize(text=text, analyzer_results=filtered)
        return anonymized.text, audit

    except Exception as e:
        logger.error("Presidio PII redaction failed", extra={
            "error_type": type(e).__name__, "error": str(e),
        })
        return text, []