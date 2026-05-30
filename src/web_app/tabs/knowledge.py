"""Library tab: direct browse/search of the Chroma KB. No LLM."""

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
    ("📘", "What is an ETF?"),
    ("💡", "Compound interest"),
    ("⚖️", "Asset allocation"),
    ("📈", "S&P 500"),
    ("🔁", "Dollar-cost averaging"),
    ("🏦", "Roth IRA vs Traditional"),
]


def _run_search(query: str, category: str | None, top_k: int = 5) -> list[dict]:
    return finance_qa_search.invoke({
        "query": query, "category": category, "top_k": top_k,
    })


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
        "Pure semantic retrieval — no LLM in the loop."
    )

    st.markdown("")

    # ── FIX for kb_query bug ──────────────────────────────────────────────
    # We use a "pending value" pattern: the widget reads its initial value
    # from `_kb_pending_query`, and popular-topic buttons set THAT (never
    # `kb_query` directly), then trigger a rerun. The widget owns its key.
    if "_kb_pending_query" not in st.session_state:
        st.session_state._kb_pending_query = ""

    # Search controls
    col_q, col_cat = st.columns([3, 1])
    with col_q:
        query = st.text_input(
            "Search the KB",
            value=st.session_state._kb_pending_query,
            placeholder="e.g., diversification, compound interest, ETFs",
            key="kb_query",
            label_visibility="collapsed",
        )
    with col_cat:
        category_choice = st.selectbox(
            "Category", CATEGORIES, label_visibility="collapsed"
        )

    # Popular-topic chips
    st.markdown(
        '<div class="section-eyebrow" style="margin-top:1rem;">Popular topics</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for i, (icon, topic) in enumerate(POPULAR_TOPICS):
        if cols[i % 3].button(f"{icon}  {topic}", use_container_width=True, key=f"pop_{i}"):
            st.session_state._kb_pending_query = topic
            st.rerun()

    if not query:
        return

    st.markdown("---")

    category_filter = category_choice if category_choice != "All" else None
    with st.spinner("Searching..."):
        try:
            results = _run_search(query, category_filter)
        except Exception as e:
            st.error(f"Search failed: {type(e).__name__}: {e}")
            return

    _render_results(results, query)