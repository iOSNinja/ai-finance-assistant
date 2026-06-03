"""
src/agents/goal/tool.py — Financial-projection math tools for the Goal Planning agent.

Pure Python — no LLM, no API, no I/O. Deterministic and instant.
The LLM parses natural-language goals, picks the right tool, and explains
the structured result.

Formulas:
  Future value with periodic contributions (monthly compounding):
      FV = PV * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]
  Where:
      PV  = present value (current savings)
      PMT = monthly contribution
      r   = monthly interest rate (annual_pct / 100 / 12)
      n   = number of months (years * 12)

  Solve for PMT to get required monthly savings:
      PMT = (FV - PV * (1 + r)^n) * r / ((1 + r)^n - 1)
"""

from langchain_core.tools import tool

from src.utils.logger import setup_logger

logger = setup_logger("finnie.agents.goals.tool")

MONTHS_PER_YEAR = 12


def _validate_positive(name: str, value: float) -> None:
    """Raise ValueError if a numeric input that must be positive isn't."""
    if value <= 0:
        raise ValueError(f"{name} must be positive (got {value})")


def _monthly_rate(annual_pct: float) -> float:
    """Convert annual percentage return to monthly decimal rate."""
    return (annual_pct / 100.0) / MONTHS_PER_YEAR


@tool
def required_monthly_savings(
    target_amount: float,
    years: int,
    expected_annual_return_pct: float = 7.0,
    current_savings: float = 0.0,
) -> dict:
    """Solve for the monthly contribution needed to hit a savings target.

    Use this when the user knows their target and time horizon and wants to
    know "how much do I need to save each month?"

    Args:
        target_amount: The dollar amount the user wants at the end of the horizon.
        years: Time horizon in years (1-60). Must be > 0.
        expected_annual_return_pct: Annual return assumption as a percentage
            (e.g., 7 for 7%). Default 7.0 (historical S&P 500 average).
        current_savings: Money the user already has saved. Default 0.0.

    Returns:
        A dict with:
          - monthly_contribution:        float — the headline number
          - target_amount:               float — echoed input
          - years:                       int   — echoed input
          - expected_annual_return_pct:  float — echoed input
          - current_savings:             float — echoed input
          - total_contributed:           float — sum of all monthly contributions
          - growth_from_current_savings: float — earnings on existing savings
          - growth_from_contributions:   float — earnings on monthly contributions
        If the target is already reachable from current_savings alone,
        monthly_contribution is 0.0 and a "note" key explains.
    """
    logger.info(
        "required_monthly_savings called",
        extra={"target_amount": target_amount, "years": years, "expected_annual_return_pct": expected_annual_return_pct, "current_savings": current_savings}
    )

    _validate_positive("target_amount", target_amount)
    _validate_positive("years", years)
    if expected_annual_return_pct < 0:
        raise ValueError("expected_annual_return_pct cannot be negative")
    if current_savings < 0:
        raise ValueError("current_savings cannot be negative")

    n = years * MONTHS_PER_YEAR
    r = _monthly_rate(expected_annual_return_pct)

    # Future value of existing savings, compounded at monthly rate
    fv_of_current = current_savings * (1 + r) ** n if r > 0 else current_savings

    # If the target is already covered by current savings alone
    if fv_of_current >= target_amount:
        return {
            "monthly_contribution":       0.0,
            "target_amount":              target_amount,
            "years":                      years,
            "expected_annual_return_pct": expected_annual_return_pct,
            "current_savings":            current_savings,
            "total_contributed":          0.0,
            "growth_from_current_savings": round(fv_of_current - current_savings, 2),
            "growth_from_contributions":  0.0,
            "note": (
                "Your current savings alone, compounded at the assumed rate, "
                "already exceed your target. No monthly contribution required."
            ),
        }

    # Solve PMT = (FV - PV*(1+r)^n) * r / ((1+r)^n - 1)
    remaining_needed = target_amount - fv_of_current
    if r > 0:
        monthly = remaining_needed * r / ((1 + r) ** n - 1)
    else:
        # Zero return -> just divide the shortfall evenly across months
        monthly = remaining_needed / n

    total_contributed = monthly * n
    growth_from_contrib = remaining_needed - total_contributed

    result = {
        "monthly_contribution":        round(monthly, 2),
        "target_amount":               target_amount,
        "years":                       years,
        "expected_annual_return_pct":  expected_annual_return_pct,
        "current_savings":             current_savings,
        "total_contributed":           round(total_contributed, 2),
        "growth_from_current_savings": round(fv_of_current - current_savings, 2),
        "growth_from_contributions":   round(growth_from_contrib, 2),
    }
    logger.info("required_monthly_savings result", extra={"monthly_contribution": result["monthly_contribution"]})
    return result


@tool
def project_growth(
    current_savings: float,
    monthly_contribution: float,
    years: int,
    expected_annual_return_pct: float = 7.0,
) -> dict:
    """Project the future value of regular savings over time.

    Use this when the user knows what they can save and wants to know
    "what will I have at the end?"

    Args:
        current_savings: Starting balance.
        monthly_contribution: Amount added every month.
        years: Time horizon in years (1-60). Must be > 0.
        expected_annual_return_pct: Annual return assumption as a percentage.
            Default 7.0 (historical S&P 500 average).

    Returns:
        A dict with:
          - final_balance:        float — value at end of horizon (headline number)
          - total_contributed:    float — sum of all contributions
          - total_growth:         float — final_balance minus money put in
          - yearly_balances:      list of {year, balance, contributed_to_date}
                                  for years 1, 5, 10, 20, 30 (or all if ≤ 5 years)
          - params:               dict — echoed inputs
    """
    logger.info(
        "project_growth called",
        extra={"current_savings": current_savings, "monthly_contribution": monthly_contribution, "years": years, "expected_annual_return_pct": expected_annual_return_pct}
    )

    if current_savings < 0:
        raise ValueError("current_savings cannot be negative")
    if monthly_contribution < 0:
        raise ValueError("monthly_contribution cannot be negative")
    _validate_positive("years", years)
    if expected_annual_return_pct < 0:
        raise ValueError("expected_annual_return_pct cannot be negative")

    n = years * MONTHS_PER_YEAR
    r = _monthly_rate(expected_annual_return_pct)

    # Iteratively compound month-by-month, capturing year-end snapshots
    balance = float(current_savings)
    yearly_snapshots: list[dict] = []
    for month in range(1, n + 1):
        balance = balance * (1 + r) + monthly_contribution
        if month % MONTHS_PER_YEAR == 0:
            year = month // MONTHS_PER_YEAR
            yearly_snapshots.append({
                "year":                year,
                "balance":             round(balance, 2),
                "contributed_to_date": round(monthly_contribution * month, 2),
            })

    # Pick milestone years to surface (don't drown the LLM with 60 rows)
    milestones = [1, 5, 10, 20, 30]
    picked = [s for s in yearly_snapshots if s["year"] in milestones]
    if not picked or years <= 5:
        picked = yearly_snapshots  # surface all if horizon is short

    total_contributed = current_savings + monthly_contribution * n
    final_balance = round(balance, 2)

    result = {
        "final_balance":     final_balance,
        "total_contributed": round(total_contributed, 2),
        "total_growth":      round(final_balance - total_contributed, 2),
        "yearly_balances":   picked,
        "params": {
            "current_savings":            current_savings,
            "monthly_contribution":       monthly_contribution,
            "years":                      years,
            "expected_annual_return_pct": expected_annual_return_pct,
        },
    }
    logger.info("project_growth result", extra={"final_balance": result["final_balance"]})
    return result


goal_tools_list = [required_monthly_savings, project_growth]