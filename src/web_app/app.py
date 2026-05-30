"""
src/web_app/app.py — Finnie Streamlit UI entry point.

Run from project root:
    uv run streamlit run src/web_app/app.py
"""

import streamlit as st

from src.web_app.components.sidebar import render_sidebar
from src.web_app.tabs import chat, goals, knowledge, markets, portfolio


def configure_page() -> None:
    """Set page-level config. MUST be the first Streamlit call in the app."""
    st.set_page_config(
        page_title="Finnie — AI Finance Assistant",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_header() -> None:
    """Top banner with title and tagline."""
    col_title, col_status = st.columns([4, 1])
    with col_title:
        st.markdown("# 💰 Finnie")
        st.markdown("*Your AI-powered personal finance education companion.*")
    with col_status:
        st.markdown("")
        st.markdown("")
        st.success("✓ Online", icon="🟢")
    st.divider()


def render_tabs() -> None:
    """Five-tab layout."""
    tab_chat, tab_portfolio, tab_markets, tab_goals, tab_knowledge = st.tabs([
        "💬 Chat",
        "📊 Portfolio",
        "📈 Markets",
        "🎯 Goals",
        "📚 Knowledge",
    ])

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
    render_header()
    render_tabs()


if __name__ == "__main__":
    main()