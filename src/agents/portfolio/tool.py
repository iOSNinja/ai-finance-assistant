"""
src/agents/portfolio/tool.py — Portfolio analysis math tool.

Pure Python — no API, no RAG. Takes a list of holdings, returns
allocation/diversification/risk metrics. Deterministic and instant.

Diversification score:
    1 - HHI, where HHI = sum of (allocation_fraction^2)
    Range: 0 (single-holding concentration) → 1 (perfectly spread)

Risk profile heuristic:
    Stocks %      Profile
    > 80          Aggressive
    60-80         Moderate-Aggressive
    40-60         Moderate
    20-40         Conservative
    < 20          Very Conservative
"""

from langchain_core.tools import tool

from src.utils.logger import setup_logger

logger = setup_logger("finnie.agents.portfolio.tool")

VALID_ASSET_CLASSES = {"stocks", "bonds", "cash", "other"}


def _validate_holdings(holdings: list[dict]) -> None:
    """Raise ValueError if holdings list is malformed."""
    if not holdings:
        raise ValueError("holdings list cannot be empty")
    for i, h in enumerate(holdings):
        if not isinstance(h, dict):
            raise ValueError(f"holding[{i}] must be a dict, got {type(h).__name__}")
        for required in ("ticker", "value_usd", "asset_class"):
            if required not in h:
                raise ValueError(f"holding[{i}] missing required field '{required}'")
        if not isinstance(h["ticker"], str) or not h["ticker"].strip():
            raise ValueError(f"holding[{i}].ticker must be a non-empty string")
        if h["value_usd"] <= 0:
            raise ValueError(f"holding[{i}].value_usd must be positive (got {h['value_usd']})")
        if h["asset_class"] not in VALID_ASSET_CLASSES:
            raise ValueError(
                f"holding[{i}].asset_class must be one of {VALID_ASSET_CLASSES} "
                f"(got {h['asset_class']!r})"
            )


def _risk_profile(stock_pct: float) -> str:
    """Map stocks % to a risk-profile label."""
    if stock_pct > 80:
        return "Aggressive"
    if stock_pct > 60:
        return "Moderate-Aggressive"
    if stock_pct > 40:
        return "Moderate"
    if stock_pct > 20:
        return "Conservative"
    return "Very Conservative"


@tool
def analyze_portfolio(holdings: list[dict]) -> dict:
    """Analyze a user's portfolio holdings and return structured metrics.

    Use this tool to compute total value, allocation, diversification,
    risk profile, and weighted expense ratio (if available) from a list
    of holdings.

    Args:
        holdings: List of holding dicts. Each MUST include:
            - ticker:      str  (e.g., "AAPL", "BND")
            - value_usd:   float (current dollar value; must be > 0)
            - asset_class: str  (one of: "stocks", "bonds", "cash", "other")
          Optional per holding:
            - expense_ratio: float (e.g., 0.04 for 0.04%)
          Example:
            [
              {"ticker": "AAPL", "value_usd": 10000, "asset_class": "stocks"},
              {"ticker": "VTI",  "value_usd":  5000, "asset_class": "stocks",
               "expense_ratio": 0.03},
              {"ticker": "BND",  "value_usd":  3000, "asset_class": "bonds",
               "expense_ratio": 0.03},
            ]

    Returns:
        A dict with:
          - total_value:              float — sum of all positions
          - num_holdings:             int
          - allocation_by_asset_class: dict[str, float] — percentages summing to 100
          - allocation_by_ticker:     dict[str, float] — percentages summing to 100
          - largest_position_pct:     float — concentration risk indicator
          - diversification_score:    float — in [0, 1]; higher = more diversified
          - risk_profile:             str  — descriptive label
          - weighted_expense_ratio:   float | None — only if ALL holdings provided one
    """
    logger.info("analyze_portfolio called", extra={"holdings_count": len(holdings)})
    _validate_holdings(holdings)

    total_value = sum(h["value_usd"] for h in holdings)

    # Allocation by asset class
    by_class: dict[str, float] = {}
    for h in holdings:
        by_class[h["asset_class"]] = by_class.get(h["asset_class"], 0.0) + h["value_usd"]
    allocation_by_asset_class = {k: round(v / total_value * 100, 2) for k, v in by_class.items()}

    # Allocation by ticker
    by_ticker: dict[str, float] = {}
    for h in holdings:
        # If a ticker appears twice, aggregate
        by_ticker[h["ticker"]] = by_ticker.get(h["ticker"], 0.0) + h["value_usd"]
    allocation_by_ticker = {k: round(v / total_value * 100, 2) for k, v in by_ticker.items()}

    # Concentration + diversification (HHI-based)
    largest = max(allocation_by_ticker.values())
    hhi = sum((pct / 100) ** 2 for pct in allocation_by_ticker.values())
    diversification = round(1 - hhi, 4)

    # Risk profile from equity exposure
    stock_pct = allocation_by_asset_class.get("stocks", 0.0)
    risk = _risk_profile(stock_pct)

    # Weighted expense ratio — only if EVERY holding provides one
    if all("expense_ratio" in h for h in holdings):
        weighted_er = sum(h["value_usd"] * h["expense_ratio"] for h in holdings) / total_value
        weighted_expense_ratio: float | None = round(weighted_er, 4)
    else:
        weighted_expense_ratio = None

    result = {
        "total_value": round(total_value, 2),
        "num_holdings": len(holdings),
        "allocation_by_asset_class": allocation_by_asset_class,
        "allocation_by_ticker": allocation_by_ticker,
        "largest_position_pct": round(largest, 2),
        "diversification_score": diversification,
        "risk_profile": risk,
        "weighted_expense_ratio": weighted_expense_ratio,
    }
    logger.info(
        "analyze_portfolio result",
        extra={
            "total_value": result["total_value"],
            "diversification_score": result["diversification_score"],
            "risk_profile": result["risk_profile"],
        },
    )
    return result


portfolio_tools_list = [analyze_portfolio]
