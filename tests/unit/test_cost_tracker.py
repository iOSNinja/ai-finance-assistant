"""
unit tests for CostTracker 
"""

from __future__ import annotations
from src.observability.cost_tracker import CostRecord

import pytest

class TestCostTrackerAccumulation:
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