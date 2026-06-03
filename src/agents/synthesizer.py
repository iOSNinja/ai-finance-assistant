"""
src/agents/synthesizer.py — Merges responses from one or more agents
into a single coherent reply, with the standard compliance disclaimer
appended deterministically.
"""

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.utils.logger import setup_logger
from src.state import FinnieState
from src.core.config import llm
from src.agents.prompts import SYNTHESIZER_PROMPT

logger = setup_logger("finnie.agents.synthesizer")

# ──────────────────────────────────────────────────────────────────────────────
# Compliance disclaimer — appended to every response. Required by the
# regulatory framing in the project brief (distinguish education from advice).
# ──────────────────────────────────────────────────────────────────────────────
DISCLAIMER = (
    "\n\n---\n"
    "_This is educational content, not personalized financial advice. "
    "For decisions specific to your situation, consult a qualified financial "
    "advisor or CPA._"
)

# Map state-field -> agent name
_AGENT_FIELDS: dict[str, str] = {
    "qa_response": "Finance Q&A",
    "portfolio_response": "Portfolio Analysis",
    "market_response":    "Market Analysis",
    "goal_response":      "Goal Planning",
    "news_response":      "News Synthesizer",
    "tax_response":       "Tax Education",
}

def _maybe_append_disclaimer(text: str, state: FinnieState) -> str:
    """Append the educational disclaimer ONLY for finance queries.
    Defaults to True if the flag is missing for any reason."""
    if state.get("is_finance_query", True):
        return text + DISCLAIMER
    return text

def synthesizer_node(state: FinnieState) -> dict:
    """Merge agent outputs into a single response, then append the disclaimer."""
    # Collect all non-empty agent responses first
    contributions: list[tuple[str, str]] = []
    for field, label in _AGENT_FIELDS.items():
        value = state.get(field, "")
        if value:
            contributions.append((label, value))

    logger.info("Synthesizing agent contributions", extra={"contribution_count": len(contributions)})

    # No agent produced anything — return fallback
    if not contributions:
        fallback = (
            "I wasn't able to produce a useful answer for that query. "
            "Could you rephrase or ask something more specific?"
        )
        final_answer = _maybe_append_disclaimer(fallback, state)
        return {
            "final_answer": final_answer,
            "messages": [AIMessage(content=final_answer)],
        }

    # Single agent contribution
    if len(contributions) == 1:
        _, single = contributions[0]
        final_answer = _maybe_append_disclaimer(single, state)
        logger.info("Single-agent passthrough", extra={"response_len": len(final_answer)})
        return {
            "final_answer": final_answer,
            "messages": [AIMessage(content=final_answer)],
        }

    # Multiple agents — LLM to merge them coherently
    agent_block = "\n\n".join(f"[{label}]\n{text}" for label, text in contributions)
    user_query = state.get("user_query", "")

    try:
        response = llm.invoke(
            [SystemMessage(content=SYNTHESIZER_PROMPT),
            HumanMessage(
                content=(
                    f"User query:\n{user_query}\n\n"
                    f"Agent outputs:\n{agent_block}"
                )
            )],
            config={
                "run_name": "synthesizer.merge",
                "tags": ["operation:synthesis", f"agents_merged:{len(contributions)}"],
            },
        )
        merged = response.content or ""
    except Exception as e:
        logger.error("Synthesizer LLM call failed", extra={"error_type": type(e).__name__, "error": str(e)})
        # Fallback to a simple concatenation if the LLM can't merge
        merged = "\n\n".join(text for _, text in contributions)

    final_answer = _maybe_append_disclaimer(merged, state)
    logger.info("Multi-agent merge complete", extra={"response_len": len(final_answer)})

    return {
        "final_answer": final_answer,
        "messages": [AIMessage(content=final_answer)],
    }
    
