"""
Smoke test for the Orchestrator's routing decisions
"""

from langchain_core.messages import SystemMessage, HumanMessage
from src.agents.orchestrator import routing_llm
from src.agents.prompts import ORCHESTRATOR_PROMPT

TEST_QUERIES = [
    "What is an ETF?",
    "Explain compound interest like I'm 10.",
    "What's AAPL trading at?",
    "Analyze my portfolio.",
    "Roth IRA vs Traditional?",
    "Latest news on NVDA.",
    "I'm 35 saving for retirement at 60 with $1.5M — what ETFs in my 401k?",
    "AAPL is up 20% — should I rebalance my holdings?",
    "Should I sell my Tesla stock?",
    "What's the weather in Paris?",
]

for q in TEST_QUERIES:
    decision = routing_llm.invoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        HumanMessage(content=q),
    ])

    print(f"\nQ: {q}")
    print(f"  Agents:    {decision.agents}")
    print(f"  Reasoning: {decision.reasoning}")