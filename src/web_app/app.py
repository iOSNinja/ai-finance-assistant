"""
src/web_app/app.py — Finnie Streamlit UI entry point.

Run from project root:
    uv run streamlit run src/web_app/app.py
"""

from dotenv import load_dotenv

load_dotenv()


# Ensure project root on sys.path so `from src...` works under Streamlit's launcher
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

# Bridge Streamlit Cloud's st.secrets -> os.environ so existing code that
# reads from environment variables works identically in cloud + local.
# Locally, secrets come from .env via load_dotenv(); this block is a no-op.
try:
    for key, value in st.secrets.items():
        if isinstance(value, str):
            os.environ.setdefault(key, value)
except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    # No secrets file (running locally without .streamlit/secrets.toml) — fine
    pass

from src.web_app.components.sidebar import render_sidebar
from src.web_app.components.styles import CUSTOM_CSS
from src.web_app.tabs import chat, goals, knowledge, markets, portfolio


def configure_page() -> None:
    st.set_page_config(
        page_title="Finnie · AI-Powered Finance Tutor",
        page_icon="🦊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_hero() -> None:
    """Hero section: pill, gradient title, AI-explicit subtitle."""
    st.markdown(
        """
        <div class="hero-pill">
          <span class="hero-dot"></span>
          <span>AI agent online · Powered by LangGraph + OpenAI</span>
        </div>
        <h1>🦊 Finnie</h1>
        <p class="hero-subtitle">
            Your <strong>AI-powered</strong> finance tutor. Plain-English answers
            grounded in real sources — never invented.
            </p>
        """,
        unsafe_allow_html=True,
    )


def render_tabs() -> None:
    tab_chat, tab_portfolio, tab_markets, tab_goals, tab_knowledge = st.tabs(
        [
            "Chat",
            "Portfolio",
            "Markets",
            "Goals",
            "Library",
        ]
    )
    with tab_chat:
        chat.render()
    with tab_portfolio:
        portfolio.render()
    with tab_markets:
        markets.render()
    with tab_goals:
        goals.render()
    with tab_knowledge:
        knowledge.render()


def main() -> None:
    configure_page()
    render_sidebar()
    render_hero()
    render_tabs()


if __name__ == "__main__":
    main()
