"""
src/observability/context.py — Request-scoped CostTracker via ContextVar.

Why a ContextVar (not a global, not a thread-local):
  - Each user query needs its own isolated tracker
  - LangGraph schedules nodes as async tasks; thread-local doesn't survive
    task switches
  - ContextVar is the async-safe way to scope per-request state.
    It's what LangChain's own LangSmith client uses internally.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from src.observability.cost_tracker import CostTracker

# The slot that holds the currently-active CostTracker for the running request.
# Default is None — code outside a 'with cost_tracker_for_request()' block
# will read None and just skip tracking (zero overhead, no errors).
_current_tracker: ContextVar[CostTracker | None] = ContextVar(
    "finnie_cost_tracker", default=None
)

def get_current_tracker() -> CostTracker | None:
    """Read the active tracker for the current request (or None if unbound)."""
    return _current_tracker.get()


@contextmanager
def cost_tracker_for_request(
    daily_budget_usd: float = 5.00,
    per_query_alert_usd: float = 0.10,
    tracker: CostTracker | None = None,
) -> Iterator[CostTracker]:
    """Bind a CostTracker for the duration of a `with` block.

    If `tracker` is provided, bind it (useful for accumulating across queries
    in a UI session). Otherwise create a fresh CostTracker with the budget
    parameters.

    Usage (one-shot, fresh tracker):
        with cost_tracker_for_request() as tracker:
            graph.invoke(state)

    Usage (accumulate across queries):
        with cost_tracker_for_request(tracker=session_tracker):
            graph.invoke(state)
    """
    if tracker is None:
        tracker = CostTracker(
            daily_budget_usd=daily_budget_usd,
            per_query_alert_usd=per_query_alert_usd,
        )
    token = _current_tracker.set(tracker)
    try:
        yield tracker
    finally:
        _current_tracker.reset(token)