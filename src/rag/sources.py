"""
sources.py - defines where Finnie should get it's knowledge from.
"""

from typing import Literal, NotRequired, TypedDict


class SourceConfig(TypedDict):
    name: str
    category: Literal[
        "investing_basics",
        "portfolio_management",
        "market_analysis",
        "goal_planning",
        "tax_education",
    ]
    discovery: Literal["sitemap", "explicit"]
    urls: NotRequired[list[str]]  # NotRequired -> makes it optional
    sitemap_url: NotRequired[str]
    limit: NotRequired[int]


SOURCES: list[SourceConfig] = [
    # ─────────── investing_basics ───────────
    {
        "name": "sec_investor_basics",
        "category": "investing_basics",
        "discovery": "explicit",
        "urls": [
            "https://www.investor.gov/introduction-investing",
            "https://www.investor.gov/introduction-investing/investing-basics/investment-products",
            "https://www.investor.gov/introduction-investing/investing-basics/role-sec",
            "https://www.investor.gov/introduction-investing/investing-basics/glossary",
            "https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-2",
            "https://www.investor.gov/introduction-investing/investing-basics/investment-products/annuities",
            "https://www.investor.gov/introduction-investing/investing-basics/investment-products/certificates-deposit-cds",
            "https://www.investor.gov/introduction-investing/investing-basics/investment-products/private-investment-funds/hedge-funds",
            "https://www.investor.gov/introduction-investing/investing-basics/investment-products/real-estate-investment-trusts-reits",
            "https://www.investor.gov/protect-your-investments/fraud/how-avoid-fraud",
        ],
    },
    {
        "name": "wikipedia_investing_basics",
        "category": "investing_basics",
        "discovery": "explicit",
        "urls": [
            "https://en.wikipedia.org/wiki/Stock",
            "https://en.wikipedia.org/wiki/Bond_(finance)",
            "https://en.wikipedia.org/wiki/Exchange-traded_fund",
            "https://en.wikipedia.org/wiki/Mutual_fund",
            "https://en.wikipedia.org/wiki/Index_fund",
            "https://en.wikipedia.org/wiki/Compound_interest",
            "https://en.wikipedia.org/wiki/Dollar_cost_averaging",
            "https://en.wikipedia.org/wiki/Dividend",
            "https://en.wikipedia.org/wiki/Stock_market",
        ],
    },
    {
        "name": "zerodha_varsity",
        "category": "investing_basics",
        "discovery": "sitemap",
        "sitemap_url": "https://zerodha.com/varsity/chapter-sitemap2.xml",
        "limit": 15,  # Zerodha has more than 50+ urls in it's sitemap
    },
    # ─────────── portfolio_management ───────────
    {
        "name": "wikipedia_portfolio",
        "category": "portfolio_management",
        "discovery": "explicit",
        "urls": [
            "https://en.wikipedia.org/wiki/Portfolio_(finance)",
            "https://en.wikipedia.org/wiki/Asset_allocation",
            "https://en.wikipedia.org/wiki/Diversification_(finance)",
            "https://en.wikipedia.org/wiki/Modern_portfolio_theory",
            "https://en.wikipedia.org/wiki/Rebalancing_investments",
            "https://en.wikipedia.org/wiki/Sharpe_ratio",
        ],
    },
    {
        "name": "sec_portfolio",
        "category": "portfolio_management",
        "discovery": "explicit",
        "urls": [
            "https://www.investor.gov/introduction-investing/getting-started/asset-allocation",
            "https://www.investor.gov/introduction-investing/getting-started/investing-your-own",
            "https://www.investor.gov/introduction-investing/getting-started/working-investment-professional",
            "https://www.investor.gov/introduction-investing/getting-started/researching-investments",
        ],
    },
    {
        "name": "bogleheads_portfolio",
        "category": "portfolio_management",
        "discovery": "explicit",
        "urls": [
            "https://www.bogleheads.org/wiki/Three-fund_portfolio",
            "https://www.bogleheads.org/wiki/Asset_allocation",
            "https://www.bogleheads.org/wiki/Bogleheads%C2%AE_investment_philosophy",
        ],
    },
    # ─────────── market_analysis ───────────
    {
        "name": "wikipedia_market_analysis",
        "category": "market_analysis",
        "discovery": "explicit",
        "urls": [
            "https://en.wikipedia.org/wiki/S%26P_500",
            "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
            "https://en.wikipedia.org/wiki/NASDAQ_Composite",
            "https://en.wikipedia.org/wiki/VIX",
            "https://en.wikipedia.org/wiki/Volatility_(finance)",
            "https://en.wikipedia.org/wiki/Bull_market",
            "https://en.wikipedia.org/wiki/Market_trend",
            "https://en.wikipedia.org/wiki/Market_capitalization",
            "https://en.wikipedia.org/wiki/Price%E2%80%93earnings_ratio",
            "https://en.wikipedia.org/wiki/Earnings_per_share",
            "https://en.wikipedia.org/wiki/Efficient-market_hypothesis",
        ],
    },
    # ─────────── goal_planning ───────────
    {
        "name": "wikipedia_goal_planning",
        "category": "goal_planning",
        "discovery": "explicit",
        "urls": [
            "https://en.wikipedia.org/wiki/Retirement_planning",
            "https://en.wikipedia.org/wiki/Retirement",
            "https://en.wikipedia.org/wiki/Time_value_of_money",
            "https://en.wikipedia.org/wiki/Future_value",
            "https://en.wikipedia.org/wiki/Present_value",
            "https://en.wikipedia.org/wiki/Annuity",
            "https://en.wikipedia.org/wiki/Personal_finance",
            "https://en.wikipedia.org/wiki/Trinity_study",
        ],
    },
    {
        "name": "sec_goal_planning",
        "category": "goal_planning",
        "discovery": "explicit",
        "urls": [
            "https://www.investor.gov/introduction-investing/investing-basics/invest-your-goals",
            "https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/define-your-goals",
        ],
    },
    {
        "name": "bogleheads_goal_planning",
        "category": "goal_planning",
        "discovery": "explicit",
        "urls": [
            "https://www.bogleheads.org/wiki/Bogleheads%C2%AE_retirement_planning_start-up_kit",
            "https://www.bogleheads.org/wiki/Investment_planning",
            "https://www.bogleheads.org/wiki/Emergency_fund",
        ],
    },
    # ─────────── tax_education ───────────
    {
        "name": "irs_tax_education",
        "category": "tax_education",
        "discovery": "explicit",
        "urls": [
            "https://www.irs.gov/retirement-plans/individual-retirement-arrangements-iras",
            "https://www.irs.gov/retirement-plans/roth-iras",
            "https://www.irs.gov/retirement-plans/traditional-and-roth-iras",
            "https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-topics-ira-contribution-limits",
            "https://www.irs.gov/retirement-plans/401k-plans",
            "https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-topics-401k-and-profit-sharing-plan-contribution-limits",
            "https://www.irs.gov/taxtopics/tc409",
            "https://www.irs.gov/taxtopics/tc451",
        ],
    },
    {
        "name": "wikipedia_tax_education",
        "category": "tax_education",
        "discovery": "explicit",
        "urls": [
            "https://en.wikipedia.org/wiki/Capital_gains_tax",
            "https://en.wikipedia.org/wiki/Roth_IRA",
            "https://en.wikipedia.org/wiki/Traditional_IRA",
            "https://en.wikipedia.org/wiki/401(k)",
            "https://en.wikipedia.org/wiki/529_plan",
            "https://en.wikipedia.org/wiki/Health_savings_account",
        ],
    },
]
