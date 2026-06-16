"""
src/mcp_server/server.py — Finnie's MCP server (single source of truth).

MCP CONCEPT:
  This server exposes Finnie's 9 educational-finance tools and 2
  reusable prompt templates via the Model Context Protocol (MCP).
  Any MCP-compatible client (Claude Desktop, custom agents, IDE
  integrations) can discover and call them without knowing they're
  backed by ChromaDB, yfinance, or Tavily under the hood.

TRANSPORT OPTIONS:
  This file defines 'mcp' (the FastMCP instance) only.
  - For stdio:           import and run via src/mcp_server/run_stdio.py
  - For SSE / HTTP:      import and run via src/mcp_server/run_http.py

TOOLS EXPOSED (9):
  RAG pattern:
    • finance_qa_search       — search the curated finance education KB
    • tax_education_search    — search the curated tax-education KB

  Math pattern (deterministic, no LLM call):
    • required_monthly_savings — solve for monthly savings to hit a target
    • project_growth           — project balance given current + monthly contributions
    • analyze_portfolio        — allocation/diversification/risk from holdings

  External-API pattern (with TTL caching + graceful fallback):
    • get_stock_quote          — current price + day change (via yfinance)
    • get_historical_prices    — historical closes (via yfinance)
    • get_index_overview       — S&P 500 / Dow / NASDAQ / VIX snapshot
    • search_financial_news    — recent news from a curated allowlist (via Tavily)

PROMPTS EXPOSED (2):
  • explain-like-im-5      — parameterized teaching template for any concept
  • regulatory-disclaimer  — canonical educational-only disclaimer footer

HOW IT INTEGRATES:
  Each @mcp.tool() is a THIN wrapper around an existing LangChain @tool
  in src/agents/*/tool.py. The wrapper calls `.invoke({...})` on the
  underlying tool, preserving observability, caching, and error handling
  that already exist. This file adds NO new business logic — it only
  re-exposes existing logic over a standardized protocol.
"""

from typing import Literal

from mcp.server.fastmcp import FastMCP

from src.agents.goal.tool import (
    project_growth as _project_growth,
)
from src.agents.goal.tool import (
    required_monthly_savings as _required_monthly_savings,
)
from src.agents.market.tool import (
    get_historical_prices as _get_historical_prices,
)
from src.agents.market.tool import (
    get_index_overview as _get_index_overview,
)
from src.agents.market.tool import (
    get_stock_quote as _get_stock_quote,
)
from src.agents.news.tool import search_financial_news as _search_financial_news
from src.agents.portfolio.tool import analyze_portfolio as _analyze_portfolio

# importing the tools
from src.agents.qa.tool import finance_qa_search as _qa_search
from src.agents.tax.tool import tax_education_search as _tax_search
from src.utils.logger import setup_logger

logger = setup_logger("finnie.mcp_server")

# FastMCP instance - singel source of truth
mcp = FastMCP(
    "finnie",
    instructions=(
        "Finnie's MCP server. Exposes 9 educational-finance tools across "
        "three architectural patterns (RAG, deterministic math, and "
        "external-API access) plus 2 parameterized prompt templates. "
        "All responses are educational ONLY and never constitute "
        "personalized financial, investment, tax, or legal advice."
    ),
)


# Exposing all our 9 Finnie's tools as mcp tools
# Tool 1/9 — RAG: finance Q&A search
@mcp.tool()
def finance_qa_search(
    query: str,
    category: Literal[
        "investing_basics",
        "portfolio_management",
        "market_analysis",
        "goal_planning",
    ]
    | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Search Finnie's curated finance education knowledge base.

    MCP NOTE: This is a RAG tool — the underlying implementation queries a
    Chroma vector store. By exposing it via MCP, any client can search the
    KB without knowing it's backed by Chroma. We could swap to Qdrant or
    Pinecone tomorrow and no client code would change.

    Args:
        query: A clear, focused finance question. Rephrase the user's
            input if needed for retrieval (e.g., "ETFs?" → "What is an ETF?").
        category: Optional. Scope retrieval to one KB category. Omit for broad search.
        top_k: How many chunks to return. Default 5.

    Returns:
        List of dicts with keys {text, source_url, source_name, category, relevance}.
        Empty list on retrieval failure.
    """
    return _qa_search.invoke(
        {
            "query": query,
            "category": category,
            "top_k": top_k,
        }
    )


# Tool 2/9 — RAG: tax education search
@mcp.tool()
def tax_education_search(query: str, top_k: int = 5) -> list[dict]:
    """Search Finnie's curated tax-education knowledge base (IRS / Bogleheads sourced).

    MCP NOTE: A separate tool from finance_qa_search even though both hit the
    same Chroma collection. Splitting them makes the LLM's tool choice
    cleaner — "tax question? use tax_education_search" — and lets us evolve
    the two tools independently later (e.g., different top_k defaults).

    Args:
        query: A clear, focused US tax question.
        top_k: How many chunks to return. Default 5.

    Returns:
        List of dicts with keys {text, source_url, source_name, category, relevance}.
    """
    return _tax_search.invoke({"query": query, "top_k": top_k})


# Tool 3/9 — Math: required monthly savings
@mcp.tool()
def required_monthly_savings(
    target_amount: float,
    years: int,
    expected_annual_return_pct: float = 7.0,
    current_savings: float = 0.0,
) -> dict:
    """Solve for the monthly contribution needed to hit a savings target.

    MCP NOTE: Pure deterministic math — no LLM call, no API call. Exposing
    it as an MCP tool means any agent (Claude Desktop, our own LangGraph
    orchestrator, a third-party app) can do "how much do I need to save?"
    calculations without re-implementing the future-value formula.

    Args:
        target_amount: Dollar amount the user wants at the end of the horizon.
        years: Time horizon in years (must be > 0).
        expected_annual_return_pct: Annual return assumption (default 7.0 = S&P avg).
        current_savings: Starting balance (default 0.0).

    Returns:
        Dict with keys including monthly_contribution, total_contributed,
        and growth attribution breakdown.
    """
    return _required_monthly_savings.invoke(
        {
            "target_amount": target_amount,
            "years": years,
            "expected_annual_return_pct": expected_annual_return_pct,
            "current_savings": current_savings,
        }
    )


# Tool 4/9 — Math: project growth
@mcp.tool()
def project_growth(
    current_savings: float,
    monthly_contribution: float,
    years: int,
    expected_annual_return_pct: float = 7.0,
) -> dict:
    """Project the future value of regular savings over time.

    MCP NOTE: The inverse of required_monthly_savings. Where that one solves
    for the contribution given a target, this one solves for the final
    balance given a contribution. Both math tools are deterministic and
    instant — they never call an LLM or external API.

    Args:
        current_savings: Starting balance.
        monthly_contribution: Amount added every month.
        years: Time horizon in years.
        expected_annual_return_pct: Annual return assumption (default 7.0).

    Returns:
        Dict with final_balance, total_contributed, total_growth, and
        milestone-year snapshots.
    """
    return _project_growth.invoke(
        {
            "current_savings": current_savings,
            "monthly_contribution": monthly_contribution,
            "years": years,
            "expected_annual_return_pct": expected_annual_return_pct,
        }
    )


# Tool 5/9 — Math: analyze portfolio
@mcp.tool()
def analyze_portfolio(holdings: list[dict]) -> dict:
    """Analyze portfolio holdings: allocation, diversification, risk profile, weighted ER.

    MCP NOTE: The one tool that takes structured input (a list of holdings).
    We use plain `list[dict]` — the LLM client reads this
    docstring to learn the expected shape. The underlying tool validates
    every dict and raises ValueError on malformed input.

    Args:
        holdings: List of holding dicts. Each MUST include:
            - ticker:      str  (e.g., "AAPL", "BND")
            - value_usd:   float (current dollar value; must be > 0)
            - asset_class: str  (one of "stocks", "bonds", "cash", "other")
          Optional per holding:
            - expense_ratio: float (e.g., 0.04 for 0.04%)
          Example:
            [
              {"ticker": "AAPL", "value_usd": 10000, "asset_class": "stocks"},
              {"ticker": "BND",  "value_usd":  3000, "asset_class": "bonds",
               "expense_ratio": 0.03},
            ]

    Returns:
        Dict with total_value, allocations, diversification_score, and
        risk_profile label.
    """
    return _analyze_portfolio.invoke({"holdings": holdings})


# Tool 6/9 — External API: stock quote
@mcp.tool()
def get_stock_quote(ticker: str) -> dict:
    """Get current price + day change + 52-week range for a single ticker.

    MCP NOTE: Backed by yfinance with a module-level TTL cache (30 min for
    quotes). Multiple MCP clients hitting this tool share the same cache —
    a single yfinance call serves many agents. That's the production
    benefit of MCP: stateful caching lives in the server, not duplicated
    in every client.

    Args:
        ticker: Stock or ETF symbol (e.g., "AAPL", "VTI"). Case-insensitive.

    Returns:
        Dict with current_price, prev_close, change, change_pct, day/52wk
        ranges, currency, and cache_hit flag. On failure: {"error": "..."}.
    """
    return _get_stock_quote.invoke({"ticker": ticker})


# Tool 7/9 — External API: historical prices
@mcp.tool()
def get_historical_prices(
    ticker: str,
    period: Literal[
        "1d",
        "5d",
        "10d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max",
    ] = "1mo",
) -> dict:
    """Get historical closing prices for a ticker over a period.

    MCP NOTE: The Literal-typed `period` parameter is the key teaching
    moment here — FastMCP introspects it and tells the client "only these
    12 strings are valid." The LLM gets that enum directly in its tool
    schema, so it can't ask for "1 month" instead of "1mo".

    Args:
        ticker: Stock or ETF symbol.
        period: One of the supported yfinance periods. Default "1mo".

    Returns:
        Dict with start_date, end_date, data_points, prices list, cache_hit.
    """
    return _get_historical_prices.invoke({"ticker": ticker, "period": period})


# Tool 8/9 — External API: index overview
@mcp.tool()
def get_index_overview() -> dict:
    """Get a snapshot of the major US market indices: S&P 500, Dow, NASDAQ, VIX.

    MCP NOTE: Takes NO arguments. This is the simplest possible MCP tool
    shape — useful for showing reviewers that not every tool needs inputs.

    Returns:
        Dict mapping each index name to a quote dict, plus cache_hit.
    """
    return _get_index_overview.invoke({})


# Tool 9/9 — External API: financial news
@mcp.tool()
def search_financial_news(query: str, max_results: int = 5) -> dict:
    """Search recent financial news from a curated reputable-source allowlist.

    MCP NOTE: Backed by Tavily with a domain allowlist (Reuters, Bloomberg,
    WSJ, etc.). The allowlist is enforced in the underlying tool, not in the
    MCP layer — that's intentional. Authorization belongs at the data source,
    not at the protocol surface, so the same allowlist applies whether the
    tool is called via MCP, directly, or through LangGraph.

    Args:
        query: Search query. Be specific for best results.
        max_results: How many articles to return. Default 5.

    Returns:
        Dict with results list (title/snippet/url/source/date) and metadata.

    """
    return _search_financial_news.invoke({"query": query, "max_results": max_results})


# Prompt 1/2 — explain-like-im-5 (parameterized teaching template)
@mcp.prompt("explain-like-im-5")
def explain_like_im_5_prompt(
    concept: str = "investing basics",
    audience: Literal["adult", "teen", "child"] = "adult",
) -> str:
    """Generate a teaching prompt that asks the LLM to explain a concept simply.

    MCP NOTE: Prompts are the THIRD MCP primitive (after tools and resources).
    Unlike a tool, a prompt is not invoked by the model — the host (Claude
    Desktop, our agent app) renders it into the chat ahead of time. Think
    of it as a "slash command" surfaced to the user.

    Args:
        concept: The finance concept to explain (e.g., "compound interest").
        audience: Reading level — "adult" / "teen" / "child". Default "adult".

    Returns:
        A teaching-style prompt string ready to drop into a chat as a user message
    """
    audience_styles = {
        "adult": "an intelligent adult who's new to finance",
        "teen": "a curious teenager",
        "child": "a 10-year-old child",
    }
    style = audience_styles.get(audience, audience_styles["adult"])
    return (
        f'Explain the financial concept of "{concept}" to {style}. '
        f"Use a concrete real-world analogy, avoid jargon, and end with one "
        f"actionable example. Keep the explanation under 200 words. "
        f"This is for educational purposes only — do not give specific "
        f"buy/sell or investment advice."
    )


# Prompt 2/2 — regulatory-disclaimer (no parameters)
@mcp.prompt("regulatory-disclaimer")
def regulatory_disclaimer_prompt() -> str:
    """Render Finnie's canonical educational disclaimer as a conversation-priming request.

    MCP NOTE: Centralizing the disclaimer in the MCP server means there's exactly
    one place to update if compliance language changes. Any host that connects
    to this server gets the latest version automatically — no hard-coded strings
    drifting across codebases.

    The returned string is framed as a USER REQUEST (not a bare statement) so
    that Claude has a clear action to take when this prompt is fired from a
    Claude Desktop / Cowork menu. Without this framing, Claude receives the
    disclaimer text with no instruction and (correctly) asks "what should I
    do with this?".

    Returns:
        A user-message string that asks Claude to acknowledge Finnie's
        regulatory disclaimer and apply it throughout the conversation.
    """
    return (
        "Please acknowledge Finnie's standard educational disclaimer for this "
        "conversation, quoted exactly below, and confirm you'll apply this "
        "principle to any financial information you provide going forward:\n\n"
        "> **Important:** Finnie is an educational tool, not a financial advisor. "
        "The information provided is for general learning purposes only and "
        "does not constitute personalized financial, investment, tax, or legal "
        "advice. Consult a licensed professional before making any financial "
        "decisions."
    )


logger.info(
    "Finnie MCP server defined.",
    extra={"tool_count": 9, "prompt_count": 2},
)
