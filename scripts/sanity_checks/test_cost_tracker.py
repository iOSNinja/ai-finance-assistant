"""
Smoke test: CostTracker accumulates records and produces per-agent summary.

Testing whether:
  - record() appends and triggers per-call alerts correctly
  - total_cost_usd / total_calls / cache_hit_rate work over multiple records
  - per_agent_summary() groups records by agent_name and computes stats
  - Budget alert fires when cumulative cost crosses 80% of daily budget

Run with:
    uv run python scripts/sanity_checks/test_cost_tracker.py
"""
from src.observability.cost_tracker import CostRecord, CostTracker


# Set a low budget so we can demo the 80% breach alert
tracker = CostTracker(daily_budget_usd=0.05, per_query_alert_usd=0.02)

# Simulate 5 fake LLM calls across 3 agents — realistic shape
fake_calls = [
    CostRecord(trace_id="t01", agent_name="orchestrator", model="gpt-4o-mini",
               prompt_tokens=120, completion_tokens=40, cost_usd=0.0008, latency_ms=410),
    CostRecord(trace_id="t01", agent_name="qa_agent", model="gpt-4o-mini",
               prompt_tokens=950, completion_tokens=300, cost_usd=0.0033, latency_ms=1820),
    CostRecord(trace_id="t02", agent_name="orchestrator", model="gpt-4o-mini",
               prompt_tokens=120, completion_tokens=42, cost_usd=0.0008, latency_ms=380),
    CostRecord(trace_id="t02", agent_name="market_agent", model="gpt-4o-mini",
               prompt_tokens=400, completion_tokens=200, cost_usd=0.0021, latency_ms=2100,
               cache_hit=True),     # this one was served from cache
    CostRecord(trace_id="t03", agent_name="synthesizer", model="gpt-4o",
               prompt_tokens=2500, completion_tokens=900, cost_usd=0.0225, latency_ms=4500),
    # the last one is intentionally expensive — should trigger BOTH alerts
]

for r in fake_calls:
    tracker.record(r)

print("=" * 70)
print("OVERALL")
print("=" * 70)
print(f"  total_calls         : {tracker.total_calls}")
print(f"  total_cost_usd      : ${tracker.total_cost_usd:.6f}")
print(f"  avg_cost_per_call   : ${tracker.avg_cost_per_call_usd:.6f}")
print(f"  cache_hit_rate      : {tracker.cache_hit_rate:.0%}")

print(f"\n{'=' * 70}")
print("PER-AGENT BREAKDOWN")
print("=" * 70)
summary = tracker.per_agent_summary()
print(f"{'Agent':<16} {'Calls':>6} {'Total $':>12} {'Avg $':>10} "
      f"{'Tokens':>8} {'Avg ms':>10} {'Cache hits':>12}")
print("-" * 70)
for agent, stats in sorted(summary.items()):
    print(f"{agent:<16} {stats['call_count']:>6} "
          f"${stats['total_cost_usd']:>11.6f} "
          f"${stats['avg_cost_usd']:>9.6f} "
          f"{stats['total_tokens']:>8} "
          f"{stats['avg_latency_ms']:>9}ms "
          f"{stats['cache_hits']:>12}")

print(f"\n{'=' * 70}")
print(f"ALERTS ({len(tracker.alerts)})")
print("=" * 70)
for a in tracker.alerts:
    print(f"  - {a}")

print(f"\n  Expected: 1 HIGH COST alert (synthesizer call > $0.02)")
print(f"  Expected: 1 BUDGET WARNING (total > 80% of $0.05)")