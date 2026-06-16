"""
src/guardrails/patterns.py — Regex patterns for Finnie's guardrails.

Scope: educational finance tutor. Patterns are deliberately conservative —
false positives degrade UX; false negatives degrade safety.
"""

import re

# INPUT — patterns that BLOCK (prompt injection / jailbreak)
INJECTION_PATTERNS = [
    # "Ignore (all) previous instructions"
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)"),
    # "You are now DAN" / "You are now FinBot"
    re.compile(r"(?i)you\s+are\s+now\s+\w+"),
    # "Disregard your role"
    re.compile(r"(?i)disregard\s+your\s+(role|instructions|prompt)"),
    # "Pretend you have insider info"
    re.compile(r"(?i)pretend\s+(you|to)\s+(are|have|be)\s+"),
    # "Act as a licensed advisor"
    re.compile(r"(?i)act\s+as\s+(a|an)\s+(licensed|certified|professional)\s+"),
    # Known jailbreak labels
    re.compile(r"(?i)\b(dan\s+mode|developer\s+mode|jailbreak)\b"),
    # Bracketed system-prompt injection
    re.compile(r"\[\s*SYSTEM\s*(PROMPT|MESSAGE|INSTRUCTION)\s*[:\]]", re.IGNORECASE),
    # "Skip your disclaimers"
    re.compile(r"(?i)skip\s+(your\s+)?(disclaim|warning|safety|caveat)"),
]

# Hard limits
MAX_QUERY_LEN = 5000
MIN_QUERY_LEN = 2

# OUTPUT — advice-violation patterns (the MOST IMPORTANT guard
# for Finnie — protects against regulatory exposure)
ADVICE_VIOLATION_PATTERNS = [
    # "You should buy/sell AAPL"
    re.compile(r"(?i)you\s+should\s+(buy|sell|invest\s+in|purchase|short)\s+\w+"),
    # "I recommend buying X"
    re.compile(r"(?i)I\s+recommend\s+(buying|selling|investing\s+in|shorting)\s+\w+"),
    # Direct ticker buy/sell
    re.compile(r"(?i)\b(buy|sell|short)\s+(AAPL|MSFT|TSLA|NVDA|GOOGL|AMZN|META|SPY|VTI|QQQ|VOO)\b"),
    # "Guaranteed return" — never a legitimate financial claim
    re.compile(r"(?i)guaranteed?\s+(return|profit|gain|yield|income)"),
    # "Risk-free investment" — same
    re.compile(r"(?i)risk[-\s]?free\s+(investment|return|portfolio)"),
]

# Disclaimer markers — at least one must appear in finance answers
DISCLAIMER_MARKERS = [
    "educational",
    "not financial advice",
    "consult",
    "professional advisor",
    "not personalized",
]

# OUTPUT — light PII safety net
PII_PATTERNS = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
}
