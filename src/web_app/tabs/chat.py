"""Chat tab: main multi-agent conversational interface."""

import streamlit as st

from src.main import FinnieAIFinanceAssistant
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

USER_AVATAR = "🧑"
FINNIE_AVATAR = "🦊"

EXAMPLE_PROMPTS = [
    ("📘", "What is an ETF?"),
    ("💡", "Explain compound interest like I'm 10"),
    ("⚖️", "Index fund vs mutual fund?"),
    ("🌿", "Why is diversification important?"),
]


def _get_assistant() -> FinnieAIFinanceAssistant:
    if "assistant" not in st.session_state:
        with st.spinner("Waking Finnie up (loading knowledge base)..."):
            st.session_state.assistant = FinnieAIFinanceAssistant()
    return st.session_state.assistant


def _init_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def _render_history() -> None:
    for msg in st.session_state.chat_messages:
        avatar = USER_AVATAR if msg["role"] == "user" else FINNIE_AVATAR
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])


def _handle_query(user_query: str) -> None:
    st.session_state.chat_messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_query)

    assistant = _get_assistant()
    with st.chat_message("assistant", avatar=FINNIE_AVATAR):
        with st.spinner("Researching..."):
            try:
                response = assistant.ask(user_query, surface="streamlit")
            except Exception as e:
                logger.exception("Graph invocation failed in chat tab")
                response = (
                    "Sorry — something went wrong while answering. "
                    "Please try again or rephrase your question.\n\n"
                    f"_({type(e).__name__})_"
                )
        st.markdown(response)

    st.session_state.chat_messages.append({"role": "assistant", "content": response})


def render() -> None:
    _init_state()

    # Conversation history
    _render_history()

    # Empty state: show prompt suggestions
    if not st.session_state.chat_messages:
        st.markdown(
            '<div class="section-eyebrow">Try a starter question</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, (icon, prompt) in enumerate(EXAMPLE_PROMPTS):
            with cols[i % 2]:
                if st.button(f"{icon}  {prompt}", use_container_width=True, key=f"ex_{i}"):
                    _handle_query(prompt)
                    st.rerun()

    # Chat input — always at bottom
    if user_query := st.chat_input("Ask Finnie anything about finance..."):
        _handle_query(user_query)
        st.rerun()