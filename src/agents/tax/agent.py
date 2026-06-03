"""
src/agents/tax/agent.py — Tax Education agent node, tools node, routing edge.

Mirrors the Q&A agent pattern. Uses tax_education_search tool, writes to
tax_messages and tax_response in state.
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
from src.agents.tax.tool import tax_tools_list
from src.state import FinnieState
from src.agents.prompts import TAX_AGENT_PROMPT

logger = setup_logger("finnie.agents.tax.agent")

# Step1:
# 1. create a singleton instance of the base llm and bind it with the tools
tax_llm = llm.bind_tools(tax_tools_list)

# 2. create tax_tools_node using LangGraph's prebuilt ToolNode
tax_tools_node = ToolNode(
    tools=tax_tools_list,
    messages_key="tax_messages"
)

MAX_AGENT_ITERATIONS = 5 # this is to prevent the llm making infinite tool calling calls

# 3. create tax_agent_node
def tax_agent_node(state: FinnieState) -> dict:
    """Invoke the Tax Education LLM (bound to tax_education_search) once.

    Behavior per call:
      - First call (tax_messages empty): seed with system prompt + user query
      - Subsequent calls: preserve system prompt, replay accumulated history
        (which now includes prior AIMessages + ToolMessages from the loop)
      - If response has tool_calls → only update tax_messages; the conditional
        edge will route to tax_tools_node
      - If response is plain text → update tax_messages AND set tax_response;
        the conditional edge will route to synthesizer_node
    """
    tax_msgs = state.get("tax_messages", [])

    if not tax_msgs:
        # First call (tax_messages empty): seed with system prompt + user query
        messages: list[AnyMessage] = [
            SystemMessage(content=TAX_AGENT_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]
    else:
        # Subsequent calls: preserve system prompt, replay accumulated history
        # (which now includes prior AIMessages + ToolMessages from the loop)
        messages = [SystemMessage(content=TAX_AGENT_PROMPT)] + list(tax_msgs)

    # prevent infinite tool calling loop
    # loop_cnt = 0
    # for m in tax_msgs:
    #     if isinstance(m, AIMessage):
    #         loop_cnt+=1
    loop_cnt = sum(1 for m in tax_msgs if isinstance(m, AIMessage))
    if loop_cnt >= MAX_AGENT_ITERATIONS:
        # return fallback message in tax_messages & tax_response
        logger.warning(
            "Tax agent hit MAX_AGENT_ITERATIONS - forcing fallback",
            extra={"max_iterations": MAX_AGENT_ITERATIONS}
        )

        fallback = (
            "I wasn't able to find a clear answer in my tax knowledge base. "
            "Tax laws change annually — please verify with the IRS website "
            "or consult a CPA."
        )

        return {
            "tax_messages": [AIMessage(content=fallback)],
            "tax_response": fallback
        }
   
    logger.info(
       "Tax agent: invoking LLM",
       extra={"history_len": len(tax_msgs), "loop_cnt": loop_cnt}
    )

    # invoke the llm, check if llm says "run the tool calls" or did it produce a final answer
    try:
        response: AIMessage = tax_llm.invoke(
            messages,
            config={
                "run_name": "tax_agent.llm_call",
                "tags": ["agent:tax", "operation:reasoning"],
            },
        )
    except Exception as e:
        logger.error("Tax agent LLM call failed", extra={"error_type": type(e).__name__, "error": str(e)})
        # return error message in tax_messages & tax_response
        err = (
            "I ran into an issue answering your tax question. Please retry or rephrase your question.",
        )

        return {
            "tax_messages": [AIMessage(content=err)],
            "tax_response": err,
        }


    # If LLM response has tool_calls → only update tax_messages; the conditional edge will route to tax_tools_node
    has_tools = bool(getattr(response, "tool_calls", None))
    update: dict = {"tax_messages": [response]}

    if has_tools:
        logger.info("Tax agent requested tool calls", extra={"tool_calls_count": len(response.tool_calls)})
    else:
        # If response is plain text → update tax_messages AND set tax_response; the conditional edge will route to synthesizer_node
        update["tax_response"] = response.content or ""
        logger.info("Tax agent produced final answer", extra={"response_len": len(update["tax_response"])})

    return update

# 4. Check if conditional edge should continue to tool_calling loop or route to synthesizer node
def should_continue_tax(state: FinnieState) -> Literal["tax_tools_node", "synthesizer_node"]:
    """Route to tools-node if the latest tax_messages has tool calls, else synthesizer"""
    tax_msgs = state.get("tax_messages", [])
    if not tax_msgs:
        return "synthesizer_node"
    
    last_msg = tax_msgs[-1]
    if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
        return "tax_tools_node"

    return "synthesizer_node"