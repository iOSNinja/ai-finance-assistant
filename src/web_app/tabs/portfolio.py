"""Portfolio tab: wired to analyze_portfolio tool for instant metrics + chart."""

import streamlit as st
import pandas as pd

from src.agents.portfolio.tool import analyze_portfolio

VALID_CLASSES = ["stocks", "bonds", "cash", "other"]

SAMPLE_PORTFOLIO = [
    {"ticker": "VTI",  "value_usd": 30000.0, "asset_class": "stocks", "expense_ratio": 0.03},
    {"ticker": "VXUS", "value_usd": 10000.0, "asset_class": "stocks", "expense_ratio": 0.07},
    {"ticker": "BND",  "value_usd": 10000.0, "asset_class": "bonds",  "expense_ratio": 0.03},
]


def _initialize_holdings() -> None:
    if "portfolio_holdings" not in st.session_state:
        st.session_state.portfolio_holdings = []


def _render_holdings_editor() -> None:
    """Editable table of holdings."""
    st.markdown('<div class="section-eyebrow">Your holdings</div>', unsafe_allow_html=True)

    if not st.session_state.portfolio_holdings:
        st.info("No holdings yet. Add one below or load the sample portfolio.")
        return

    df = pd.DataFrame(st.session_state.portfolio_holdings)
    edited = st.data_editor(
        df,
        column_config={
            "ticker":        st.column_config.TextColumn("Ticker", required=True),
            "value_usd":     st.column_config.NumberColumn("$ Value", min_value=0.0, format="$%.2f"),
            "asset_class":   st.column_config.SelectboxColumn("Asset class", options=VALID_CLASSES),
            "expense_ratio": st.column_config.NumberColumn("Expense ratio %", min_value=0.0, format="%.3f"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="portfolio_editor",
    )
    st.session_state.portfolio_holdings = edited.to_dict("records")


def _render_results(result: dict) -> None:
    st.markdown("---")
    st.markdown('<div class="section-eyebrow">Portfolio metrics</div>', unsafe_allow_html=True)

    # Allow metric values to wrap onto multiple lines instead of truncating
    # (otherwise long labels like "Moderate-Aggressive" show as "Moderate-Ag...")
    st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        white-space: normal !important;
        word-wrap: break-word;
        overflow: visible;
        font-size: 1.5rem;
        line-height: 1.2;
    }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total value",       f"${result['total_value']:,.0f}")
    c2.metric("# Holdings",        result["num_holdings"])
    c3.metric("Diversification",   f"{result['diversification_score']:.2f}",
              help="Higher = more diversified (0=concentrated, 1=perfectly spread)")
    c4.metric("Risk profile",      result["risk_profile"])

    if result["weighted_expense_ratio"] is not None:
        st.caption(
            f"📉 Weighted expense ratio: **{result['weighted_expense_ratio']:.3f}%** "
            "(based on the expense ratios you provided)"
        )

    st.markdown("### Allocation by asset class")
    cls_df = pd.DataFrame(
        list(result["allocation_by_asset_class"].items()),
        columns=["Asset class", "% of portfolio"],
    ).set_index("Asset class")
    st.bar_chart(cls_df)

    st.markdown("### Allocation by ticker")
    tic_df = pd.DataFrame(
        list(result["allocation_by_ticker"].items()),
        columns=["Ticker", "% of portfolio"],
    ).set_index("Ticker")
    st.bar_chart(tic_df)

    st.caption(
        f"⚠️ Largest position is {result['largest_position_pct']:.1f}% of portfolio. "
        "This is a snapshot — it doesn't account for trading fees, taxes on "
        "rebalancing, or future market moves."
    )


def render() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        '<h2 style="margin:0;">📊 Portfolio</h2>'
        '<span class="feature-badge badge-live">Live</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Allocation, diversification, expense ratios, risk — at a glance.")

    st.markdown("")

    _initialize_holdings()

    # Load actions
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📁  Load sample portfolio", use_container_width=True):
            st.session_state.portfolio_holdings = list(SAMPLE_PORTFOLIO)
            st.rerun()
    with c2:
        if st.button("🗑️  Clear holdings", use_container_width=True):
            st.session_state.portfolio_holdings = []
            st.rerun()

    st.markdown("")
    _render_holdings_editor()

    # Add-row form (for users who want explicit entry)
    with st.expander("➕  Add a holding"):
        col_t, col_v, col_c, col_e = st.columns([1, 1, 1, 1])
        with col_t: new_ticker = st.text_input("Ticker", key="new_ticker")
        with col_v: new_value  = st.number_input("$ Value", min_value=0.0, value=1000.0, key="new_value")
        with col_c: new_class  = st.selectbox("Asset class", VALID_CLASSES, key="new_class")
        with col_e: new_er     = st.number_input("Expense ratio %", min_value=0.0, value=0.0, format="%.3f", key="new_er")

        if st.button("Add", use_container_width=True):
            if new_ticker.strip():
                st.session_state.portfolio_holdings.append({
                    "ticker":        new_ticker.strip().upper(),
                    "value_usd":     float(new_value),
                    "asset_class":   new_class,
                    "expense_ratio": float(new_er) if new_er > 0 else None,
                })
                st.rerun()

    if not st.session_state.portfolio_holdings:
        return

    st.markdown("")
    if st.button("📊  Analyze portfolio", use_container_width=True, type="primary"):
        # Strip None expense_ratio entries — the tool only expects them when present
        clean = [
            {k: v for k, v in h.items() if v is not None}
            for h in st.session_state.portfolio_holdings
        ]
        try:
            result = analyze_portfolio.invoke({"holdings": clean})
        except Exception as e:
            st.error(f"{type(e).__name__}: {e}")
            return
        _render_results(result)