"""
src/observability/semantic_cache.py — Embedding-similarity LLM result cache.

WHAT IT DOES:
  Caches LLM-graph results keyed by query EMBEDDING similarity (not exact
  string match). When a new query's embedding is close enough (cosine
  similarity ≥ threshold) to a stored one, returns the stored result
  instead of re-running the graph.

GROUNDED IN: SemanticCache pattern. Extended with:
  - NumPy-vectorized cosine similarity (≈50-100x faster than Python loops)
  - TTL — entries expire after `ttl_seconds`
  - Max size with FIFO eviction when full
  - Thread-safe (threading.Lock) for Streamlit re-runs and concurrent access
  - Per-entry hit_count for cache-tuning visibility

WHAT IT INTENTIONALLY DOESN'T DO:
  - Persistence: this is in-process / per-Streamlit-session.
  - Sub-result caching (e.g., per-agent or per-tool): we cache the full
    graph result. That's the largest savings per hit and the simplest
    insertion point.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

import numpy as np


# Cached entry
@dataclass
class CacheEntry:
    """One cached query -> result mapping with embedding + creation time."""
    query:      str
    embedding:  np.ndarray            # shape (D,) — typically 1536 for OpenAI small
    result:     Any                   # whatever the graph returns
    created_at: float = field(default_factory=time.monotonic)
    hit_count:  int   = 0             # increment each time this entry serves a hit


# Cache
class SemanticCache:
    """LRU-bounded, TTL-aware, embedding-similarity-keyed cache for LLM results."""

    def __init__(
        self,
        embeddings,                         # langchain Embeddings (OpenAIEmbeddings, etc.)
        threshold: float = 0.95,            # cosine sim ≥ threshold → cache HIT
        ttl_seconds: float = 3600.0,        # entries older than this are evicted
        max_size: int = 100,                # cap on entries in cache
    ) -> None:
        self._embeddings = embeddings
        self.threshold = threshold
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size

        self._entries: list[CacheEntry] = []
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    # Public API
    def get(self, query: str) -> Any | None:
        """Look up 'query' by semantic similarity. Returns the stored result on HIT, None on MISS."""
        # Compute embedding OUTSIDE the lock — it's an expensive HTTP call;
        # holding the lock around it would serialize every concurrent lookup.
        qvec = self._embed(query)
        now = time.monotonic()

        with self._lock:
            self._evict_expired(now)
            if not self._entries:
                self.misses += 1
                return None

            # Vectorized similarity: one matrix multiply gives us all sims at once
            mat = np.stack([e.embedding for e in self._entries])
            sims = _cosine_similarity_batch(qvec, mat)
            best_idx = int(np.argmax(sims))
            best_sim = float(sims[best_idx])

            if best_sim >= self.threshold:
                entry = self._entries[best_idx]
                entry.hit_count += 1
                self.hits += 1
                return entry.result

            self.misses += 1
            return None

    def put(self, query: str, result: Any) -> None:
        """Store '(query, result)'. Evicts oldest entry if at capacity."""
        embedding = self._embed(query)
        entry = CacheEntry(query=query, embedding=embedding, result=result)
        now = time.monotonic()

        with self._lock:
            self._evict_expired(now)
            # FIFO eviction when at capacity (oldest entry goes first)
            if len(self._entries) >= self.max_size:
                self._entries.pop(0)
            self._entries.append(entry)

    def clear(self) -> None:
        """Drop all entries and reset hit/miss counters."""
        with self._lock:
            self._entries.clear()
            self.hits = 0
            self.misses = 0

    # Read-only properties
    @property
    def hit_rate(self) -> float:
        """Fraction of lookups that hit (0.0 to 1.0)."""
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    @property
    def size(self) -> int:
        """Current entry count."""
        return len(self._entries)

    def stats(self) -> dict:
        """Snapshot of cache stats — safe to call from any thread."""
        with self._lock:
            return {
                "hits":         self.hits,
                "misses":       self.misses,
                "hit_rate":     self.hit_rate,
                "entries":      len(self._entries),
                "max_size":     self.max_size,
                "threshold":    self.threshold,
                "ttl_seconds":  self.ttl_seconds,
            }

    # Internals
    def _embed(self, text: str) -> np.ndarray:
        """Call the embeddings model and return a NumPy float32 vector."""
        vec = self._embeddings.embed_query(text)
        return np.array(vec, dtype=np.float32)

    def _evict_expired(self, now: float) -> None:
        """Drop entries older than ttl_seconds. Caller MUST hold the lock."""
        cutoff = now - self.ttl_seconds
        self._entries = [e for e in self._entries if e.created_at >= cutoff]


# Vectorized cosine similarity helper
def _cosine_similarity_batch(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity between one query vector and N rows of a matrix.

    Args:
        query_vec: shape (D,)
        matrix:    shape (N, D)
    Returns:
        shape (N,) — similarity score in [-1, 1] for each row.
    """
    q_norm = np.linalg.norm(query_vec)
    row_norms = np.linalg.norm(matrix, axis=1)

    # Guard against zero-norm vectors (would divide by zero); treat as zero similarity.
    safe_q = q_norm if q_norm else 1.0
    safe_rows = np.where(row_norms == 0, 1.0, row_norms)

    # matrix @ query_vec produces N dot products in one call
    return (matrix @ query_vec) / (safe_rows * safe_q)