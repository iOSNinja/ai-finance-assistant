"""
tests/eval/run_eval.py — CLI entry point to run an evaluation suite against Finnie.

Pattern:
    1. Look up the suite (dataset name, raw examples, ensure_fn, evaluators).
    2. Ensure the dataset exists in LangSmith (lazy create on first use).
    3. Build the FinnieEvalWrapper once (graph build is expensive).
    4. Hand the wrapper + dataset name + evaluators to langsmith.evaluate(),
       which handles parallelism, retries, and dashboard logging.

Usage:
    uv run python -m tests.eval.run_eval routing
    uv run python -m tests.eval.run_eval routing --reps 3 --prefix finnie-v2
"""

import argparse
import sys
from datetime import datetime, timezone

from langsmith import evaluate

from src.utils.logger import setup_logger
from tests.eval.datasets import (
    ROUTING_DATASET_NAME,
    ROUTING_EXAMPLES,
    ensure_routing_dataset,
)
from tests.eval.evaluators import (
    routing_accuracy,
    routing_precision,
    routing_recall,
)
from tests.eval.wrapper import FinnieEvalWrapper

logger = setup_logger(__name__)


# Each suite bundles every piece the runner needs. Adding a new suite is one
# entry — the main() body stays generic.
SUITES: dict[str, dict] = {
    "routing": {
        "dataset_name": ROUTING_DATASET_NAME,
        "examples":     ROUTING_EXAMPLES,
        "ensure_fn":    ensure_routing_dataset,
        "evaluators":   [routing_accuracy, routing_precision, routing_recall],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Finnie evaluation suite.")
    parser.add_argument(
        "suite",
        choices=sorted(SUITES.keys()),
        help="Which evaluation suite to run.",
    )
    parser.add_argument(
        "--reps",
        type=int,
        default=1,
        help="Number of repetitions per example (recommended 3 or more runs).",
    )
    parser.add_argument(
        "--prefix",
        default="finnie-v1",
        help="Experiment name prefix in LangSmith.",
    )
    args = parser.parse_args()

    suite = SUITES[args.suite]
    dataset_name = suite["dataset_name"]
    examples     = suite["examples"]
    ensure_fn    = suite["ensure_fn"]
    evaluators   = suite["evaluators"]

    # Fail fast on empty/misconfigured suite
    if not examples:
        logger.error("Suite '%s' has zero examples — nothing to evaluate.", args.suite)
        return 1

    # Create the dataset on LangSmith if it doesn't exist yet (idempotent)
    ensure_fn()

    # UTC timestamp keeps experiment names unique across re-runs and collaborators
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    experiment_name = f"{args.prefix}-{args.suite}-{timestamp}"

    logger.info(
        "Starting eval: suite=%s dataset=%s examples=%d reps=%d experiment=%s",
        args.suite, dataset_name, len(examples), args.reps, experiment_name,
    )

    # Build wrapper once
    wrapper = FinnieEvalWrapper()

    # LangSmith pulls examples from the server-side dataset by name, calls
    # wrapper(inputs) per example, then scores each output via the evaluators.
    evaluate(
        wrapper,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_name,
        num_repetitions=args.reps,
        max_concurrency=2,
    )

    # Terminal summary — full table lives in LangSmith
    bar = "=" * 70
    print(f"\n{bar}")
    print(f"Eval complete: {experiment_name}")
    print(bar)
    print(f"Suite:        {args.suite}")
    print(f"Dataset:      {dataset_name}")
    print(f"Examples:     {len(examples)}")
    print(f"Repetitions:  {args.reps}")
    print(f"Total runs:   {len(examples) * args.reps}")
    print(f"\nFull results: https://smith.langchain.com/")
    print(f"{bar}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
