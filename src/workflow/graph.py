"""
src/workflow/graph.py — Build and compile Finnie's LangGraph StateGraph.

Topology (dashed = conditional, solid = fixed):
    START → orchestrator ─ ─ ─ ┬─ qa_agent_node ↔ qa_tools_node ─┐
                               │                                  │
                               │                                  ↓
                               └─ (other agents land here later) → synthesizer → END

Orchestrator dispatches to agents via Command(goto=Send(...)) — no fixed edges
from orchestrator to agents.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from src.guardrails import check_input, scrub_output

from src.state import FinnieState
from src.utils.logger import setup_logger
from src.state import FinnieState
from src.agents.orchestrator import orchestrator_node
from src.agents.synthesizer import synthesizer_node
from src.agents.qa.agent import qa_agent_node, qa_tools_node, should_continue_qa
from src.agents.tax.agent import tax_agent_node, tax_tools_node, should_continue_tax
from src.agents.goal.agent import goal_agent_node, goal_tools_node, should_continue_goal
from src.agents.portfolio.agent import (
    portfolio_agent_node,
    portfolio_tools_node,
    should_continue_portfolio,
)
from src.agents.market.agent import (
    market_agent_node,
    market_tools_node,
    should_continue_market,
)
from src.agents.news.agent import (
    news_agent_node,
    news_tools_node,
    should_continue_news,
)

logger = setup_logger("finnie.workflow.graph")

# Generic safe fallback — DO NOT reveal which guard fired.
# Same message for every block, so attackers can't probe for bypasses.
SAFE_FALLBACK = (
    "I'm Finnie, your finance education assistant. I can help with financial "
    "concepts, taxes, savings goals, portfolio analysis, market data, and "
    "financial news. If you have a question on one of these topics, please rephrase."
)

def input_guard_node(state: FinnieState) -> dict:
    """Pre-orchestrator input safety. Blocks unsafe OR forwards a cleaned query."""
    result = check_input(state["user_query"])
    if not result.is_safe:
        # Block path
        return {
            "is_safe_input":        False,
            "input_block_category": result.category,
            "final_answer":         SAFE_FALLBACK,
            "route":                [],
        }
    
    # Safe path — forward cleaned query (which may equal original if no PII found)
    return {
        "is_safe_input":        True,
        "input_block_category": "ok",
        "user_query":           result.cleaned_query,    # may be redacted
        "input_redactions":     result.input_redactions,
    }


def output_guard_node(state: FinnieState) -> dict:
    """Post-synthesizer output safety. Redact + audit."""
    answer = state.get("final_answer", "")
    is_finance = state.get("is_finance_query", True)
    result = scrub_output(answer, is_finance_query=is_finance)

    update = {}
    if result.modified:
        update["final_answer"] = result.text
    if result.pii_redactions:
        update["pii_redactions"] = result.pii_redactions
    return update


def _route_after_input_guard(state: FinnieState) -> str:
    """Conditional edge: skip everything if input blocked."""
    return "END" if not state.get("is_safe_input", True) else "orchestrator"

def build_graph():
    """Construct, compile and return the Finnie AI Finance Assistant graph."""

    builder = StateGraph(FinnieState)

    # --- Nodes ----------------------------------------------------
    # input_guard runs first
    builder.add_node("input_guard", input_guard_node)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("qa_agent_node", qa_agent_node)
    builder.add_node("qa_tools_node", qa_tools_node)
    builder.add_node("tax_agent_node", tax_agent_node)
    builder.add_node("tax_tools_node", tax_tools_node)
    builder.add_node("goal_agent_node", goal_agent_node)
    builder.add_node("goal_tools_node", goal_tools_node)
    builder.add_node("portfolio_agent_node", portfolio_agent_node)
    builder.add_node("portfolio_tools_node", portfolio_tools_node)
    builder.add_node("market_agent_node", market_agent_node)
    builder.add_node("market_tools_node", market_tools_node)
    builder.add_node("news_agent_node", news_agent_node)
    builder.add_node("news_tools_node", news_tools_node)
    builder.add_node("synthesizer_node", synthesizer_node)
    # output_guard runs last
    builder.add_node("output_guard", output_guard_node)

    # --- Edges ----------------------------------------------------
    
    # START -> input_guard (fixed)
    builder.add_edge(START, "input_guard")
    builder.add_conditional_edges(
        "input_guard",
        _route_after_input_guard,
        {"orchestrator": "orchestrator", "END": END},
    )

     # Orchestrator -> agent(s): handled internally by Command(goto=Send(...))

    # Finance QA agent: conditional -> tools-node (loop) or synthesizer node
    builder.add_conditional_edges(
        "qa_agent_node",
        should_continue_qa,
        {
            "qa_tools_node": "qa_tools_node", 
            "synthesizer_node": "synthesizer_node"
        },  
    )

    # tools-node back to agent-node
    builder.add_edge("qa_tools_node", "qa_agent_node")

    # Tax Education agent: conditional -> tools-node (loop) or synthesizer node
    builder.add_conditional_edges(
        "tax_agent_node",
        should_continue_tax,
        {
            "tax_tools_node": "tax_tools_node",
            "synthesizer_node": "synthesizer_node"
        }
    )
    # wire tools-node back to agent node
    builder.add_edge("tax_tools_node", "tax_agent_node")

    # Goal Planning agent
    builder.add_conditional_edges(
        "goal_agent_node",
        should_continue_goal,
        {
            "goal_tools_node":  "goal_tools_node",
            "synthesizer_node": "synthesizer_node",
        },
    )
    # wire tools-node back to agent node
    builder.add_edge("goal_tools_node", "goal_agent_node")

    # Portfolio Analysis agent
    builder.add_conditional_edges(
        "portfolio_agent_node",
        should_continue_portfolio,
        {
            "portfolio_tools_node": "portfolio_tools_node",
            "synthesizer_node":     "synthesizer_node",
        },
    )
    # wire tools-node back to agent node
    builder.add_edge("portfolio_tools_node", "portfolio_agent_node")

    # Maket Analysis agent
    builder.add_conditional_edges(
        "market_agent_node",
        should_continue_market,
        {
            "market_tools_node": "market_tools_node",
            "synthesizer_node": "synthesizer_node",
        },   
    )
    # wire tools-node back to agent node
    builder.add_edge("market_tools_node", "market_agent_node")

    # News Synthesizer agent
    builder.add_conditional_edges(
        "news_agent_node",
        should_continue_news,
        {
            "news_tools_node":  "news_tools_node",
            "synthesizer_node": "synthesizer_node",
        },
    )
    # wire tools-node back to agent node
    builder.add_edge("news_tools_node", "news_agent_node")

    # Synthesizer -> output_guard -> END (fixed)
    builder.add_edge("synthesizer_node", "output_guard")
    builder.add_edge("output_guard", END)

    # Let's compile with in-memory checkpointer
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    logger.info("Finnie graph compiled", extra={"node_count": 14})
    return graph

