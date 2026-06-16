"""
Smoke test: estimate_tokens() across input formats and models.

Testing scenarios:
  - estimate_tokens accepts plain strings, dict-format messages, BaseMessage lists
  - Pricing scales correctly (gpt-4o ~17x gpt-4o-mini)
  - estimate_cost() (direct from token counts) agrees with estimate_tokens()
  - Unknown model names fall back to gpt-4o-mini pricing without crashing

Run with:
    uv run python scripts/sanity_checks/test_token_counter.py
"""

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage

from src.observability.token_counter import estimate_cost, estimate_tokens

CASES = [
    ("Plain string (short)", "What is an ETF?", "gpt-4o-mini"),
    ("Plain string (long)", "Explain ETFs in detail. " * 100, "gpt-4o-mini"),
    ("Same prompt, gpt-4o (expensive)", "What is an ETF?", "gpt-4o"),
    (
        "LangChain BaseMessage list",
        [
            SystemMessage(content="You are a finance tutor."),
            HumanMessage(content="What is dollar-cost averaging?"),
        ],
        "gpt-4o-mini",
    ),
    (
        "Dict-format messages (OpenAI shape)",
        [
            {"role": "system", "content": "You are a finance tutor."},
            {"role": "user", "content": "What is dollar-cost averaging?"},
        ],
        "gpt-4o-mini",
    ),
    ("Unknown model -> gpt-4o-mini fallback", "What is an ETF?", "imaginary-future-model-v99"),
]

print("=" * 90)
print(f"{'Case':<45} {'In':>5} {'Out':>5} {'$ Total':>16}  Model")
print("-" * 90)
for label, msgs, model in CASES:
    e = estimate_tokens(msgs, model=model)
    print(
        f"{label:<45} {e.input_tokens:>5} {e.estimated_output_tokens:>5} "
        f"${e.estimated_total_cost_usd:>14.8f}  {model}"
    )
print("=" * 90)

# Cross-check: estimate_cost(known counts) should agree with estimate_tokens()
print("\nCross-check (same inputs, two functions):")
e = estimate_tokens("What is an ETF?", model="gpt-4o-mini")
cost_a = e.estimated_total_cost_usd
cost_b = estimate_cost(e.input_tokens, e.estimated_output_tokens, "gpt-4o-mini")
print(f"  estimate_tokens total : ${cost_a:.8f}")
print(f"  estimate_cost (direct): ${cost_b:.8f}")
print(f"  match                 : {abs(cost_a - cost_b) < 1e-10}")

# Price ratio sanity: gpt-4o should be much more expensive than gpt-4o-mini
print("\nPricing ratio sanity:")
mini = estimate_tokens("hello world this is a test", "gpt-4o-mini")
big = estimate_tokens("hello world this is a test", "gpt-4o")
ratio = (
    big.estimated_total_cost_usd / mini.estimated_total_cost_usd
    if mini.estimated_total_cost_usd > 0
    else 0
)
print(f"  gpt-4o-mini: ${mini.estimated_total_cost_usd:.10f}")
print(f"  gpt-4o    : ${big.estimated_total_cost_usd:.10f}")
print(f"  ratio     : {ratio:.1f}x  (expect ~17x)")
