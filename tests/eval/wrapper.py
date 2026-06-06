"""
tests/eval/wrapper.py — Adapter that makes Finnie's graph callable by LangSmith's
evaluate() function. The wrapper takes a dict of inputs, runs the graph, and
returns a dict of outputs INCLUDING intermediate state (route, agent responses)
that evaluators need to score against expected values.
"""

import uuid
import json
from typing import Any

from src.utils.logger import setup_logger
from src.workflow.graph import build_graph
from langchain_core.messages import ToolMessage

logger = setup_logger(__name__)

def _extract_chunks_from_messages(messages: list) -> list[dict]:
    """Walk an agent's messages, find RAG-tool results, parse chunks.

    LangGraph stores tool results as ToolMessage instances whose .content
    is the JSON-serialized return value of the tool. Both finance_qa_search
    and tax_education_search return list[dict] — we deserialize and flatten.
    """
    chunks = []
    for msg in (messages or []):
        if not isinstance(msg, ToolMessage):
            continue
        tool_name = getattr(msg, "name", "")
        if tool_name not in ("finance_qa_search", "tax_education_search"):
            continue
        # Tool result is either already a list/dict OR a JSON string
        try:
            content = msg.content
            parsed = json.loads(content) if isinstance(content, str) else content
            if isinstance(parsed, list):
                chunks.extend(parsed)
        except (json.JSONDecodeError, TypeError):
            # Malformed tool message — skip silently, don't crash the eval
            continue
    return chunks

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
        "is_safe_input":      True,
        "input_block_reason": "",
        "input_block_category": "ok",
        "pii_redactions":       [],
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
                "chunks":             [],
                "chunk_count":        0,
                "error":              True,
                "is_safe_input":      True,
                "input_block_reason": "",
                "input_block_category": "ok",
                "pii_redactions":       [],
            }
        
        # extract chunks from each agent's tool messages
        all_chunks = []
        for msg_key in ("qa_messages", "tax_messages"):
            all_chunks.extend(_extract_chunks_from_messages(final.get(msg_key, [])))

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
            "chunks":             all_chunks,
            "chunk_count":        len(all_chunks),
            "is_finance_query":   final.get("is_finance_query", True),
            "is_safe_input":        final.get("is_safe_input", True),
            "input_block_reason":   final.get("input_block_reason", ""),
            "input_block_category": final.get("input_block_category", "ok"),
            "pii_redactions":       final.get("pii_redactions", []),
        }