"""
Smoke test: SemanticCache handles hits, misses, paraphrases, TTL, eviction.

Testing whether:
  - Exact-same query hits cache after put()
  - Paraphrased query hits via cosine similarity
  - Unrelated query misses cleanly
  - TTL expires entries after ttl_seconds
  - max_size triggers FIFO eviction
  - hit_rate, size, stats() all work

Run with:
    uv run python scripts/sanity_checks/test_semantic_cache.py
"""

from dotenv import load_dotenv

load_dotenv()

import time

from src.core.config import embeddings
from src.observability.semantic_cache import SemanticCache

# Build a tight cache for quick testing
cache = SemanticCache(
    embeddings=embeddings,
    # threshold=0.85,        # a bit looser so paraphrases hit reliably
    threshold=0.60,  # tuned for short queries — paraphrases hit, unrelated misses
    ttl_seconds=2.0,  # short — so we can demo TTL fast
    max_size=10,
)

print("=" * 70)
print("Phase 1 — hits, misses, paraphrases")
print("=" * 70)

# 1. First lookup — should miss (empty cache)
r1 = cache.get("What is an ETF?")
print(
    f"  Q1 'What is an ETF?'                          -> {'HIT' if r1 else 'MISS'}  (expect MISS)"
)

# 2. Store a result
cache.put("What is an ETF?", {"answer": "An ETF is an exchange-traded fund..."})
print(f"  Stored 'What is an ETF?' -> cache size = {cache.size}")

# 3. Exact same query — should HIT
r2 = cache.get("What is an ETF?")
print(f"  Q2 same exact query                           -> {'HIT' if r2 else 'MISS'}  (expect HIT)")

# 4. Paraphrased query — should HIT (semantic match)
r3 = cache.get("Tell me about exchange-traded funds")
print(f"  Q3 paraphrase 'Tell me about ETFs'            -> {'HIT' if r3 else 'MISS'}  (expect HIT)")

# 5. Different but related — depending on threshold may hit
r4 = cache.get("How do exchange-traded funds work?")
print(f"  Q4 'How do ETFs work?'                        -> {'HIT' if r4 else 'MISS'}  (expect HIT)")

# 6. Unrelated — should MISS
r5 = cache.get("What's AAPL trading at right now?")
print(
    f"  Q5 unrelated 'AAPL price'                     -> {'HIT' if r5 else 'MISS'}  (expect MISS)"
)

print(f"\n  Stats: hits={cache.hits} misses={cache.misses} rate={cache.hit_rate:.0%}")

# Phase 2 — TTL eviction
print()
print("=" * 70)
print("Phase 2 — TTL eviction")
print("=" * 70)
print(f"  Waiting {cache.ttl_seconds}s for entries to expire...")
time.sleep(cache.ttl_seconds + 0.5)

r6 = cache.get("What is an ETF?")
print(
    f"  Same query after TTL window                   -> {'HIT' if r6 else 'MISS'}  (expect MISS)"
)
print(f"  Cache size after expiration                   = {cache.size}  (expect 0)")

# Phase 3 — max_size FIFO eviction
print()
print("=" * 70)
print("Phase 3 — max_size FIFO eviction (capacity=3, 4 puts)")
print("=" * 70)

small = SemanticCache(embeddings=embeddings, max_size=3, ttl_seconds=3600)
for q in ["What is an ETF?", "What is a mutual fund?", "What is a bond?", "What is a stock?"]:
    small.put(q, {"q": q})
print(f"  After 4 puts on max_size=3 cache, size = {small.size}")
print(f"  Queries remaining: {[e.query for e in small._entries]}")
print("  (should be the last 3 — the first 'ETF' query evicted)")

# Stats snapshot
print()
print("=" * 70)
print("Final stats snapshot")
print("=" * 70)
for k, v in cache.stats().items():
    print(f"  {k:<14} = {v}")
