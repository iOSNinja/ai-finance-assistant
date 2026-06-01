"""Markets tab: wired to yfinance-backed tools for live data + chart."""

from datetime import datetime

import pandas as pd
import streamlit as st

from src.agents.market.tool import (
    get_historical_prices,
    get_index_overview,
    get_stock_quote,
)


def _render_quote_card(name: str, q: dict) -> None:
    """Render a single quote as an st.metric."""
    if "error" in q:
        st.metric(name, "—", q["error"])
        return
    delta = f"{q['change_pct']:+.2f}%"
    st.metric(name, f"${q['current_price']:,.2f}", delta)


def _render_indices() -> None:
    st.markdown('<div class="section-eyebrow">Major indices</div>', unsafe_allow_html=True)
    with st.spinner("Fetching indices..."):
        overview = get_index_overview.invoke({})
    cols = st.columns(len(overview["indices"]))
    for col, (name, quote) in zip(cols, overview["indices"].items()):
        with col:
            _render_quote_card(name, quote)
    if overview.get("cache_hit"):
        st.caption(f"🕒 Cached — refreshed at most {overview['indices'].get('S&P 500', {}).get('cache_hit') and '30 min' or 'recently'} ago.")


def _render_stock_lookup() -> None:
    st.markdown('<div class="section-eyebrow">Stock lookup</div>', unsafe_allow_html=True)
    col_in, col_period, col_btn = st.columns([3, 2, 1])
    with col_in:
        ticker = st.text_input(
            "Ticker symbol",
            placeholder="e.g., AAPL, MSFT, NVDA",
            label_visibility="collapsed",
            key="market_ticker_input",
        )
    with col_period:
        period = st.selectbox(
            "Period",
            ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd"],
            index=1,
            label_visibility="collapsed",
        )
    with col_btn:
        go = st.button("Look up", use_container_width=True, type="primary")

    if not go or not ticker.strip():
        return

    with st.spinner(f"Fetching {ticker.upper()}..."):
        quote = get_stock_quote.invoke({"ticker": ticker})

    if "error" in quote:
        st.error(quote["error"])
        return

    # Headline metrics
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        quote["ticker"],
        f"${quote['current_price']:,.2f}",
        f"{quote['change_pct']:+.2f}%",
    )
    c2.metric("Prev close",  f"${quote['prev_close']:,.2f}")
    c3.metric("Day high",    f"${quote['day_high']:,.2f}" if quote['day_high'] else "—")
    c4.metric("Day low",     f"${quote['day_low']:,.2f}"  if quote['day_low']  else "—")

    c5, c6 = st.columns(2)
    c5.metric("52-week high", f"${quote['fifty_two_week_high']:,.2f}" if quote['fifty_two_week_high'] else "—")
    c6.metric("52-week low",  f"${quote['fifty_two_week_low']:,.2f}"  if quote['fifty_two_week_low']  else "—")

    if quote.get("cache_hit"):
        st.caption("🕒 Cached quote — may be up to 30 min old.")

    # Historical chart
    st.markdown(f"### Price history — {period}")
    with st.spinner("Fetching history..."):
        hist = get_historical_prices.invoke({"ticker": ticker, "period": period})

    if "error" in hist:
        st.warning(f"Couldn't fetch history: {hist['error']}")
        return

    df = pd.DataFrame(hist["prices"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    st.line_chart(df["close"], height=300)
    st.caption(
        f"{hist['data_points']} data points · {hist['start_date']} → {hist['end_date']}"
    )


def render() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        '<h2 style="margin:0;">📈 Markets</h2>'
        '<span class="feature-badge badge-live">Live</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Live market data via yfinance. "
        f"Last loaded: {datetime.now().strftime('%H:%M:%S')}."
    )

    st.markdown("")

    _render_indices()

    st.markdown("---")

    _render_stock_lookup()

    st.markdown("---")
    st.caption(
        "⚠️ Market data may be delayed up to 15 minutes. Quotes outside US "
        "trading hours (9:30 AM – 4 PM ET) reflect the last available close. "
        "Cached data is refreshed every 30 minutes."
    )