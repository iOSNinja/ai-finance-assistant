"""
agents/orchestrator.py — Classifies the user query and dispatches
to the correct specialist agent(s) using LangGraph's Send() API.
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command, Send

from src.core.config import llm
from src.state import FinnieState
from src.agents.prompts import ORCHESTRATOR_PROMPT
from src.utils.logger import setup_logger

logger = setup_logger("finnie.orchestrator")

class OrchestratorDecision(BaseModel):
    """The orchestrator's routing decision."""

    reasoning: str = Field(description="Brief explanation of why these agents were chosen")
    agents: list[Literal["qa_agent", "tax_agent", "goal_agent", "portfolio_agent", "market_agent", "news_agent"]] = Field(
        description="List of agents to dispatch. Always at least one.",
        min_length=1,
    )
    is_finance_query: bool = Field(
        description=(
            "True if the query is about finance, investing, taxes, or money "
            "and warrants the educational disclaimer. False for off-topic "
            "redirects, greetings, or queries unrelated to finance."
        ),
    )

routing_llm = llm.with_structured_output(OrchestratorDecision)

def orchestrator_node(
    state: FinnieState,
) -> Command[Literal["qa_agent_node", "tax_agent_node", "goal_agent_node", "portfolio_agent_node", "market_agent_node", "news_agent_node"]]:
    """Classify the query and fan out to one or more agents."""

    query = state["user_query"]
    logger.info("Routing query: %s", query[:60])

    # Retrieves the last 6 messages from conversation history (for context).
    history = state.get("messages", [])[-6:] 

    decision: OrchestratorDecision = routing_llm.invoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        *history,
        HumanMessage(content=query),
    ])

    logger.info("Agents: %s | Reason: %s", decision.agents, decision.reasoning)

    clean_state = {
        **state,
        "qa_messages": [],
        "portfolio_messages": [],
        "market_messages": [],
        "goal_messages": [],
        "news_messages": [],
        "tax_messages": [],
        "qa_response": "",
        "portfolio_response": "",
        "market_response": "",
        "goal_response": "",
        "news_response": "",
        "tax_response": "",
    }

    # Create Send objects for each selected agent
    sends = [Send(f"{agent}_node", clean_state) for agent in decision.agents]
    return Command(goto=sends, update={
        "route": decision.agents,
        "is_finance_query": decision.is_finance_query,
    }) # return a Command that: (1) routes to those agents in parallel, and (2) updates state with which agents were chosen.