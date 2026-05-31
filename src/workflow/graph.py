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

logger = setup_logger("finnie.workflow.graph")

def build_graph():
    """Construct, compile and return the Finnie AI Finance Assistant graph."""

    builder = StateGraph(FinnieState)

    # --- Nodes ----------------------------------------------------
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("qa_agent_node", qa_agent_node)
    builder.add_node("qa_tools_node", qa_tools_node)
    builder.add_node("tax_agent_node", tax_agent_node)
    builder.add_node("tax_tools_node", tax_tools_node)
    builder.add_node("goal_agent_node", goal_agent_node)
    builder.add_node("goal_tools_node", goal_tools_node)
    builder.add_node("portfolio_agent_node", portfolio_agent_node)
    builder.add_node("portfolio_tools_node", portfolio_tools_node)
    builder.add_node("synthesizer_node", synthesizer_node)

    # --- Edges ----------------------------------------------------
    
    # START -> orchestrator (fixed)
    builder.add_edge(START, "orchestrator")

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

    # TODO - add other specialist agent nodes/tool nodes later

    # Synthesizer -> END (fixed)
    builder.add_edge("synthesizer_node", END)

    # Let's compile with in-memory checkpointer
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    logger.info("Finnie graph compiled with %d nodes", 10)
    return graph

