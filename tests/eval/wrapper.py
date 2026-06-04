"""
tests/eval/wrapper.py — Adapter that makes Finnie's graph callable by LangSmith's
evaluate() function. The wrapper takes a dict of inputs, runs the graph, and
returns a dict of outputs INCLUDING intermediate state (route, agent responses)
that evaluators need to score against expected values.
"""

import uuid
from typing import Any

from src.utils.logger import setup_logger
from src.workflow.graph import build_graph

logger = setup_logger(__name__)

def _build_initial_state(query: str) -> dict:
    """Reset all per-agent buffers. Same shape as main.py's ask() does."""
    return {
        "user_query":         query,
        "route":              [],
        "is_finance_query":   True,
        "qa_messages":        [],
        "tax_messages":       [],
        "goal_messages":      [],
        "portfolio_messages": [],
        "market_messages":    [],
        "news_messages":      [],
        "qa_response":        "",
        "tax_response":       "",
        "goal_response":      "",
        "portfolio_response": "",
        "market_response":    "",
        "news_response":      "",
        "final_answer":       "",
    }


class FinnieEvalWrapper:
    """Build the graph once, invoke it per eval example with isolated thread IDs."""

    def __init__(self):
        logger.info("Building graph for eval wrapper")
        self.graph = build_graph()

    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the graph and return the fields evaluators care about. 

        LangSmith calls this func with {"query": "...} per example in the dataset.
        """
        query = inputs["query"]

        # Each eval invocation gets a fresh thread_id so checkpointer state
        # doesn't leak across examples
        thread_id = f"eval-{uuid.uuid4().hex[:8]}"

        config = {
            "configurable": {"thread_id": thread_id},
            "tags": ["env:eval", "surface:eval"],
            "metadata": {"eval_thread_id": thread_id},
            "run_name": f"eval.query: {query[:60]}",
        }

        try:
            final = self.graph.invoke(_build_initial_state(query), config=config)
        except Exception as e:
            logger.error("Eval invocation failed: %s: %s", type(e).__name__, e)
            return {
                "route":              [],
                "final_answer":       f"[ERROR] {type(e).__name__}: {e}",
                "qa_response":        "",
                "tax_response":       "",
                "goal_response":      "",
                "portfolio_response": "",
                "market_response":    "",
                "news_response":      "",
                "error":              True,
            }

        # Return the fields evaluators care about
        return {
            "route":              final.get("route", []),
            "final_answer":       final.get("final_answer", ""),
            "qa_response":        final.get("qa_response", ""),
            "tax_response":       final.get("tax_response", ""),
            "goal_response":      final.get("goal_response", ""),
            "portfolio_response": final.get("portfolio_response", ""),
            "market_response":    final.get("market_response", ""),
            "news_response":      final.get("news_response", ""),
            "is_finance_query":   final.get("is_finance_query", True),
        }