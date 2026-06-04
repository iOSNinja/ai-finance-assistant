"""
tests/eval/evaluators.py - Evaluators that score Finnie's quality
"""

from typing import Any

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# define 3 routing evaluators
    # 1. routing_accuracy - headline metric - strict match
    # 2. routing_precision - catches overrouting(fanning out to multiple agents, when single agent would do - cost waste)
    # 3. routing_recall - catches underrouting(missed agents - quality loss)

# 1. Routing accuracy
# The most critical metric —> wrong routing = wrong answer (regardless of agent quality)
def routing_accuracy(run: Any, example: Any) -> dict:
    """Did the orchestrator dispatch to the right agent(s)?"""

    actual = set(run.outputs.get("route", []))
    expected = set(example.outputs.get("agents", []))

    # strict match: did the system fire exactly the right agent set?
    strict_score = 1.0 if actual == expected else 0.0

    if not expected:
        return {
            "key": "routing_accuracy",
            "score": strict_score,
            "comment": "Empty expected set - check dataset entry.",
        }

    # Calculating Precision, Recall & F1 metrics
    intersect = actual & expected # elements present in both sets

    # precision-> Of the agents fired, what fraction were correct?
    precision = len(intersect) / len(actual) if actual else 0.0 
    # recall -> Of the agents that should have fired, what fraction did?
    recall = len(intersect) / len(expected)
    # harmonic mean of precision & recall
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0

    comment = (
        f"expected={sorted(expected)} actual={sorted(actual)} "
        f"precision={precision:.2f} recall={recall:.2f} f1={f1:.2f}"
    )

    return {
        "key": "routing_accuracy",
        "score": strict_score,
        "comment": comment,
    }

# 2. Routing Precision
def routing_precision(run: Any, example: Any) -> dict:
    """Of agents that fired, how many were expected? (catches over-routing)"""
    actual = set(run.outputs.get("route", []))
    expected = set(example.outputs.get("agents", []))
    if not actual:
        return {"key": "routing_precision", "score": 0.0}
    precision = len(actual & expected) / len(actual)
    return {"key": "routing_precision", "score": precision}

# 3. Routing Recall
def routing_recall(run: Any, example: Any) -> dict:
    """How many of the EXPECTED agents actually fired?"""
    actual = set(run.outputs.get("route", []))
    expected = set(example.outputs.get("agents", []))
    if not expected:
        return {"key": "routing_recall", "score": 0.0}
    recall = len(actual & expected) / len(expected)
    return {"key": "routing_recall", "score": recall}


