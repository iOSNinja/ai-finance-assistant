"""
tests/eval/cache_calibration/calibrate.py — Threshold sweep for SemanticCache.

What it does:
  1. Embeds every unique query in the labeled dataset (once — reused for all thresholds)
  2. Computes cosine similarity for every labeled pair
  3. Sweeps thresholds from 0.40 → 0.95 (configurable)
  4. At each threshold, computes confusion matrix → precision, recall, F1
  5. Recommends the highest threshold with zero false positives + acceptable recall

Run with:
    uv run python -m tests.eval.cache_calibration.calibrate
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from dotenv import load_dotenv

load_dotenv()

from src.core.config import embeddings
from tests.eval.cache_calibration.dataset import PAIRS, CalibrationPair


@dataclass(frozen=True, slots=True)
class ThresholdResult:
    """Confusion matrix + derived metrics at a single threshold."""

    threshold: float
    tp: int  # equivalent pairs correctly hit
    fp: int  # distinct/unrelated pairs incorrectly hit (DANGER)
    tn: int  # distinct/unrelated pairs correctly missed
    fn: int  # equivalent pairs incorrectly missed (slow but safe)

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        denom = p + r
        return 2 * p * r / denom if denom else 0.0


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def calibrate(
    pairs: list[CalibrationPair],
    thresholds: list[float] | None = None,
) -> list[ThresholdResult]:
    """Run the dataset through each candidate threshold. Returns per-threshold metrics."""
    if thresholds is None:
        thresholds = [round(t, 2) for t in np.arange(0.40, 0.96, 0.05)]

    # Embed every unique query ONCE — reused for all thresholds
    unique_queries = set()
    for p in pairs:
        unique_queries.add(p.query_a)
        unique_queries.add(p.query_b)

    print(f"Embedding {len(unique_queries)} unique queries...")
    query_to_vec: dict[str, np.ndarray] = {
        q: np.array(embeddings.embed_query(q), dtype=np.float32) for q in unique_queries
    }
    print(f"  done. (cost: ~${len(unique_queries) * 0.00002:.5f} for text-embedding-3-small)")

    # Compute similarity for every labeled pair (threshold-independent)
    pair_sims: list[tuple[CalibrationPair, float]] = [
        (p, _cosine(query_to_vec[p.query_a], query_to_vec[p.query_b])) for p in pairs
    ]

    # For each threshold, classify every pair → fill confusion matrix
    results: list[ThresholdResult] = []
    for threshold in thresholds:
        tp = fp = tn = fn = 0
        for pair, sim in pair_sims:
            predicted_hit = sim >= threshold
            should_hit = pair.label == "equivalent"
            if predicted_hit and should_hit:
                tp += 1
            elif predicted_hit and not should_hit:
                fp += 1
            elif not predicted_hit and not should_hit:
                tn += 1
            elif not predicted_hit and should_hit:
                fn += 1
        results.append(ThresholdResult(threshold, tp, fp, tn, fn))

    return results


def recommend_threshold(
    results: list[ThresholdResult],
    min_recall: float = 0.70,
) -> ThresholdResult:
    """Recommend the highest threshold with ZERO false positives and recall ≥ min_recall.

    Why this policy: in finance/finance-ed, false positives mean wrong answers to users.
    We optimize for safety (zero FPs) FIRST, then take whatever recall is achievable.
    If no threshold achieves zero FPs at the recall floor, we report the best F1 instead.
    """
    safe = [r for r in results if r.fp == 0 and r.recall >= min_recall]
    if safe:
        return max(safe, key=lambda r: r.threshold)  # highest safe threshold (most conservative)
    # No threshold meets both criteria — recommend best F1 instead, with a warning
    return max(results, key=lambda r: r.f1)


def print_report(results: list[ThresholdResult], recommended: ThresholdResult) -> None:
    """Tabular report + recommendation."""
    print()
    print("=" * 80)
    print(
        f"{'Threshold':>10}  {'TP':>4}  {'FP':>4}  {'TN':>4}  {'FN':>4}  "
        f"{'Precision':>10}  {'Recall':>8}  {'F1':>6}  {'Verdict':>8}"
    )
    print("-" * 80)
    for r in results:
        verdict = ""
        if r is recommended:
            verdict = "← PICK"
        elif r.fp > 0:
            verdict = "(unsafe)"
        elif r.recall < 0.50:
            verdict = "(low recall)"
        print(
            f"{r.threshold:>10.2f}  {r.tp:>4}  {r.fp:>4}  {r.tn:>4}  {r.fn:>4}  "
            f"{r.precision:>10.2f}  {r.recall:>8.2f}  {r.f1:>6.2f}  {verdict:>8}"
        )
    print("=" * 80)
    print()
    print("RECOMMENDATION")
    print(f"  Use threshold = {recommended.threshold:.2f}")
    print("  Expected behavior:")
    print(
        f"    • Catches {recommended.tp}/{recommended.tp + recommended.fn} legitimate paraphrases ({recommended.recall:.0%} recall)"
    )
    print(f"    • Wrong answers to user: {recommended.fp} (FALSE POSITIVES)")
    print(f"    • Misses {recommended.fn} paraphrases (slower but correct)")
    print()


def main() -> None:
    results = calibrate(PAIRS)
    recommended = recommend_threshold(results, min_recall=0.70)
    print_report(results, recommended)


if __name__ == "__main__":
    main()
