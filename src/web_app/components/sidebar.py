"""Sidebar: session controls, about, compliance."""

import streamlit as st


def render_sidebar() -> None:
    with st.sidebar:
        # Brand block
        st.markdown(
            """
            <div style="padding: 8px 0 16px 0;">
            <div style="font-family: 'Outfit', sans-serif; font-size: 1.5rem;
                        font-weight: 800; color: #fafafa;">
                🦊 Finnie
            </div>
            <div style="font-size: 0.8rem; color: #71717a; margin-top: 2px;">
                AI-powered finance tutor
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("### Conversation")
        if st.button("Start new conversation", use_container_width=True):
            _reset_conversation()
            st.rerun()
        st.caption("Clears chat history and starts a fresh memory thread.")

        st.markdown("---")
        st.markdown("### Agents")
        st.markdown(
            """
            <div style="display: flex; flex-direction: column; gap: 6px;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Finance Q&amp;A</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Market Analysis</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Portfolio Analysis</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Goal Planning</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">News Synthesizer</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #a1a1aa; font-size: 0.85rem;">Tax Education</span>
                <span class="feature-badge badge-live">Live</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("### About")
        st.caption(
            "Finnie is a multi-agent AI assistant for personal finance "
            "education. Built with LangGraph, RAG, and OpenAI."
        )

        st.markdown("---")
        st.warning(
            "**Educational content only.** Not personalized financial advice. "
            "Consult a qualified advisor for decisions specific to your situation.",
            icon="⚠️",
        )


def _reset_conversation() -> None:
    if "chat_messages" in st.session_state:
        st.session_state.chat_messages = []
    if "assistant" in st.session_state:
        st.session_state.assistant._new_session()