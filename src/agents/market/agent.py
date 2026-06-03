"""
src/agents/market/agent.py — Market Analysis agent node, tools node, routing edge.

Mirrors QA/Tax/Goal/Portfolio agent pattern. Uses yfinance-backed tools,
writes to market_messages and market_response in state.
"""

from typing import Literal

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    AnyMessage,
)
from langgraph.prebuilt import ToolNode

from src.agents.market.tool import market_tools_list
from src.agents.prompts import MARKET_AGENT_PROMPT
from src.core.config import llm
from src.state import FinnieState
from src.utils.logger import setup_logger

logger = setup_logger("finnie.agents.market.agent")

# Steps:
# 1. create a singleton llm at import time and bind it with tools
market_llm = llm.bind_tools(market_tools_list)

# 2. create goal_tools_node using LangGraph's prebuilt ToolNode
market_tools_node = ToolNode(
    tools=market_tools_list,
    messages_key="market_messages",
)

MAX_AGENT_ITERATIONS = 5 # to prevent the agent from making infinite tool_calling

# 3. defining the market_agent_node which runs the ReAct loop
def market_agent_node(state: FinnieState) -> dict:
    """Invoke the Market Analysis LLM (bound to yfinance tools) once.

    Behavior per call:
      - First call (market_messages empty): seed with system prompt + user query
      - Subsequent calls: preserve system prompt, replay accumulated history
        (which now includes prior AIMessages + ToolMessages from the loop)
      - If response has tool_calls → only update market_messages; the
        conditional edge will route to market_tools_node
      - If response is plain text → update market_messages AND set
        market_response; the conditional edge will route to synthesizer_node
    """
    market_msgs = state.get("market_messages", [])

    if not market_msgs:
        # First call (goal_messages empty): seed with system prompt + user query
        messages: list[AnyMessage] = [
            SystemMessage(content=MARKET_AGENT_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]
    else:
        # Subsequent calls: preserve system prompt, replay accumulated history
        # (which now includes prior AIMessages + ToolMessages from the loop)
        messages = [SystemMessage(content=MARKET_AGENT_PROMPT)] + list(market_msgs)

    # prevent infinite tool calling loop
    # loop_cnt = 0
    # for m in market_msgs:
    #     if isinstance(m, AIMessage):
    #         loop_cnt+=1
    loop_cnt = sum(1 for m in market_msgs if isinstance(m, AIMessage))
    if loop_cnt >= MAX_AGENT_ITERATIONS:
        # return fallback message in market_messages & market_response
        logger.warning(
            "Market agent hit MAX_AGENT_ITERATIONS=%d — forcing fallback",
            MAX_AGENT_ITERATIONS,
        )
        fallback = (
            "I wasn't able to fetch market data right now. Please try "
            "again in a moment, or check the ticker symbol if it's "
            "unusual (e.g., '^GSPC' for S&P 500)."
        )
        return {
            "market_messages": [AIMessage(content=fallback)],
            "market_response": fallback,
        }

    logger.info(
        "Market agent: invoking LLM | history_len=%d loop_cnt=%d",
        len(market_msgs),
        loop_cnt,
    )

    # invoke the llm, check if llm says "run the tool calls" or did it produce a final answer
    try:
        response: AIMessage = market_llm.invoke(
            messages,
            config={
                "run_name": "market_agent.llm_call",
                "tags": ["agent:market", "operation:reasoning"],
            },
        )
    except Exception as e:
        logger.error("Market agent LLM call failed: %s: %s", type(e).__name__, e)
        # return error message in market_messages & market_response
        err = (
            "I ran into an issue fetching market data. "
            "Please try again in a moment."
        )
        return {
            "market_messages": [AIMessage(content=err)],
            "market_response": err,
        }

    # If LLM response has tool_calls → only update market_messages; the conditional edge will route to market_tools_node
    has_tools = bool(getattr(response, "tool_calls", None))
    update: dict = {"market_messages": [response]}
    if has_tools:
        logger.info("Market agent: requested %d tool call(s)", len(response.tool_calls))
    else:
        # If response is plain text → update market_messages AND set market_response; the conditional edge will route to synthesizer_node
        update["market_response"] = response.content or ""
        logger.info("Market agent: produced final answer | len=%d", len(update["market_response"]))

    return update

# 4. Check if conditional edge should continue to tool_calling loop or route to synthesizer node
def should_continue_market(
    state: FinnieState,
) -> Literal["market_tools_node", "synthesizer_node"]:
    """Route to tools-node if the latest market_message has tool calls, else synthesizer."""
    market_msgs = state.get("market_messages", [])
    if not market_msgs:
        return "synthesizer_node"
    
    last = market_msgs[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "market_tools_node"
    
    return "synthesizer_node"