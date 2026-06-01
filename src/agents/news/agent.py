"""
src/agents/news/agent.py — News Synthesizer agent node, tools node, routing edge.

Mirrors QA/Tax/Goal/Portfolio/Market agent pattern. Uses Tavily-backed
search_financial_news tool, writes to news_messages and news_response in state.
"""

from typing import Literal

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    AnyMessage,
)
from langgraph.prebuilt import ToolNode

from src.agents.news.tool import news_tools_list
from src.agents.prompts import NEWS_AGENT_PROMPT
from src.core.config import llm
from src.state import FinnieState
from src.utils.logger import setup_logger

logger = setup_logger("finnie.agents.news.agent")

# Steps:
# 1. create a singleton llm at import time and bind it with tools
news_llm = llm.bind_tools(news_tools_list)

# 2. create goal_tools_node using LangGraph's prebuilt ToolNode
news_tools_node = ToolNode(
    tools=news_tools_list,
    messages_key="news_messages",
)

MAX_AGENT_ITERATIONS = 5 # to prevent the agent from making infinite tool_calling

# 3. defining the news_agent_node which runs the ReAct loop
def news_agent_node(state: FinnieState) -> dict:
    """Invoke the News Synthesizer LLM (bound to search_financial_news) once.

    Behavior per call:
      - First call (news_messages empty): seed with system prompt + user query
      - Subsequent calls: preserve system prompt, replay accumulated history
        (which now includes prior AIMessages + ToolMessages from the loop)
      - If response has tool_calls → only update news_messages; the conditional
        edge will route to news_tools_node
      - If response is plain text → update news_messages AND set news_response;
        the conditional edge will route to synthesizer_node
    """
    news_msgs = state.get("news_messages", [])

    if not news_msgs:
        # First call (goal_messages empty): seed with system prompt + user query
        messages: list[AnyMessage] = [
            SystemMessage(content=NEWS_AGENT_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]
    else:
        # Subsequent calls: preserve system prompt, replay accumulated history
        # (which now includes prior AIMessages + ToolMessages from the loop)
        messages = [SystemMessage(content=NEWS_AGENT_PROMPT)] + list(news_msgs)

    loop_cnt = sum(1 for m in news_msgs if isinstance(m, AIMessage))
    if loop_cnt >= MAX_AGENT_ITERATIONS:
        # return fallback message in news_messages & news_response
        logger.warning(
            "News agent hit MAX_AGENT_ITERATIONS=%d — forcing fallback",
            MAX_AGENT_ITERATIONS,
        )
        fallback = (
            "I wasn't able to fetch news on that. Try a more specific query "
            "(e.g., 'Apple Q4 2026 earnings' instead of 'Apple')."
        )
        return {
            "news_messages": [AIMessage(content=fallback)],
            "news_response": fallback,
        }

    logger.info(
        "News agent: invoking LLM | history_len=%d loop_cnt=%d",
        len(news_msgs),
        loop_cnt,
    )

    # invoke the llm, check if llm says "run the tool calls" or did it produce a final answer
    try:
        response: AIMessage = news_llm.invoke(messages)
    except Exception as e:
        logger.error("News agent LLM call failed: %s: %s", type(e).__name__, e)
        # return error message in news_messages & news_response
        err = (
            "I ran into an issue fetching news. "
            "Please try again or rephrase your question."
        )
        return {
            "news_messages": [AIMessage(content=err)],
            "news_response": err,
        }

    # If LLM response has tool_calls → only update news_messages; the conditional edge will route to news_tools_node
    has_tools = bool(getattr(response, "tool_calls", None))
    update: dict = {"news_messages": [response]}
    if has_tools:
        logger.info("News agent: requested %d tool call(s)", len(response.tool_calls))
    else:
        # If response is plain text → update news_messages AND set news_response; the conditional edge will route to synthesizer_node
        update["news_response"] = response.content or ""
        logger.info("News agent: produced final answer | len=%d", len(update["news_response"]))

    return update

# 4. Check if conditional edge should continue to tool_calling loop or route to synthesizer node
def should_continue_news(
    state: FinnieState,
) -> Literal["news_tools_node", "synthesizer_node"]:
    """Route to tools-node if the latest news_message has tool calls, else synthesizer."""
    news_msgs = state.get("news_messages", [])
    if not news_msgs:
        return "synthesizer_node"
    
    last = news_msgs[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "news_tools_node"
    
    return "synthesizer_node"