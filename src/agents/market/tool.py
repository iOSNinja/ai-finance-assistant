"""
src/agents/market/tool.py — Live market data tools backed by yfinance.

Three tools:
  - get_stock_quote(ticker)         — current price + day change + 52-wk range
  - get_historical_prices(ticker, period)  — time-series for charts
  - get_index_overview()            — S&P 500, Dow, NASDAQ, VIX snapshot

Module-level in-memory cache with TTL to respect yfinance's implicit
rate limits and to keep the UI snappy. Cache TTLs come from config.yaml.
"""

import yfinance as yf
import time
from langchain_community.tools import tool
from langsmith import traceable

from src.utils.logger import setup_logger
from src.core.config import MARKET_CONFIG

logger = setup_logger("finnie.agents.market.tool")

# Define a simple dict as Local Cache: {key, (value, expires_at)}
_cache: dict[str, tuple[dict, float]] = {}

CACHE_TTL_QUOTE = MARKET_CONFIG.get("cache_ttl_quote", 1800) # default to 30 mins
CACHE_TTL_HISTORY = MARKET_CONFIG.get("cache_ttl_history", 3600) # default to 60 mins

VALID_PERIODS = {"1d", "5d", "10d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}

# MAJOR INDICES
INDEX_SYMBOLS: dict[str, str] = {
    "S&P 500":   "^GSPC",
    "Dow Jones": "^DJI",
    "NASDAQ":    "^IXIC",
    "VIX":       "^VIX",
}

def _cache_get(key: str) -> dict | None:
    """Return cached value if present and is not expired, else None"""
    entry = _cache.get(key)

    if entry is None:
        return None
    
    value, expires_at = entry
    if time.time() > expires_at:
        del _cache[key]
        return None
    
    return value

def _cache_set(key: str, value: dict, ttl_seconds: float) -> None:
    """store value with TTL as a tuple for the key passed in."""
    _cache[key] = value, time.time() + ttl_seconds


# private method
@traceable(name="yfinance.fetch_quote", run_type="tool")
def _fetch_quote(ticker: str) -> dict:
    """Internal helper methid used by get_stock_quote AND get_index_overview.

    Returns either a quote dict OR {"error": "..."} if data is unavailable.
    Centralizes the yfinance interaction + caching so we don't duplicate logic.
    """
    ticker = ticker.upper().strip() # cleaning
    cache_key = f"quote:{ticker}" # to differentiate from historical ticker data

    # Check in local cache. If hit, return along with cache_hit flag
    if (cached := _cache_get(cache_key)) is not None: # using Walrus operator :=
        logger.info("quote cache hit", extra={"ticker": ticker})
        return {**cached, "cache_hit": True}

    # If not in local cache, fetch using yfinance API
    logger.info("quote not in local cache, fetching", extra={"ticker": ticker})
    try:
        t = yf.Ticker(ticker)
        # We use .fast_info because we only need the basics. 
        # This is a 10x latency win with no loss for our use case. 
        # .info to be used only when we need company description, sector, employee count, etc. — fields that fast_info doesn't expose.
        # And .info makes multiple HTTP calls to gather all data points.
        fast = t.fast_info

        current = fast.last_price
        previous = fast.previous_close

        if current is None or previous is None:
            return {"error": f"No price data for {ticker!r}. Check the symbol."}
        
        change = float(current) - float(previous)
        change_pct = (change / float(previous)) * 100 if previous else 0.0

        result = {
            "ticker":              ticker,
            "current_price":       round(float(current), 2),
            "prev_close":          round(float(previous), 2),
            "change":              round(change, 2),
            "change_pct":          round(change_pct, 2),
            "day_high":            round(float(fast.day_high), 2) if fast.day_high else None,
            "day_low":             round(float(fast.day_low), 2) if fast.day_low else None,
            "fifty_two_week_high": round(float(fast.year_high), 2) if fast.year_high else None,
            "fifty_two_week_low":  round(float(fast.year_low), 2) if fast.year_low else None,
            "currency":            fast.currency or "USD",
            "cache_hit":           False,
        }

        _cache_set(cache_key, result, CACHE_TTL_QUOTE)
        return result

    except Exception as e:
        logger.error("quote fetch failed", extra={"ticker": ticker, "error_type": type(e).__name__, "error": str(e)})
        return {"error": f"Failed to fetch {ticker!r}: {type(e).__name__}"}


@tool
def get_stock_quote(ticker: str) -> dict:
    """Get current price + day movement + 52-week range for a single ticker.

    Args:
        ticker: Stock or ETF symbol (e.g., "AAPL", "MSFT", "VTI").
                Case-insensitive; whitespace stripped.

    Returns:
        On success: dict with keys
          - ticker, current_price, prev_close, change, change_pct,
            day_high, day_low, fifty_two_week_high, fifty_two_week_low,
            currency, cache_hit
        On failure: {"error": "..."}
    """
    return _fetch_quote(ticker)

@tool
def get_historical_prices(ticker: str, period: str = "1mo") -> dict:
    """Get historical closing prices for a ticker.

    Args:
        ticker: Stock or ETF symbol (e.g., "AAPL").
        period: One of "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y",
                "5y", "10y", "ytd", "max". Default "1mo".

    Returns:
        On success: dict with keys
          - ticker, period, start_date, end_date, data_points,
            prices (list of {date, close}), cache_hit
        On failure: {"error": "..."}
    """
    ticker = ticker.upper().strip()

    if period not in VALID_PERIODS:
        return {"error": f"period must be one of {sorted(VALID_PERIODS)} (got {period!r})"}

    cache_key = f"hist:{ticker}:{period}"
    if (cached := _cache_get(cache_key)) is not None:
        logger.info("history cache hit", extra={"ticker": ticker, "period": period})
        return {**cached, "cache_hit": True}

    logger.info("history fetch", extra={"ticker": ticker, "period": period})
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period)
        if df.empty:
            return {"error": f"No historical data for {ticker!r}."}

        prices = [
            {"date": idx.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)}
            for idx, row in df.iterrows()
            # iterrows() — iterates over DataFrame rows. 
            # Each iteration yields (index, row) where: 
                # idx is the row's index (a pandas Timestamp object)
                # row is a Series with the column values
        ]

        result = {
            "ticker":      ticker,
            "period":      period,
            "start_date":  prices[0]["date"],
            "end_date":    prices[-1]["date"],
            "data_points": len(prices),
            "prices":      prices,
            "cache_hit":   False,
        }
        _cache_set(cache_key, result, CACHE_TTL_HISTORY)
        return result

    except Exception as e:
        logger.error("history fetch failed", extra={"ticker": ticker, "period": period, "error_type": type(e).__name__, "error": str(e)})
        return {"error": f"Failed to fetch history for {ticker!r}: {type(e).__name__}"}
    

@tool
def get_index_overview() -> dict:
    """Get a snapshot of the major US market indices: S&P 500, Dow, NASDAQ, VIX.

    Takes no arguments. Use for "how's the market doing?" queries.

    Returns:
        On success: dict with keys
          - indices: dict mapping index_name → quote_dict (same shape as
            get_stock_quote return value)
          - cache_hit: bool
    """
    cache_key = "indices:overview"
    if (cached := _cache_get(cache_key)) is not None:
        logger.info("indices cache hit")
        return {**cached, "cache_hit": True}

    logger.info("indices fetch")
    indices: dict[str, dict] = {}
    for name, symbol in INDEX_SYMBOLS.items():
        indices[name] = _fetch_quote(symbol)

    result = {"indices": indices, "cache_hit": False}
    _cache_set(cache_key, result, CACHE_TTL_QUOTE)

    return result


market_tools_list = [get_stock_quote, get_historical_prices, get_index_overview]