"""
state.py - Shared state scheme for the ai-finance-assistant multi-agent graph.
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


def reset_or_add_messages(current: list[AnyMessage], update: list[AnyMessage]) -> list[AnyMessage]:
    """Like add_messages, but an empty update list signals a reset.

    Standard add_messages([X], []) returns [X] (no-op merge). This wrapper
    treats an empty update as 'clear the channel' so the orchestrator's
    per-turn buffer reset actually works.
    """
    if not update:
        return []
    return current + update


class FinnieState(TypedDict):
    """State that flows through every node in the graph."""

    messages: Annotated[
        list[AnyMessage], add_messages
    ]  # full conversation history -> does not need(reset_or_add_messages) reset, needs to persist whole chat history
    user_query: str  # original user query

    # routing
    route: list[str]  # e.g. ["qa_agent", "portfolio_agent"]
    is_finance_query: bool  # to be set by orchestrator & read by synthesizer

    # Per-agent message buffers (isolated via reset_or_add_messages reducer)
    qa_messages: Annotated[list[AnyMessage], reset_or_add_messages]
    portfolio_messages: Annotated[list[AnyMessage], reset_or_add_messages]
    market_messages: Annotated[list[AnyMessage], reset_or_add_messages]
    goal_messages: Annotated[list[AnyMessage], reset_or_add_messages]
    news_messages: Annotated[list[AnyMessage], reset_or_add_messages]
    tax_messages: Annotated[list[AnyMessage], reset_or_add_messages]

    # Per-agent outputs
    qa_response: str
    portfolio_response: str
    market_response: str
    goal_response: str
    news_response: str
    tax_response: str

    final_answer: str  # final response returned to the user, set by synthesizer

    # guardrails
    is_safe_input: bool
    input_block_category: str
    input_redactions: list[dict]  # input PII audit
    pii_redactions: Annotated[list[dict], operator.add]  # output PII audit
