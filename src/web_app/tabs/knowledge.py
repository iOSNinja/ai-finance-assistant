"""Knowledge tab: direct browse/search of the Chroma KB. No LLM involved — pure retrieval."""

import streamlit as st

from src.agents.qa.tool import finance_qa_search

CATEGORIES = [
    "All",
    "investing_basics",
    "portfolio_management",
    "market_analysis",
    "goal_planning",
    "tax_education",
]

POPULAR_TOPICS = [
    "What is an ETF?",
    "Compound interest",
    "Asset allocation",
    "S&P 500",
    "Dollar-cost averaging",
    "Roth IRA vs Traditional",
]


def _run_search(query: str, category: str | None, top_k: int = 5) -> list[dict]:
    """Direct call to the search tool — no LLM, no synthesizer."""
    return finance_qa_search.invoke({
        "query": query,
        "category": category,
        "top_k": top_k,
    })


def _render_results(results: list[dict], query: str) -> None:
    """Render retrieved chunks with relevance indicators."""
    if not results:
        st.warning(
            "No results found. Try a broader query or remove the category filter."
        )
        return

    st.markdown(f"**Found {len(results)} chunk(s)** for: *{query}*")

    for i, r in enumerate(results, 1):
        rel = r["relevance"]
        emoji = "🟢" if rel >= 0.7 else "🟡" if rel >= 0.5 else "🔴"
        header = f"{emoji} #{i} · [{r['category']}] · relevance {rel}"
        with st.expander(header):
            st.markdown(r["text"])
            st.caption(f"📎 Source: [{r['source_url']}]({r['source_url']})")


def render() -> None:
    st.markdown("## 📚 Knowledge Base")
    st.caption(
        "Browse and search Finnie's curated educational content directly. "
        "Pure semantic retrieval — no LLM in the loop, so you see exactly what's stored."
    )

    # Search controls
    col_q, col_cat = st.columns([3, 1])
    with col_q:
        query = st.text_input(
            "Search the KB",
            placeholder="e.g., diversification, compound interest, ETFs",
            key="kb_query",
            label_visibility="collapsed",
        )
    with col_cat:
        category_choice = st.selectbox(
            "Category", CATEGORIES, label_visibility="collapsed"
        )

    # Popular topics — quick-click chips
    st.markdown("**Popular topics:**")
    cols = st.columns(3)
    for i, topic in enumerate(POPULAR_TOPICS):
        if cols[i % 3].button(topic, use_container_width=True, key=f"pop_{i}"):
            st.session_state.kb_query = topic
            st.rerun()

    if not query:
        return

    st.divider()

    # Run search
    category_filter = category_choice if category_choice != "All" else None
    with st.spinner("Searching..."):
        try:
            results = _run_search(query, category_filter)
        except Exception as e:
            st.error(f"Search failed: {type(e).__name__}: {e}")
            return

    _render_results(results, query)