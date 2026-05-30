"""Chat tab: main multi-agent conversational interface."""

import streamlit as st

from src.main import FinnieAIFinanceAssistant
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _get_assistant() -> FinnieAIFinanceAssistant:
    """Lazy singleton — initialized once and cached in session state."""
    if "assistant" not in st.session_state:
        with st.spinner("Initializing Finnie (loading graph + KB)..."):
            st.session_state.assistant = FinnieAIFinanceAssistant()
    return st.session_state.assistant


def _initialize_chat_state() -> None:
    """Ensure chat-history list exists in session state."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def _render_message_history() -> None:
    """Replay all past messages from session state."""
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def _handle_user_input(user_query: str) -> None:
    """Process one round-trip: echo user, invoke graph, render reply."""
    # 1. Append + echo user message
    st.session_state.chat_messages.append(
        {"role": "user", "content": user_query}
    )
    with st.chat_message("user"):
        st.markdown(user_query)

    # 2. Invoke graph + render assistant reply
    assistant = _get_assistant()
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = assistant.ask(user_query)
            except Exception as e:
                logger.exception("Graph invocation failed in chat tab")
                response = (
                    f"Sorry — something went wrong while answering. "
                    f"Please try again or rephrase your question.\n\n"
                    f"_({type(e).__name__})_"
                )
        st.markdown(response)

    # 3. Persist assistant reply
    st.session_state.chat_messages.append(
        {"role": "assistant", "content": response}
    )


def render() -> None:
    """Render the chat tab."""
    st.markdown("## 💬 Chat with Finnie")
    st.caption(
        "Ask any educational finance question. Finnie searches its curated "
        "knowledge base and cites sources."
    )

    _initialize_chat_state()
    _render_message_history()

    # Example prompts (only show when chat is empty)
    if not st.session_state.chat_messages:
        st.markdown("**Try one of these to get started:**")
        examples = [
            "What is an ETF?",
            "Explain compound interest like I'm 10",
            "Index fund vs mutual fund?",
            "Why is diversification important?",
        ]
        cols = st.columns(len(examples))
        for col, ex in zip(cols, examples):
            if col.button(ex, use_container_width=True, key=f"ex_{ex}"):
                _handle_user_input(ex)
                st.rerun()

    # User input
    if user_query := st.chat_input("Ask a finance question..."):
        _handle_user_input(user_query)
        st.rerun()