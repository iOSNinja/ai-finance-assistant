"""
src/agents/qa/agent.py - Q&A agent node, tools and routing edge. Uses qa tool to answer user queries
related to finance, portfolio, market data, goal planning & general questions.

Uses LangGraph conditional edges instead of a manual tool-calling loop.
- qa_agent_node() — calls the LLM bound to the search tool; LLM decides whether to call the tool.
- qa_tools_node() — executes any tool calls and returns results to the agent.
- should_continue_qa() — conditional edge: route to tools node if there are tool calls, else to synthesizer.
- System prompt for the Q&A agent emphasizing: ground answers in retrieved chunks, cite sources, say "I don't know" when retrieval is weak.

State channels used by this node:
- qa_messages - isolated tool-loop buffer
- qa_response - final text answer
- user_query - original query
"""

from typing import Literal

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
)
from langgraph.prebuilt import ToolNode

from src.agents.prompts import QA_AGENT_PROMPT
from src.agents.qa.tool import qa_tools_list
from src.core.config import llm
from src.state import FinnieState
from src.utils.logger import setup_logger

logger = setup_logger("finnie.agents.qa.agent")

# Steps:
# 1. create a singleton llm at import time and bind it with tools
qa_llm = llm.bind_tools(qa_tools_list)

# 2. create qa_tools_node using LangGraph's prebuilt ToolNode
qa_tools_node = ToolNode(
    tools=qa_tools_list,
    messages_key="qa_messages",
)

MAX_AGENT_ITERATIONS = 5  # to prevent the agent from making infinite tool_calling


# 3. defining the qa_agent_node which runs the ReAct loop
def qa_agent_node(state: FinnieState) -> dict:
    """Invoke the Q&A LLM (bound to finance_qa_search) once.

    Behavior per call:
      - First call (qa_messages empty): seed with system prompt + user query
      - Subsequent calls: preserve system prompt, replay accumulated history
        (which now includes prior AIMessages + ToolMessages from the loop)
      - If response has tool_calls → only update qa_messages; the conditional
        edge will route to qa_tools_node
      - If response is plain text → update qa_messages AND set qa_response;
        the conditional edge will route to synthesizer_node
    """
    qa_msgs = state.get("qa_messages", [])

    if not qa_msgs:
        # First call (qa_messages empty): seed with system prompt + user query
        messages: list[AnyMessage] = [
            SystemMessage(content=QA_AGENT_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]
    else:
        # Subsequent calls: preserve system prompt, replay accumulated history
        # (which now includes prior AIMessages + ToolMessages from the loop)
        messages = [SystemMessage(content=QA_AGENT_PROMPT)] + list(qa_msgs)

    # prevent infinite tool calling loop
    # loop_cnt = 0
    # for m in qa_msgs:
    #     if isinstance(m, AIMessage):
    #         loop_cnt+=1
    loop_cnt = sum(1 for m in qa_msgs if isinstance(m, AIMessage))
    if loop_cnt >= MAX_AGENT_ITERATIONS:
        # return fallback message in qa_messages & qa_response
        logger.warning(
            "QA agent hit MAX_AGENT_ITERATIONS - forcing fallback",
            extra={"max_iterations": MAX_AGENT_ITERATIONS},
        )

        fallback = (
            "I wasn't able to find a clear anwser in the knowledge base."
            "Please try rephrasing your question or ask about a different topic."
        )

        return {"qa_messages": [AIMessage(content=fallback)], "qa_response": fallback}

    # logger.info(
    #    "QA agent: invoking LLM | history_len=%d, loop_cnt=%d",
    #    len(qa_msgs),
    #    loop_cnt
    # )

    logger.info(
        "QA agent: invoking LLM",
        extra={
            "agent": "qa",
            "history_len": len(qa_msgs),
            "ai_turns": loop_cnt,
        },
    )

    # invoke the llm, check if llm says "run the tool calls" or did it produce a final answer
    try:
        response: AIMessage = qa_llm.invoke(
            messages,
            config={
                "run_name": "qa_agent.llm_call",
                "tags": ["agent:qa", "operation:reasoning"],
            },
        )
    except Exception as e:
        logger.error(
            "QA agent LLM call failed", extra={"error_type": type(e).__name__, "error": str(e)}
        )
        # return error message in qa_messages & qa_response
        err = (
            "QA agent ran into an issue while answering. Please retry or rephrase your question.",
        )

        return {
            "qa_messages": [AIMessage(content=err)],
            "qa_response": err,
        }

    # If LLM response has tool_calls → only update qa_messages; the conditional edge will route to qa_tools_node
    has_tools = bool(getattr(response, "tool_calls", None))
    update: dict = {"qa_messages": [response]}

    if has_tools:
        logger.info(
            "QA agent requested tool calls", extra={"tool_calls_count": len(response.tool_calls)}
        )
    else:
        # If response is plain text → update qa_messages AND set qa_response; the conditional edge will route to synthesizer_node
        update["qa_response"] = response.content or ""
        logger.info(
            "QA agent produced final answer", extra={"response_len": len(update["qa_response"])}
        )

    return update


# 4. Check if conditional edge should continue to tool_calling loop or route to synthesizer node
def should_continue_qa(state: FinnieState) -> Literal["qa_tools_node", "synthesizer_node"]:
    """Route to tools-node if the latest qa_messages has tool calls, else synthesizer"""
    qa_msgs = state.get("qa_messages", [])
    if not qa_msgs:
        return "synthesizer_node"

    last_msg = qa_msgs[-1]
    if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
        return "qa_tools_node"

    return "synthesizer_node"
