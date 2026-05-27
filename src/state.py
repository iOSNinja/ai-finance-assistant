"""
state.py - Shared state scheme for the ai-finance-assistant multi-agent graph.
"""

from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class FinnieState(TypedDict):
    """State that flows through every node in the graph."""

    messages: Annotated[list[AnyMessage], add_messages] # full conversation history
    user_query: str # original user query

    # routing
    route: list[str] # e.g. ["qa_agent", "portfolio_agent"]

    # Per-agent message buffers (isolated via add_messages reducer)
    qa_messages: Annotated[list[AnyMessage], add_messages]
    portfolio_messages: Annotated[list[AnyMessage], add_messages]
    market_messages: Annotated[list[AnyMessage], add_messages]
    goal_messages: Annotated[list[AnyMessage], add_messages]
    news_messages: Annotated[list[AnyMessage], add_messages]
    tax_messages: Annotated[list[AnyMessage], add_messages]

    # Per-agent outputs
    qa_response: str
    portfolio_response: str
    market_response: str
    goal_response: str
    news_response: str
    tax_response: str

    final_answer: str # final response returned to the user, set by synthesizer