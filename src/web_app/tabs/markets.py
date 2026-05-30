"""Markets tab: placeholder UI; Market Analysis Agent lands in Phase 3."""

import streamlit as st


def render() -> None:
    st.markdown("## 📈 Markets")
    st.caption("Live market data: indices, stock quotes, historical trends.")

    st.info(
        "🚧 **Market Analysis Agent is in active development.** "
        "Live data will plug into the UI below in Phase 3."
    )

    # --- Major Indices ---
    st.markdown("### Major Indices")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("S&P 500", "—", "—")
    with col2:
        st.metric("Dow Jones", "—", "—")
    with col3:
        st.metric("NASDAQ", "—", "—")
    with col4:
        st.metric("VIX", "—", "—")

    st.divider()

    # --- Stock Lookup ---
    st.markdown("### Stock Lookup")
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        st.text_input(
            "Enter ticker symbol",
            placeholder="e.g., AAPL, MSFT, NVDA",
            disabled=True,
            label_visibility="collapsed",
        )
    with col_btn:
        st.button("🔍 Look up", use_container_width=True, disabled=True)

    st.divider()

    st.markdown("### Coming in Phase 3")
    st.markdown(
        """
        - **Real-time stock quotes** via yfinance (Alpha Vantage as fallback)
        - **Major index overview** (S&P 500, Dow, NASDAQ, VIX)
        - **Historical price charts** (1D / 1W / 1M / YTD / 1Y)
        - **Company overview**: sector, market cap, fundamentals
        - **30-minute caching** to respect API limits
        """
    )