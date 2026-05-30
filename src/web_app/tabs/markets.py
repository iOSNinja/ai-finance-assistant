"""Markets tab: placeholder UI; agent lands in Phase 3."""

import streamlit as st


def render() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        '<h2 style="margin:0;">📈 Markets</h2>'
        '<span class="feature-badge badge-coming-soon">In development</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Live indices, stock quotes, and historical trends.")

    st.markdown("")

    st.markdown('<div class="section-eyebrow">Major indices</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("S&P 500",   "—", "—")
    c2.metric("Dow Jones", "—", "—")
    c3.metric("NASDAQ",    "—", "—")
    c4.metric("VIX",       "—", "—")

    st.markdown("---")

    st.markdown('<div class="section-eyebrow">Stock lookup</div>', unsafe_allow_html=True)
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        st.text_input(
            "Ticker symbol",
            placeholder="e.g., AAPL, MSFT, NVDA",
            disabled=True,
            label_visibility="collapsed",
        )
    with col_btn:
        st.button("Look up", use_container_width=True, disabled=True)

    st.markdown("---")

    st.markdown('<div class="section-eyebrow">What\'s coming</div>', unsafe_allow_html=True)
    st.markdown(
        """
        - Real-time stock quotes via yfinance (Alpha Vantage backup)
        - Major index overview with day movement
        - Historical price charts (1D / 1W / 1M / YTD / 1Y)
        - Company overview: sector, market cap, fundamentals
        - 30-minute caching to respect API limits
        """
    )