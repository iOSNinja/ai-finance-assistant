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
    "DATE_TIME",  # kept; filtered post-hoc to DOB-context-only
    "IP_ADDRESS",
    "IBAN_CODE",
]

# Phrases that, when found IMMEDIATELY BEFORE a DATE_TIME match,
# indicate the date is a date-of-birth (worth redacting) rather than
# a tax year / contribution year / general date reference (not PII).
DOB_CONTEXT_MARKERS = [
    "born on",
    "born in",
    "born:",
    "dob",
    "d.o.b",
    "date of birth",
    "birth date",
    "birthdate",
    "birthday",
    "my birth",
]


def _get_engines():
    """Lazy-init Presidio engines on first use."""
    global _analyzer, _anonymizer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_anonymizer import AnonymizerEngine

        logger.info("Initializing Presidio engines (one-time cost)")

        # Configure spaCy explicitly with en_core_web_sm (12MB) instead of
        # Presidio's en_core_web_lg default (~400MB). The small model is
        # sufficient for our PII types (SSN, email, phone, names) since
        # most detection is regex-based; the NLP model only helps PERSON
        # entity recognition, which the small model handles fine.
        nlp_engine = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }).create_engine()

        _analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=["en"],
        )
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
    pre = text[max(0, match_start - window) : match_start].lower()
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
                logger.debug(
                    "DATE_TIME match dropped — no DOB context",
                    extra={"snippet": text[r.start : r.end][:30]},
                )
                continue
            filtered.append(r)

        if not filtered:
            return text, []

        audit = [
            {
                "type": r.entity_type,
                "score": round(r.score, 3),
                "snippet": text[r.start : r.end][:40],
            }
            for r in filtered
        ]

        anonymized = anonymizer.anonymize(text=text, analyzer_results=filtered)
        return anonymized.text, audit

    except Exception as e:
        logger.error(
            "Presidio PII redaction failed",
            extra={
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        return text, []


# ──────────────────────────────────────────────────────────────
# OUTPUT-LAYER PII detection (narrower, stricter than input)
# ──────────────────────────────────────────────────────────────
# Philosophy: input-layer Presidio should favor RECALL (strip aggressively;
# false positives are fine because user PII shouldn't reach the LLM).
# Output-layer Presidio should favor PRECISION (only redact when certain,
# because false positives degrade the answer the user actually sees).
#
# So output-layer drops the ambiguous types (PERSON, LOCATION, DATE_TIME,
# US_DRIVER_LICENSE) that frequently false-positive on finance content
# (e.g., "Bitcoin" → PERSON, "Frisco" → LOCATION, "2024" → DATE_TIME).
# What remains are unambiguous high-stakes entities that the LLM should
# NEVER be generating in an educational finance answer.

HIGH_STAKES_OUTPUT_ENTITIES = [
    "US_SSN",
    "CREDIT_CARD",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_BANK_NUMBER",
    "IBAN_CODE",
    # Deliberately omitted: PERSON, LOCATION, DATE_TIME, US_DRIVER_LICENSE
    # Too many false positives on finance content; input layer handles them.
]


def redact_pii_output(text: str, score_threshold: float = 0.85) -> tuple[str, list[dict]]:
    """Tighter Presidio variant for OUTPUT redaction.

    Differences vs redact_pii():
      - Narrower entity list (high-stakes only)
      - Higher default threshold (0.85 vs 0.5) — only act when certain
      - No DOB-context filtering needed (DATE_TIME not in entity list)

    Use this on synthesized answers; use redact_pii() on raw user input.
    """
    if not text:
        return text, []

    try:
        analyzer, anonymizer = _get_engines()
        results = analyzer.analyze(
            text=text,
            language="en",
            entities=HIGH_STAKES_OUTPUT_ENTITIES,
            score_threshold=score_threshold,
        )
        if not results:
            return text, []

        audit = [
            {
                "type": r.entity_type,
                "score": round(r.score, 3),
                "snippet": text[r.start : r.end][:40],
            }
            for r in results
        ]

        anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text, audit

    except Exception as e:
        logger.error(
            "Presidio output redaction failed",
            extra={
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        return text, []
