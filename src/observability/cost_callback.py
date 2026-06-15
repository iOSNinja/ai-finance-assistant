"""
src/observability/cost_callback.py — LangChain BaseCallbackHandler for cost tracking.

How it integrates:
  LangChain emits on_llm_start / on_llm_end events around every LLM call.
  Our handler listens for both:
    - on_llm_start records the start time
    - on_llm_end extracts token usage, builds a CostRecord, and pushes it
      into the ContextVar-bound CostTracker

Agent attribution:
  Every LLM call already passes config={"tags": ["agent:qa", ...]} in Finnie's
  code. Our handler reads these tags to attribute the call to a specific
  agent. Falls back to "unknown" if no agent tag is present.
"""
from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.observability.context import get_current_tracker
from src.observability.cost_tracker import CostRecord
from src.observability.token_counter import estimate_cost


class CostTrackingCallback(BaseCallbackHandler):
    """LangChain callback that records cost for every LLM call automatically."""

    def __init__(self) -> None:
        super().__init__()
        # Map from run_id -> start time, so we can compute latency at on_llm_end.
        # Indexed by run_id because async tasks can interleave starts/ends.
        self._start_times: dict[UUID, float] = {}

    # on_llm_start: stash the start time keyed by this call's run_id
    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._start_times[run_id] = time.perf_counter()

    # on_llm_end: build a CostRecord and push to the bound tracker
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # 🪲 TEMPORARY DEBUG — remove after diagnosing
        print(f"[cost_callback] tags={tags} metadata={metadata}")

        # If no tracker is bound, drop the record — this just means we're
        # outside a 'with cost_tracker_for_request()' block (e.g., during
        # standalone scripts or tests that don't care about cost).
        tracker = get_current_tracker()
        if tracker is None:
            return

        # Compute latency from the start time we stashed in on_llm_start
        start = self._start_times.pop(run_id, None)
        latency_ms = (time.perf_counter() - start) * 1000 if start else 0.0

        # LangChain stores token usage in a standard place: llm_output.token_usage.
        # Different providers structure this slightly differently — for OpenAI
        # it's {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}.
        usage = (response.llm_output or {}).get("token_usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))

        # Pull model name from the same llm_output dict
        model = (response.llm_output or {}).get("model_name", "unknown")

        # Pull agent name from the tags ("agent:qa") that Finnie code already passes
        agent_name = _extract_agent_name(tags, metadata)

        # Convert tokens to $ using the pricing table we built earlier
        cost = estimate_cost(prompt_tokens, completion_tokens, model)

        # Build and record
        tracker.record(CostRecord(
            trace_id=str(run_id)[:8],     # short prefix of the LangChain run UUID
            agent_name=agent_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_ms=round(latency_ms, 1),
        ))


def _extract_agent_name(
    tags: list[str] | None,
    metadata: dict[str, Any] | None,
) -> str:
    """Find the 'agent:<name>' tag and return the name part.

    Falls back to metadata['agent_name'] if present, otherwise 'unknown'.
    """
    if tags:
        for t in tags:
            if t.startswith("agent:"):
                return t.split(":", 1)[1]     # "agent:qa" -> "qa"
    if metadata and "agent_name" in metadata:
        return str(metadata["agent_name"])
    return "unknown"