"""
src/agents/portfolio/agent.py — Portfolio Analysis agent node, tools node,
routing edge. 

Mirrors QA/Tax/Goal pattern; uses analyze_portfolio tool.
"""

from typing import Literal

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    AnyMessage,
)
from langgraph.prebuilt import ToolNode

from src.utils.logger import setup_logger
from src.core.config import llm
from src.agents.portfolio.tool import portfolio_tools_list
from src.state import FinnieState
from src.agents.prompts import PORTFOLIO_AGENT_PROMPT

logger = setup_logger("finnie.agents.portfolio.agent")

# Steps:
# 1. create a singleton llm at import time and bind it with tools
portfolio_llm = llm.bind_tools(portfolio_tools_list)

# 2. create portfolio_tools_node using LangGraph's prebuilt ToolNode
portfolio_tools_node = ToolNode(
    tools=portfolio_tools_list,
    messages_key="portfolio_messages",
)

MAX_AGENT_ITERATIONS = 5 # to prevent the agent from making infinite tool_calling

# 3. defining the portfolio_agent_node which runs the ReAct loop
def portfolio_agent_node(state: FinnieState) -> dict:
    """Invoke the Portfolio Analysis LLM (bound to analyze_portfolio) once.

    Behavior per call:
      - First call (portfolio_messages empty): seed with system prompt + user query
      - Subsequent calls: preserve system prompt, replay accumulated history
        (which now includes prior AIMessages + ToolMessages from the loop)
      - If response has tool_calls → only update portfolio_messages; the
        conditional edge will route to portfolio_tools_node
      - If response is plain text → update portfolio_messages AND set
        portfolio_response; the conditional edge will route to synthesizer_node
    """
    portfolio_msgs = state.get("portfolio_messages", [])

    if not portfolio_msgs:
        # First call (portfolio_messages empty): seed with system prompt + user query
        messages: list[AnyMessage] = [
            SystemMessage(content=PORTFOLIO_AGENT_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]
    else:
        # Subsequent calls: preserve system prompt, replay accumulated history
        # (which now includes prior AIMessages + ToolMessages from the loop)
        messages = [SystemMessage(content=PORTFOLIO_AGENT_PROMPT)] + list(portfolio_msgs)

    # prevent infinite tool calling loop
    # loop_cnt = 0
    # for m in portfolio_msgs:
    #     if isinstance(m, AIMessage):
    #         loop_cnt+=1
    loop_cnt = sum(1 for m in portfolio_msgs if isinstance(m, AIMessage))
    if loop_cnt >= MAX_AGENT_ITERATIONS:
        # return fallback message in portfolio_messages & portfolio_response
        logger.warning(
            "Portfolio agent hit MAX_AGENT_ITERATIONS - forcing fallback",
            extra={"max_iterations": MAX_AGENT_ITERATIONS}
        )

        fallback = (
            "I wasn't able to analyze that portfolio. Could you provide the "
            "holdings as a clear list — e.g., '$10K AAPL, $5K BND'?"
        )

        return {
            "portfolio_messages": [AIMessage(content=fallback)],
            "portfolio_response": fallback
        }
   
    logger.info(
       "Portfolio agent: invoking LLM",
       extra={"history_len": len(portfolio_msgs), "loop_cnt": loop_cnt}
    )

    # invoke the llm, check if llm says "run the tool calls" or did it produce a final answer
    try:
        response: AIMessage = portfolio_llm.invoke(
            messages,
            config={
                "run_name": "portfolio_agent.llm_call",
                "tags": ["agent:portfolio", "operation:reasoning"],
            },
        )
    except Exception as e:
        logger.error("Portfolio agent LLM call failed", extra={"error_type": type(e).__name__, "error": str(e)})
        # return error message in portfolio_messages & portfolio_response
        err = (
            "I ran into an issue analyzing your portfolio. "
            "Please try again or paste your holdings as a clear list."
        )

        return {
            "portfolio_messages": [AIMessage(content=err)],
            "portfolio_response": err,
        }


    # If LLM response has tool_calls → only update portfolio_messages; the conditional edge will route to portfolio_tools_node
    has_tools = bool(getattr(response, "tool_calls", None))
    update: dict = {"portfolio_messages": [response]}

    if has_tools:
        logger.info("Portfolio agent requested tool calls", extra={"tool_calls_count": len(response.tool_calls)})
    else:
        # If response is plain text → update portfolio_messages AND set portfolio_response; the conditional edge will route to synthesizer_node
        update["portfolio_response"] = response.content or ""
        logger.info("Portfolio agent: produced final answer", extra={"response_len": len(update["portfolio_response"])})

    return update

# 4. Check if conditional edge should continue to tool_calling loop or route to synthesizer node
def should_continue_portfolio(state: FinnieState) -> Literal["portfolio_tools_node", "synthesizer_node"]:
    """Route to tools-node if the latest portfolio_messages has tool calls, else synthesizer"""
    portfolio_msgs = state.get("portfolio_messages", [])
    if not portfolio_msgs:
        return "synthesizer_node"
    
    last_msg = portfolio_msgs[-1]
    if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
        return "portfolio_tools_node"

    return "synthesizer_node"
