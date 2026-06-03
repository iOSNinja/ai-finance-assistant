"""Markets tab: wired to yfinance-backed tools for live data + chart."""

from datetime import datetime

import pandas as pd
import streamlit as st

from src.agents.market.tool import (
    get_historical_prices,
    get_index_overview,
    get_stock_quote,
)

import yfinance as yf
from src.utils.logger import setup_logger

logger = setup_logger("finnie.web_app.tabs.markets")

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

    st.line_chart(df["close"], height=300)
    st.caption(
        f"{hist['data_points']} data points · {hist['start_date']} → {hist['end_date']}"
    )

    # News section after the chart
    st.markdown("---")
    _render_ticker_news(quote["ticker"])


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

def _render_news_card(article: dict) -> None:
    """Render a single news article as a styled card."""
    title    = article.get("title", "(untitled)")
    url      = article.get("url", "#")
    source   = article.get("source", "unknown source")
    date     = article.get("published_date", "")
    snippet  = (article.get("snippet", "") or "")[:240].strip()
    if len(article.get("snippet", "")) > 240:
        snippet += "..."

    st.markdown(
        f'<div class="finnie-card" style="padding:16px;margin-bottom:10px;">'
        f'  <div style="font-weight:600;font-size:1rem;line-height:1.3;">'
        f'    <a href="{url}" target="_blank" style="color:var(--text-primary);">{title}</a>'
        f'  </div>'
        f'  <div style="font-size:0.78rem;color:var(--text-muted);margin-top:6px;'
        f'              text-transform:uppercase;letter-spacing:0.05em;">'
        f'    {source} · {date}'
        f'  </div>'
        f'  <div style="font-size:0.92rem;color:var(--text-secondary);margin-top:10px;line-height:1.5;">'
        f'    {snippet}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _fetch_ticker_news(ticker: str, limit: int = 5) -> list[dict]:
    """Fetch ticker-specific news from Yahoo Finance via yfinance.

    Returns normalized news items: {title, url, source, published_date, snippet}.
    Handles both the older flat yfinance news format and the newer wrapped one.
    """
    ticker_upper = ticker.upper().strip()
    logger.info("Fetching ticker news", extra={"ticker": ticker_upper, "limit": limit})

    try:
        t = yf.Ticker(ticker_upper)
        raw = t.news[:limit]
        logger.info("Fetched raw news items", extra={"ticker": ticker_upper, "raw_count": len(raw)})
    except Exception:
        logger.exception("Failed to fetch ticker news from yfinance | ticker=%s", ticker_upper)
        return []

    normalized: list[dict] = []
    skipped_count = 0

    for index, item in enumerate(raw, start=1):
        logger.debug("Normalizing news item", extra={"ticker": ticker_upper, "item_index": index})

        # Newer yfinance wraps data in "content"; older flattens it
        if "content" in item and isinstance(item["content"], dict):
            logger.debug("Detected wrapped yfinance news format", extra={"ticker": ticker_upper, "item_index": index})

            c = item["content"]
            title = c.get("title", "")
            summary = c.get("summary", "") or c.get("description", "")

            # canonicalUrl can be a dict or a string depending on yfinance version
            canonical = c.get("canonicalUrl") or c.get("clickThroughUrl") or {}
            url = canonical.get("url", "") if isinstance(canonical, dict) else str(canonical)

            provider = c.get("provider") or {}
            source = provider.get("displayName", "") if isinstance(provider, dict) else str(provider)

            pub_date = c.get("pubDate", "")
        else:
            logger.debug("Detected flat yfinance news format", extra={"ticker": ticker_upper, "item_index": index})

            # Old flat format
            title = item.get("title", "")
            url = item.get("link", "")
            source = item.get("publisher", "")
            summary = ""

            ts = item.get("providerPublishTime")
            pub_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""

        if title and url:
            normalized.append({
                "title": title,
                "url": url,
                "source": source or "Yahoo Finance",
                "published_date": pub_date,
                "snippet": summary[:240] + ("..." if len(summary) > 240 else ""),
            })

            logger.debug(
                "Normalized news item",
                extra={"ticker": ticker_upper, "item_index": index, "source": source or "Yahoo Finance", "title": title}
            )
        else:
            skipped_count += 1
            logger.warning(
                "Skipping news item - missing title or url",
                extra={"ticker": ticker_upper, "item_index": index, "has_title": bool(title), "has_url": bool(url)}
            )

    logger.info(
        "Finished normalizing ticker news",
        extra={"ticker": ticker_upper, "normalized_count": len(normalized), "skipped_count": skipped_count}
    )

    return normalized


def _render_ticker_news(ticker: str) -> None:
    """Fetch + render ticker-specific news from Yahoo Finance."""
    ticker_upper = ticker.upper().strip()
    logger.info("Rendering ticker news section", extra={"ticker": ticker_upper})

    st.markdown("### 📰 Recent news")

    with st.spinner(f"Fetching news on {ticker_upper}..."):
        articles = _fetch_ticker_news(ticker_upper, limit=5)

    if not articles:
        logger.info("No news articles to render", extra={"ticker": ticker_upper})
        st.info(f"No recent news found for {ticker_upper}.")
        return

    logger.info(
        "Rendering news articles",
        extra={"ticker": ticker_upper, "article_count": len(articles)}
    )

    for index, article in enumerate(articles, start=1):
        logger.info(
            "Rendering news card",
            extra={"ticker": ticker_upper, "item_index": index, "title": article.get("title", "")}
        )
        _render_news_card(article)

    logger.info("Finished rendering ticker news section", extra={"ticker": ticker_upper})