"""Library tab: direct, LLM-free browse/search of the Chroma KB."""

import streamlit as st

from src.rag.retriever import kb_search

CATEGORIES = [
    "All",
    "investing_basics",
    "portfolio_management",
    "market_analysis",
    "goal_planning",
    "tax_education",
]

POPULAR_TOPICS = [
    ("📘", "What is an ETF?"),
    ("💡", "Compound interest"),
    ("⚖️", "Asset allocation"),
    ("📈", "S&P 500"),
    ("🔁", "Dollar-cost averaging"),
    ("🏦", "Roth IRA vs Traditional"),
]


def _render_results(results: list[dict], query: str) -> None:
    if not results:
        st.warning("No results. Try a broader query or remove the category filter.")
        return
    st.markdown(f"**{len(results)} chunk(s)** for: _{query}_")
    for i, r in enumerate(results, 1):
        rel = r["relevance"]
        emoji = "🟢" if rel >= 0.7 else "🟡" if rel >= 0.5 else "🔴"
        with st.expander(f"{emoji}  #{i} · {r['category']} · relevance {rel}"):
            st.markdown(r["text"])
            st.caption(f"Source: [{r['source_url']}]({r['source_url']})")


def render() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        '<h2 style="margin:0;">📚 Knowledge Library</h2>'
        '<span class="feature-badge badge-live">Live</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Browse Finnie's curated educational content directly. "
        "Pure semantic retrieval — no LLM in the loop. Searches across all categories."
    )

    st.markdown("")

    # ── Apply pending query (set by a popular-topic button) BEFORE widgets render.
    # Must happen here — once st.text_input(key="kb_query") instantiates the widget,
    # Streamlit forbids writes to st.session_state["kb_query"].
    if st.session_state.get("_kb_pending_query"):
        st.session_state["kb_query"] = st.session_state["_kb_pending_query"]
        st.session_state["_kb_pending_query"] = ""

    # Search controls — note: NO `value=` arg; session_state IS the value
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

    # Popular-topic chips — set pending and rerun; the block above will apply on next run
    st.markdown(
        '<div class="section-eyebrow" style="margin-top:1rem;">Popular topics</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for i, (icon, topic) in enumerate(POPULAR_TOPICS):
        if cols[i % 3].button(f"{icon}  {topic}", use_container_width=True, key=f"pop_{i}"):
            st.session_state["_kb_pending_query"] = topic
            st.rerun()

    if not query:
        return

    st.markdown("---")

    category_filter = category_choice if category_choice != "All" else None
    with st.spinner("Searching..."):
        results = kb_search(query, category_filter, top_k=5)

    _render_results(results, query)