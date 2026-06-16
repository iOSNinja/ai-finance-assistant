from __future__ import annotations
import pytest

from src.observability.cost_tracker import CostTracker, CostRecord

@pytest.fixture
def fresh_tracker() -> CostTracker:
    return CostTracker(
        daily_budget_usd=5.00,
        per_query_alert_usd=0.10,
    )

@pytest.fixture
def tight_budget_tracker() -> CostTracker:
    return CostTracker(
        daily_budget_usd=0.001, # 0.1 cent daily
        per_query_alert_usd=0.0001, # 0.01 cent per call
    )

@pytest.fixture
def sample_record() -> CostRecord:
    return CostRecord(
        trace_id="t01abc",
        agent_name="qa_agent",
        model="gpt-4o-mini",
        prompt_tokens=100,
        completion_tokens=40,
        cost_usd=0.000039,
        latency_ms=1234.5,
    )

@pytest.fixture
def make_record():
    """Factory fixture: returns a function that builds CostRecords with overrides.
    """
    
    def _factory(**overrides) -> CostRecord:
        defaults = dict(
            trace_id="t01abc",
            agent_name="qa_agent",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=40,
            cost_usd=0.000039,
            latency_ms=1234.5,
        )
        defaults.update(overrides)
        return CostRecord(**defaults)
    return _factory
