"""
src/agents/goal/agent.py — Goal Planning agent node, tools node, routing edge.

Mirrors the QA / Tax agent pattern. Uses goal_tools_list (pure-math tools),
writes to goal_messages and goal_response in state.
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
from src.agents.goal.tool import goal_tools_list
from src.state import FinnieState
from src.agents.prompts import GOAL_AGENT_PROMPT

logger = setup_logger("finnie.agents.goals.agent")

# Steps:
# 1. create a singleton llm at import time and bind it with tools
goal_llm = llm.bind_tools(goal_tools_list)

# 2. create goal_tools_node using LangGraph's prebuilt ToolNode
goal_tools_node = ToolNode(
    tools=goal_tools_list,
    messages_key="goal_messages",
)

MAX_AGENT_ITERATIONS = 5 # to prevent the agent from making infinite tool_calling

# 3. defining the goal_agent_node which runs the ReAct loop
def goal_agent_node(state: FinnieState) -> dict:
    """Invoke the Goal Planning LLM (bound to math tools) once.

    Behavior per call:
      - First call (goal_messages empty): seed with system prompt + user query
      - Subsequent calls: preserve system prompt, replay accumulated history
        (which now includes prior AIMessages + ToolMessages from the loop)
      - If response has tool_calls → only update goal_messages; the conditional
        edge will route to goal_tools_node
      - If response is plain text → update goal_messages AND set goal_response;
        the conditional edge will route to synthesizer_node
    """
    goal_msgs = state.get("goal_messages", [])

    if not goal_msgs:
        # First call (goal_messages empty): seed with system prompt + user query
        messages: list[AnyMessage] = [
            SystemMessage(content=GOAL_AGENT_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]
    else:
        # Subsequent calls: preserve system prompt, replay accumulated history
        # (which now includes prior AIMessages + ToolMessages from the loop)
        messages = [SystemMessage(content=GOAL_AGENT_PROMPT)] + list(goal_msgs)

    # prevent infinite tool calling loop
    # loop_cnt = 0
    # for m in goal_msgs:
    #     if isinstance(m, AIMessage):
    #         loop_cnt+=1
    loop_cnt = sum(1 for m in goal_msgs if isinstance(m, AIMessage))
    if loop_cnt >= MAX_AGENT_ITERATIONS:
        # return fallback message in goal_messages & goal_response
        logger.warning(
            "Goal agent hit MAX_AGENT_ITERATIONS=%d - forcing fallback",
            MAX_AGENT_ITERATIONS
        )

        fallback = (
            "I wasn't able to compute a projection for that. "
            "Could you rephrase your goal — a target amount, a time horizon, "
            "and either current savings or a monthly contribution?"
        )

        return {
            "goal_messages": [AIMessage(content=fallback)],
            "goal_response": fallback
        }
   
    logger.info(
       "Goal agent: invoking LLM | history_len=%d, loop_cnt=%d",
       len(goal_msgs),
       loop_cnt
    )

    # invoke the llm, check if llm says "run the tool calls" or did it produce a final answer
    try:
        response: AIMessage = goal_llm.invoke(messages)
    except Exception as e:
        logger.error("Goal agent LLM call failed: %s: %s", type(e).__name__, e)
        # return error message in goal_messages & goal_response
        err = (
            "I ran into an issue computing your projection. "
            "Please try again or rephrase your goal."
        )

        return {
            "goal_messages": [AIMessage(content=err)],
            "goal_response": err,
        }


    # If LLM response has tool_calls → only update goal_messages; the conditional edge will route to goal_tools_node
    has_tools = bool(getattr(response, "tool_calls", None))
    update: dict = {"goal_messages": [response]}

    if has_tools:
        logger.info("Goal agent requested: %d tool call(s)", len(response.tool_calls))
    else:
        # If response is plain text → update goal_messages AND set goal_response; the conditional edge will route to synthesizer_node
        update["goal_response"] = response.content or ""
        logger.info("Goal agent: produced final answer | len=%d", len(update["goal_response"]))

    return update

# 4. Check if conditional edge should continue to tool_calling loop or route to synthesizer node
def should_continue_goal(state: FinnieState) -> Literal["goal_tools_node", "synthesizer_node"]:
    """Route to tools-node if the latest goal_messages has tool calls, else synthesizer"""
    goal_msgs = state.get("goal_messages", [])
    if not goal_msgs:
        return "synthesizer_node"
    
    last_msg = goal_msgs[-1]
    if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
        return "goal_tools_node"

    return "synthesizer_node"
