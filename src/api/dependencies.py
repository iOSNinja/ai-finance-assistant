"""
src/api/dependencies.py — Shared dependencies (singletons, factories).

FastAPI's 'Depends(...)' system reads from this module. We declare each
dependency as a function; FastAPI calls it for each request that needs it.

For expensive-to-create singletons (the assistant, the semantic cache),
we cache them at module level so they're built once at startup.
"""

from functools import lru_cache

from src.core.config import embeddings
from src.main import FinnieAIFinanceAssistant
from src.observability.cost_tracker import CostTracker
from src.observability.semantic_cache import SemanticCache


@lru_cache(maxsize=1)
def get_assistant() -> FinnieAIFinanceAssistant:
    """Singleton FinnieAIFinanceAssistant — boot once, reuse for every request.

    The @lru_cache decorator means the function body runs at most once.
    Subsequent calls return the cached instance instantly. This is the
    cleanest Python way to express "module-level singleton."
    """
    return FinnieAIFinanceAssistant()


@lru_cache(maxsize=1)
def get_semantic_cache() -> SemanticCache:
    """Shared SemanticCache for the API (one cache for all requests)."""
    return SemanticCache(
        embeddings=embeddings,
        threshold=0.75,  # calibrated against text-embedding-3-small
        ttl_seconds=3600.0,
        max_size=200,
    )


@lru_cache(maxsize=1)
def get_daily_tracker() -> CostTracker:
    """Process-wide daily cost tracker for demo budget enforcement.

    Lifetime: shared across ALL requests in this FastAPI process.
    Resets on container restart (acceptable: max budget per restart is daily_budget_usd).

    Why process-wide vs per-session: a browser refresh cannot bypass this.
    A bot hitting the API cannot reset this. Multiple users share ONE budget.
    """
    return CostTracker(
        daily_budget_usd=1.50,  # demo budget — enough for ~300 queries
        per_query_alert_usd=0.05,  # flag any unusually expensive single query
    )
