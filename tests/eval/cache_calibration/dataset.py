"""
tests/eval/cache_calibration/dataset.py — Labeled query pairs for cache calibration.

LABEL SEMANTICS:
  "equivalent" — Same intent, same answer expected. Cache MUST hit.
  "distinct"   — Related topic, DIFFERENT intent or answer. Cache MUST miss.
                 These are the dangerous false-positive risks.
  "unrelated"  — Completely different topic. Easy miss.

How to extend:
  Every time the cache returns the wrong answer in production, add the
  offending pair here as "distinct". Re-run calibration. The threshold
  may need to rise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class CalibrationPair:
    """One labeled (query_a, query_b) pair for threshold calibration."""

    query_a: str
    query_b: str
    label: Literal["equivalent", "distinct", "unrelated"]
    notes: str = ""


PAIRS: list[CalibrationPair] = [
    # EQUIVALENT — same intent, same answer. Cache SHOULD hit.
    CalibrationPair(
        "What is an ETF?",
        "Tell me about exchange-traded funds",
        "equivalent",
        "Acronym vs full form",
    ),
    CalibrationPair("What is an ETF?", "Explain ETFs", "equivalent"),
    CalibrationPair("What is an ETF?", "What are ETFs?", "equivalent", "Singular vs plural"),
    CalibrationPair("What is a Roth IRA?", "Explain the Roth IRA to me", "equivalent"),
    CalibrationPair("How does compound interest work?", "Explain compound interest", "equivalent"),
    CalibrationPair("How does compound interest work?", "What is compound interest?", "equivalent"),
    CalibrationPair(
        "What is dollar-cost averaging?", "DCA explained", "equivalent", "Common acronym"
    ),
    CalibrationPair(
        "What's the 2024 401(k) contribution limit?",
        "How much can I contribute to my 401k in 2024?",
        "equivalent",
    ),
    CalibrationPair("What is the S&P 500?", "Tell me about the S&P 500 index", "equivalent"),
    CalibrationPair("How do mutual funds work?", "Explain mutual funds", "equivalent"),
    CalibrationPair("What is asset allocation?", "Define asset allocation", "equivalent"),
    CalibrationPair(
        "What is diversification?",
        "Why is diversification important?",
        "equivalent",
        "Definition vs rationale — close enough to share an answer",
    ),
    # DISTINCT — related topic, different intent. Cache MUST miss.
    # These are the dangerous cases. FP here = wrong answer to user.
    CalibrationPair(
        "What is an ETF?",
        "What is a mutual fund?",
        "distinct",
        "Related products, different answers",
    ),
    CalibrationPair(
        "What is a Roth IRA?",
        "What is a Traditional IRA?",
        "distinct",
        "Cousin accounts, tax treatment is opposite",
    ),
    CalibrationPair(
        "What is compound interest?",
        "What is simple interest?",
        "distinct",
        "Related concept, fundamentally different formula",
    ),
    CalibrationPair(
        "What is the S&P 500?", "What is the Dow Jones?", "distinct", "Different indices"
    ),
    CalibrationPair(
        "What is a bond?",
        "What is a Treasury bill?",
        "distinct",
        "Both fixed-income, different vehicle",
    ),
    CalibrationPair(
        "How do mutual funds work?",
        "How do index funds work?",
        "distinct",
        "Subset relationship; answer would differ",
    ),
    CalibrationPair(
        "What is the 2024 401(k) contribution limit?",
        "What is the 2024 IRA contribution limit?",
        "distinct",
        "Different account, different limit",
    ),
    CalibrationPair(
        "What is dollar-cost averaging?",
        "What is value averaging?",
        "distinct",
        "Sound similar; different strategies",
    ),
    CalibrationPair(
        "What is an ETF?", "What is an ESG fund?", "distinct", "Three-letter acronym overlap"
    ),
    CalibrationPair(
        "What is asset allocation?",
        "What is rebalancing?",
        "distinct",
        "Allocation = target. Rebalancing = action",
    ),
    # UNRELATED — completely different topics. Easy miss.
    CalibrationPair("What is an ETF?", "What's AAPL trading at?", "unrelated"),
    CalibrationPair("How does compound interest work?", "Latest news on NVDA", "unrelated"),
    CalibrationPair(
        "What is a Roth IRA?", "How much should I save for a $500K house?", "unrelated"
    ),
    CalibrationPair(
        "What is the S&P 500?",
        "What's the weather in Frisco?",
        "unrelated",
        "Off-topic — should never hit",
    ),
    CalibrationPair(
        "What is dollar-cost averaging?", "Analyze my portfolio: $10K AAPL, $5K BND", "unrelated"
    ),
    CalibrationPair(
        "What is asset allocation?", "How do I report fraud on my account?", "unrelated"
    ),
]
