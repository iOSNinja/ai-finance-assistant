"""Sidebar: session controls, app info, links."""

import streamlit as st


def render_sidebar() -> None:
    """Render the persistent left sidebar."""
    with st.sidebar:
        st.markdown("## ⚙️ Controls")
        st.divider()

        # Session reset
        st.markdown("### Conversation")
        if st.button("🔄 New conversation", use_container_width=True):
            _reset_conversation()
            st.rerun()

        st.caption("Clears chat history and starts a fresh memory thread.")

        st.divider()

        # About
        st.markdown("### About Finnie")
        st.caption(
            "Finnie is a multi-agent AI assistant for personal finance "
            "education. Built with LangGraph, RAG, and OpenAI."
        )
        st.caption("Sources are cited where used.")

        st.divider()

        # Compliance
        st.warning(
            "⚠️ **Educational content only.** Not personalized financial "
            "advice. Consult a qualified advisor for decisions specific to "
            "your situation.",
            icon="⚠️",
        )

        st.divider()

        # Tech stack
        st.markdown("### Tech")
        st.caption(
            "🔗 LangGraph · Chroma · OpenAI gpt-4o · Streamlit"
        )


def _reset_conversation() -> None:
    """Clear chat-tab history and start a new memory thread on the assistant."""
    if "chat_messages" in st.session_state:
        st.session_state.chat_messages = []
    if "assistant" in st.session_state:
        st.session_state.assistant._new_session()