"""
src/api/dependencies.py — Shared dependencies (singletons, factories).

FastAPI's 'Depends(...)' system reads from this module. We declare each
dependency as a function; FastAPI calls it for each request that needs it.

For expensive-to-create singletons (the assistant, the semantic cache),
we cache them at module level so they're built once at startup.
"""
from functools import lru_cache

from src.main import FinnieAIFinanceAssistant
from src.observability.semantic_cache import SemanticCache
from src.core.config import embeddings


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
    """Shared SemanticCache for the API (one cache for all requests).
    """
    return SemanticCache(
        embeddings=embeddings,
        threshold=0.60,        # calibrated against text-embedding-3-small
        ttl_seconds=3600.0,
        max_size=200,
    )