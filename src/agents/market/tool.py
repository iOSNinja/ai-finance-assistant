"""
src/agents/market/tool.py — Live market data tools backed by yfinance.

Three tools:
  - get_stock_quote(ticker)         — current price + day change + 52-wk range
  - get_historical_prices(ticker, period)  — time-series for charts
  - get_index_overview()            — S&P 500, Dow, NASDAQ, VIX snapshot

Module-level in-memory cache with TTL to respect yfinance's implicit
rate limits and to keep the UI snappy. Cache TTLs come from config.yaml.

Production hardening notes (future):
  - Add Alpha Vantage as a fallback when yfinance fails
  - Add stale-cache fallback when network is fully down
  - Persistent cache (redis/sqlite) if running multi-process
"""

import yfinance as yf
import time
from langchain_community.tools import tool

from src.utils.logger import setup_logger
from src.core.config import MARKET_CONFIG

logger = setup_logger("finnie.agents,market.tool")

# Define a simple dict as Local Cache: {key, (value, expires_at)}
_cache: dict[str, tuple[dict, float]] = {}

CACHE_TTL_QUOTE = MARKET_CONFIG.get("cache_ttl_quote", 1800) # default to 30 mins
CACHE_TTL_HISTORY = MARKET_CONFIG.get("cache_ttl_history", 3600) # default to 60 mins

def _cache_get(key: str) -> dict | None:
    """Return cached value if present and is not expired, else None"""
    entry = _cache.get(key)

    if entry is None:
        return None
    
    value, expires_at = entry
    if time.time() > expires_at:
        del _cache(key)
        return None
    
    return value

def _cache_set(key: str, value: dict, ttl_seconds: float) -> None:
    """store value with TTL as a tuple for the key passed in."""
    _cache[key] = value, time.time() + ttl_seconds

