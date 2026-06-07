"""
src/mcp_server/server.py — Finnie's MCP server (single source of truth).
"""

from typing import Literal

from mcp.server.fastmcp import FastMCP

from src.utils.logger import setup_logger

# importing the tools
from src.agents.qa.tool import finance_qa_search as _qa_search
from src.agents.tax.tool import tax_education_search as _tax_search
from src.agents.goal.tool import (
    required_monthly_savings as _required_monthly_savings,
    project_growth as _project_growth,
)
from src.agents.portfolio.tool import analyze_portfolio as _analyze_portfolio
from src.agents.market.tool import (
    get_stock_quote as _get_stock_quote,
    get_historical_prices as _get_historical_prices,
    get_index_overview as _get_index_overview,
)
from src.agents.news.tool import search_financial_news as _search_financial_news

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
        "investing_basics", "portfolio_management",
        "market_analysis", "goal_planning",
    ] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Search Finnie's curated finance education knowledge base.
    """
    return _qa_search.invoke({
        "query": query,
        "category": category,
        "top_k": top_k,
    })


# Tool 2/9 — RAG: tax education search
@mcp.tool()
def tax_education_search(query: str, top_k: int = 5) -> list[dict]:
    """Search Finnie's curated tax-education knowledge base (IRS / Bogleheads sourced).
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
    """
    return _required_monthly_savings.invoke({
        "target_amount": target_amount,
        "years": years,
        "expected_annual_return_pct": expected_annual_return_pct,
        "current_savings": current_savings,
    })


# Tool 4/9 — Math: project growth
@mcp.tool()
def project_growth(
    current_savings: float,
    monthly_contribution: float,
    years: int,
    expected_annual_return_pct: float = 7.0,
) -> dict:
    """Project the future value of regular savings over time.
    """
    return _project_growth.invoke({
        "current_savings": current_savings,
        "monthly_contribution": monthly_contribution,
        "years": years,
        "expected_annual_return_pct": expected_annual_return_pct,
    })


# Tool 5/9 — Math: analyze portfolio
@mcp.tool()
def analyze_portfolio(holdings: list[dict]) -> dict:
    """Analyze portfolio holdings: allocation, diversification, risk profile, weighted ER.
    """
    return _analyze_portfolio.invoke({"holdings": holdings})


# Tool 6/9 — External API: stock quote
@mcp.tool()
def get_stock_quote(ticker: str) -> dict:
    """Get current price + day change + 52-week range for a single ticker.
    """
    return _get_stock_quote.invoke({"ticker": ticker})


# Tool 7/9 — External API: historical prices
@mcp.tool()
def get_historical_prices(
    ticker: str,
    period: Literal[
        "1d", "5d", "10d", "1mo", "3mo", "6mo",
        "1y", "2y", "5y", "10y", "ytd", "max",
    ] = "1mo",
) -> dict:
    """Get historical closing prices for a ticker over a period.
    """
    return _get_historical_prices.invoke({"ticker": ticker, "period": period})


# Tool 8/9 — External API: index overview
@mcp.tool()
def get_index_overview() -> dict:
    """Get a snapshot of the major US market indices: S&P 500, Dow, NASDAQ, VIX.
    """
    return _get_index_overview.invoke({})


# Tool 9/9 — External API: financial news
@mcp.tool()
def search_financial_news(query: str, max_results: int = 5) -> dict:
    """Search recent financial news from a curated reputable-source allowlist.
    """
    return _search_financial_news.invoke({"query": query, "max_results": max_results})


# Prompt 1/2 — explain-like-im-5 (parameterized teaching template)
@mcp.prompt("explain-like-im-5")
def explain_like_im_5_prompt(
    concept: str,
    audience: Literal["adult", "teen", "child"] = "adult",
) -> str:
    """Generate a teaching prompt that asks the LLM to explain a concept simply.
    """
    audience_styles = {
        "adult": "an intelligent adult who's new to finance",
        "teen": "a curious teenager",
        "child": "a 10-year-old child",
    }
    style = audience_styles.get(audience, audience_styles["adult"])
    return (
        f"Explain the financial concept of \"{concept}\" to {style}. "
        f"Use a concrete real-world analogy, avoid jargon, and end with one "
        f"actionable example. Keep the explanation under 200 words. "
        f"This is for educational purposes only — do not give specific "
        f"buy/sell or investment advice."
    )


# Prompt 2/2 — regulatory-disclaimer (no parameters)
@mcp.prompt("regulatory-disclaimer")
def regulatory_disclaimer_prompt() -> str:
    """Return Finnie's educational-only disclaimer footer.
    """
    return (
        "**Important:** Finnie is an educational tool, not a financial advisor. "
        "The information provided is for general learning purposes only and "
        "does not constitute personalized financial, investment, tax, or legal "
        "advice. Consult a licensed professional before making any financial "
        "decisions."
    )

logger.info(
    "Finnie MCP server defined.",
    extra={"tool_count": 9, "prompt_count": 2},
)