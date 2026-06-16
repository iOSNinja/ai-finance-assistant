"""
Unit tests for CostTracker — accumulator, per-agent breakdown, edge-triggered alerts.
"""

from __future__ import annotations
from src.observability.cost_tracker import CostRecord

import pytest

class TestCostTrackerAccumulation:
    """Verifies CostTracker correctly accumulates records and properties."""

    def test_empty_tracker_has_zero_stats(self, fresh_tracker):
        assert fresh_tracker.total_calls == 0
        assert fresh_tracker.total_cost_usd == 0.0
        assert fresh_tracker.avg_cost_per_call_usd == 0.0
        assert fresh_tracker.cache_hit_rate == 0.0

    def test_single_record_updates_totals(self, fresh_tracker, sample_record):
        fresh_tracker.record(sample_record)
        assert fresh_tracker.total_calls == 1
        assert fresh_tracker.total_cost_usd == pytest.approx(0.000039)

    def test_multiple_records_accumulate(self, fresh_tracker, make_record):
        for _ in range(5):
            fresh_tracker.record(make_record(cost_usd=0.001))
        assert fresh_tracker.total_calls == 5
        assert fresh_tracker.total_cost_usd == pytest.approx(0.005)
        assert fresh_tracker.avg_cost_per_call_usd == pytest.approx(0.001)

class TestPerAgentSummary:
    """Verifies per_agent_summary() correctly groups records by agent_name."""

    def test_groups_by_agent(self, fresh_tracker, make_record):
        fresh_tracker.record(make_record(agent_name="qa", cost_usd=0.001))
        fresh_tracker.record(make_record(agent_name="qa", cost_usd=0.002))
        fresh_tracker.record(make_record(agent_name="tax", cost_usd=0.005))

        summary = fresh_tracker.per_agent_summary()

        assert summary["qa"]["call_count"] == 2
        assert summary["qa"]["total_cost_usd"] == pytest.approx(0.003)
        assert summary["tax"]["call_count"] == 1
        assert summary["tax"]["total_cost_usd"] == pytest.approx(0.005)

class TestEdgeTriggeredAlerts:
    """Verifies budget alert fires ONCE per crossing, not on every subsequent call."""

    def test_budget_warning_fires_once(self, tight_budget_tracker, make_record):
        # Each call costs $0.0005 — 0.1¢ budget threshold is 80% = $0.0008
        # After 2 calls (0.0010), we've crossed the threshold
        for _ in range(5):
            tight_budget_tracker.record(make_record(cost_usd=0.0005))

        budget_alerts = [a for a in tight_budget_tracker.alerts if "BUDGET" in a]
        assert len(budget_alerts) == 1, (
            f"Expected exactly 1 BUDGET WARNING, got {len(budget_alerts)}: "
            f"{budget_alerts}"
        )

    def test_high_cost_fires_per_call(self, tight_budget_tracker, make_record):
        # Per-call alert at $0.0001 — each $0.0005 call exceeds it = fires every time
        for _ in range(3):
            tight_budget_tracker.record(make_record(cost_usd=0.0005))

        high_cost_alerts = [a for a in tight_budget_tracker.alerts if "HIGH COST" in a]
        assert len(high_cost_alerts) == 3, (
            "HIGH COST should fire once per individual call exceeding the threshold"
        )

    def test_reset_clears_budget_flag(self, tight_budget_tracker, make_record):
        # Trigger budget warning
        for _ in range(5):
            tight_budget_tracker.record(make_record(cost_usd=0.0005))
        assert any("BUDGET" in a for a in tight_budget_tracker.alerts)

        tight_budget_tracker.reset()

        # After reset, a fresh budget crossing should fire again
        for _ in range(5):
            tight_budget_tracker.record(make_record(cost_usd=0.0005))
        budget_alerts = [a for a in tight_budget_tracker.alerts if "BUDGET" in a]
        assert len(budget_alerts) == 1


class TestImmutableCostRecord:
    """CostRecord is frozen — verify we can't accidentally mutate one."""

    def test_record_is_frozen(self, sample_record):
        with pytest.raises(Exception):    # FrozenInstanceError or AttributeError
            sample_record.cost_usd = 999.99