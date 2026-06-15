"""
src/observability/cost_tracker.py - Multi-agent cost accounting + budget alerts.

WHAT THIS PROVIDES:
  - CostRecord  : one immutable observation per LLM call
  - CostTracker : accumulator + per-agent summary + budget alerts

DESIGN CHOICES:
  - CostRecord is frozen — observations are facts, never modified post-record
  - CostTracker is mutable — its whole purpose is to accumulate records
  - We record AGENT_NAME (not the user's query) per record — keeps PII out
    of the cost trail. The trace_id is the only handle back to the query.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

# 1. define an immutable CostRecord class -> everytime an LLM call is made, 
# the associated cost tracking is recorded using this CostRecord obj.
@dataclass(frozen=True, slots=True)
class CostRecord:
    """One LLM call's cost + perf observation.
    
    Frozen because an observed measurement is a fact about a past event;
    mutating it would corrupt history. Slots saves memory at scale.
    """

    trace_id:          str            # LangSmith trace ID for correlation
    agent_name:        str            # "orchestrator", "qa_agent", etc.
    model:             str            # "gpt-4o-mini", "gpt-4o"
    prompt_tokens:     int            # actual count (from get_openai_callback)
    completion_tokens: int
    cost_usd:          float
    latency_ms:        float
    cache_hit:         bool = False
    timestamp_iso:     str  = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # computed property
    @property
    def total_tokens(self) -> int:
        """Sum of prompt + completion tokens."""
        return self.prompt_tokens + self.completion_tokens
    

# 2. define CostTracker -> track cost by all LLM calls by the agents & compute summary stats.
@dataclass
class CostTracker:
    """Accumulates CostRecord instances and computes summary stats.
    
    Mutable by design — the whole point is to add records over a session/day.
    Use 'daily_budget_usd' for a soft cap; alerts fire at 80% breach.
    """

    daily_budget_usd:    float = 5.00        # daily $ceiling for alerts
    per_query_alert_usd: float = 0.10        # single-call alert threshold
    records: list[CostRecord] = field(default_factory=list)
    alerts: list[str]         = field(default_factory=list)
    _budget_warned: bool       = False     # edge-trigger flag

    # computed property
    @property
    def total_cost_usd(self) -> float:
        """Sum of $ across all recorded calls."""
        return sum(r.cost_usd for r in self.records)

    def record(self, r: CostRecord) -> None:
        """Add a record and run threshold checks."""

        self.records.append(r)

        # Per-call alert
        if r.cost_usd > self.per_query_alert_usd:
            self.alerts.append(
                f"HIGH COST: ${r.cost_usd:.6f} > ${self.per_query_alert_usd:.6f} "
                f"(trace={r.trace_id}, agent={r.agent_name})"
            )

        # Daily budget warning — edge-triggered: fires ONCE when total crosses
        # 80% of the daily budget, not on every subsequent call.
        if not self._budget_warned and self.total_cost_usd > self.daily_budget_usd * 0.8:
            self.alerts.append(
                f"BUDGET WARNING: ${self.total_cost_usd:.4f} > 80% of "
                f"${self.daily_budget_usd:.2f} daily budget"
            )
            self._budget_warned = True


    # other computed properties
    @property
    def total_calls(self) -> int:
        """How many LLM calls we've observed."""
        return len(self.records)
    
    @property
    def avg_cost_per_call_usd(self) -> float:
        """Average $ spent per LLM call."""
        if not self.records:
            return 0.0
        return self.total_cost_usd / len(self.records)
    
    @property
    def cache_hit_rate(self) -> float:
        """Fraction of calls served from cache (Step 2a will use this)."""
        if not self.records:
            return 0.0
        cache_hits = sum(1 for r in self.records if r.cache_hit)
        return cache_hits / len(self.records)
    
    def per_agent_summary(self) -> dict[str, dict]:
        """Group records by agent_name and compute per-agent stats.

        Returns a dict like:
            {
              "qa_agent": {
                "call_count":     12,
                "total_cost_usd": 0.0234,
                "avg_cost_usd":   0.00195,
                "total_tokens":   4521,
                "avg_latency_ms": 1245.3,
                "cache_hits":     2,
              },
              "orchestrator": {...},
              ...
            }
        """

        by_agent: dict[str, list[CostRecord]] = defaultdict(list)
        for r in self.records:
            by_agent[r.agent_name].append(r)

        summary: dict[str, dict] = {}
        for agent, recs in by_agent.items():
            n = len(recs)
            summary[agent] = {
                "call_count":     n,
                "total_cost_usd": round(sum(r.cost_usd for r in recs), 6),
                "avg_cost_usd":   round(sum(r.cost_usd for r in recs) / n, 6),
                "total_prompt_tokens":    sum(r.prompt_tokens for r in recs),
                "total_completion_tokens": sum(r.completion_tokens for r in recs),
                "total_tokens":   sum(r.total_tokens for r in recs),
                "avg_latency_ms": round(sum(r.latency_ms for r in recs) / n, 1),
                "cache_hits":     sum(1 for r in recs if r.cache_hit),
            }

        return summary
    

    def reset(self) -> None:
        """Clear all records and alerts (for end-of-day reset)."""
        self.records.clear()
        self.alerts.clear()
        self._budget_warned = False