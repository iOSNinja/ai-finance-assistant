"""
tests/unit/conftest.py — Shared pytest fixtures.

Discovered automatically by pytest — no imports needed in test files. Any
fixture defined here is available to every test under tests/unit/.

Fixtures are isolated by default: each test gets its OWN fresh fixture
instance. That's the whole point — tests don't share state.
"""

from __future__ import annotations

import pytest

from src.observability.cost_tracker import CostRecord, CostTracker


@pytest.fixture
def fresh_tracker() -> CostTracker:
    """A brand-new CostTracker with default budgets."""
    return CostTracker(
        daily_budget_usd=5.00,
        per_query_alert_usd=0.10,
    )


@pytest.fixture
def tight_budget_tracker() -> CostTracker:
    """A CostTracker with tiny thresholds so alerts fire easily in tests."""
    return CostTracker(
        daily_budget_usd=0.001,  # 0.1 cent daily
        per_query_alert_usd=0.0001,  # 0.01 cent per call
    )


@pytest.fixture
def sample_record() -> CostRecord:
    """A canonical CostRecord — small, cheap, qa_agent."""
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

    Used when one test needs many slightly-different records:
        def test_X(make_record):
            r1 = make_record(agent_name="qa")
            r2 = make_record(agent_name="tax", cost_usd=0.5)
    """

    def _factory(**overrides) -> CostRecord:
        defaults = {
            "trace_id": "t01abc",
            "agent_name": "qa_agent",
            "model": "gpt-4o-mini",
            "prompt_tokens": 100,
            "completion_tokens": 40,
            "cost_usd": 0.000039,
            "latency_ms": 1234.5,
        }
        defaults.update(overrides)
        return CostRecord(**defaults)

    return _factory
