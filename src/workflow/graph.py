"""
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import FinnieState
from src.utils.logger import setup_logger
from src.state import FinnieState
from src.agents.orchestrator import orchestrator_node
from src.agents.synthesizer import synthesizer_node
from src.agents.qa.agent import qa_agent_node, qa_tools_node, should_continue_qa

logger = setup_logger("finnie.workflow.graph")

def build_graph():
    """Construct, compile and return ai-finance-assistant graph."""

    builder = StateGraph(FinnieState)

    # --- Nodes ----------------------------------------------------
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("qa_agent_node", qa_agent_node)
    builder.add_node("qa_tools_node", qa_tools_node)
    builder.add_node("synthesizer_node", synthesizer_node)

    # --- Edges ----------------------------------------------------
    
    # START -> orchestrator (fixed)
    builder.add_edge(START, "orchestrator")
    # orchestrator -> agen(s) routing handled via Command + Send()

    # Finance QA agent: conditional -> tools (loop) or synthesizer node
    builder.add_conditional_edges(
        "qa_agent_node",
        should_continue_qa,
        {"qa_tools_node": "qa_tools_node", "synthesizer_node": "synthesizer_node"},  
    )
    builder.add_edge("qa_tools_node", "qa_agent_node")

    # add other specialist agent nodes/tool nodes later

    # Synthesizer -> END (fixed)
    builder.add_edge("synthesizer_node", END)

    # Let's compile with memory
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    logger.info("Finnie AI Assistant graph compiled")
    return graph

