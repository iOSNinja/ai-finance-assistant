"""
src/agents/synthesizer.py - Merges responses from one or more agents
into a single coherent reply to the user.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.logger import setup_logger
from src.state import FinnieState
from src.core.config import llm
from src.agents.prompts import SYNTHESIZER_PROMPT

logger = setup_logger("finnie.agents.synthesizer")

def synthesizer_node(state: FinnieState) -> dict:
    """Combine agent outputs into a final, user-friendly answer."""
    logger.info("Combining agent responses...")

    qa_agent_response = state.get("qa_response", "")
    
    combined = ""
    if qa_agent_response:
        combined += f"[Finance Q&A Agent]\n{qa_agent_response}\n\n"

    if not combined:
        combined = "Could not find relevant information. Please try rephrasing your query."

    final = llm.invoke(
        [
            SystemMessage(content=SYNTHESIZER_PROMPT),
            HumanMessage(
                content=f"User query: {state["user_query"]}\n\nAgent outputs:\n{combined}"
            ),
        ]
    )

    logger.info("Final answer ready (%d chars)", len(final.content))

    return {
        "final_answer": final.content,
        "messages": [final],
    }
    
