"""
src/agents/news/tool.py — Financial-news search via Tavily.

One tool: search_financial_news.

Tavily is queried with a domain allowlist (reputable financial sources only)
to filter out blog spam and clickbait. Results are cached with a 1-hour TTL
since news shifts daily, not minute-by-minute.

Tavily API key is read from TAVILY_API_KEY env var.
"""

import os
import time

from langchain_core.tools import tool
from langsmith import traceable
from tavily import TavilyClient

from src.core.config import NEWS_CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("finnie.agents.news.tool")

# Hard coding allowed list of reputable financial sources list to filter out blog spam and clickbait
ALLOWED_DOMAINS = [
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "cnbc.com",
    "finance.yahoo.com",
    "marketwatch.com",
    "ft.com",
    "investing.com",
    "barrons.com",
    "fortune.com",
    "businessinsider.com",
    "seekingalpha.com",
]

# Local cache: {key, (value, expires_at)}
_cache: dict[str, tuple[dict, float]] = {}

CACHE_TTL = NEWS_CONFIG.get("cache_ttl_seconds", 3600)  # default to 1 hr
DEFAULT_MAX_RESULTS = NEWS_CONFIG.get("max_results", 5)


# Local cache implementation
def _cache_get(key: str) -> dict | None:
    """Return cached value if present and not expired, else None."""
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


# Tavily client - singleton at import time
_tavily_key = os.environ.get("TAVILY_API_KEY", "")

if not _tavily_key:
    logger.warning("TAVILY_API_KEY not set — news_agent will return errors")

_tavily_client: TavilyClient | None = TavilyClient(api_key=_tavily_key) if _tavily_key else None


@traceable(name="tavily.search", run_type="tool")
def _tavily_search(query: str, max_results: int) -> list[dict]:
    """Internal helper: actual Tavily call. Wrapped for trace visibility."""
    if _tavily_client is None:
        raise RuntimeError("Tavily client not configured")
    response = _tavily_client.search(
        query=query,
        search_depth="advanced",
        topic="news",
        max_results=max_results,
        include_domains=ALLOWED_DOMAINS,
    )
    return response.get("results", [])


@tool
def search_financial_news(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> dict:
    """Search recent financial news from reputable sources.

    Use this tool for any news-related query — earnings, Fed announcements,
    market events, company-specific news.

    Args:
        query: Search query. Be specific (e.g., "AAPL Q4 2026 earnings",
               "Fed September 2026 rate decision"). Rephrase vague queries.
        max_results: How many articles to return. Default 5. Max recommended 10.

    Returns:
        On success: dict with keys
          - query:       the search query used
          - results:     list of {title, snippet, url, source, published_date}
          - num_results: int
          - cache_hit:   bool
        On failure: {"error": "...", "query": query}
    """
    if _tavily_client is None:
        return {
            "error": "Tavily API key not configured (TAVILY_API_KEY missing).",
            "query": query,
        }

    cache_key = f"news:{query}:{max_results}"
    if (cached := _cache_get(cache_key)) is not None:
        logger.info("news cache hit", extra={"query": query[:60]})
        return {**cached, "cache_hit": True}

    logger.info("news fetch called", extra={"query": query[:60], "max_results": max_results})
    try:
        response = _tavily_search(query, max_results)
    except Exception as e:
        logger.error(
            "Tavily search failed", extra={"error_type": type(e).__name__, "error": str(e)}
        )
        return {
            "error": f"Search service unavailable: {type(e).__name__}",
            "query": query,
        }

    raw_results = response  # already the list, returned by _tavily_search
    if not raw_results:
        return {
            "query": query,
            "results": [],
            "num_results": 0,
            "cache_hit": False,
        }

    # Normalize each result into our stable contract
    results = []
    for r in raw_results:
        url = r.get("url", "")
        results.append(
            {
                "title": r.get("title", "(no title)"),
                "snippet": r.get("content", "")[:500],  # trim long snippets
                "url": url,
                "source": _extract_domain(url),
                "published_date": r.get("published_date", "unknown"),
            }
        )

    result = {
        "query": query,
        "results": results,
        "num_results": len(results),
        "cache_hit": False,
    }
    _cache_set(cache_key, result, CACHE_TTL)
    logger.info("news fetch returned results", extra={"result_count": len(results)})
    return result


def _extract_domain(url: str) -> str:
    """Extract clean domain from a URL for display (e.g., 'reuters.com')."""
    try:
        from urllib.parse import urlparse

        netloc = urlparse(url).netloc
        # Strip "www." prefix for cleanliness
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


news_tools_list = [search_financial_news]
