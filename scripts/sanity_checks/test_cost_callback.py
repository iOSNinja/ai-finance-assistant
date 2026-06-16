"""
Smoke test: CostTrackingCallback captures real LLM call costs via ContextVar.

Testing whether:
  - The callback fires on every LLM call when installed on a ChatOpenAI instance
  - It correctly identifies agent_name from tags (e.g., "agent:qa")
  - Real token counts and $ cost get populated from LangChain's standardized
    llm_output.token_usage
  - The ContextVar binding (cost_tracker_for_request) isolates per-request state

Run with:
    uv run python scripts/sanity_checks/test_cost_callback.py
"""
from dotenv import load_dotenv; load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.observability.context import cost_tracker_for_request
from src.observability.cost_callback import CostTrackingCallback


# Build a tiny test LLM with our callback installed
callback = CostTrackingCallback()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, callbacks=[callback])

# A few calls tagged with different agent names — simulates orchestrator + qa + tax
TEST_CALLS = [
    ("orchestrator", "Is the next message a finance question or not? 'What is an ETF?'"),
    ("qa_agent",     "Explain ETF in one short sentence."),
    ("tax_agent",    "What is the 2024 401(k) contribution limit, in one sentence?"),
]

with cost_tracker_for_request() as tracker:
    for agent_name, query in TEST_CALLS:
        print(f"Invoking {agent_name}...")
        llm.invoke(
            [SystemMessage(content="You are a concise finance tutor. One sentence max."),
             HumanMessage(content=query)],
            config={"tags": [f"agent:{agent_name}"]},
        )

    print(f"\n{'=' * 70}")
    print(f"Captured {tracker.total_calls} calls, total ${tracker.total_cost_usd:.6f}")
    print(f"\n{'=' * 70}")
    print(f"Captured {tracker.total_calls} calls, total ${tracker.total_cost_usd:.6f}")
    print(f"{'=' * 70}")
    summary = tracker.per_agent_summary()
    print(f"{'Agent':<15} {'Calls':>6} {'In':>8} {'Out':>8} {'Total $':>14}")
    print("-" * 60)
    for agent, stats in sorted(summary.items()):
        print(f"  {agent:<13} {stats['call_count']:>6} "
            f"{stats['total_prompt_tokens']:>8} "
            f"{stats['total_completion_tokens']:>8} "
            f"${stats['total_cost_usd']:>13.6f}")

    # Cross-check: dropping out of the context unbinds the tracker
    
# Outside the 'with' block — the tracker should be unbound now
from src.observability.context import get_current_tracker
print(f"\nAfter exiting `with`, get_current_tracker() returns: {get_current_tracker()}")
print("(should be None)")