"""
tests/eval/datasets.py - Golden datasets for evaluating Finnie's quality.

"""

# ROUTING DATASET
ROUTING_DATASET = [
    # -- Singel-agent cases: --
    {"inputs": {"query": "What is an ETF?"},
     "outputs": {"agents": ["qa_agent"]},
     "tags": ["single", "qa"]},
    {"inputs": {"query": "Explain compound interest like I'm 10"},
     "outputs": {"agents": ["qa_agent"]},
     "tags": ["single", "qa"]},
    {"inputs": {"query": "Roth IRA vs Traditional IRA?"},
     "outputs": {"agents": ["tax_agent"]},
     "tags": ["single", "tax"]},
    {"inputs": {"query": "What's the 2026 401(k) contribution limit?"},
     "outputs": {"agents": ["tax_agent"]},
     "tags": ["single", "tax"]},
    {"inputs": {"query": "How much to save monthly to hit $1M in 30 years at 7%?"},
     "outputs": {"agents": ["goal_agent"]},
     "tags": ["single", "goal"]},
    {"inputs": {"query": "Analyze my portfolio: $10K AAPL, $5K BND, $5K VTI"},
     "outputs": {"agents": ["portfolio_agent"]},
     "tags": ["single", "portfolio"]},
    {"inputs": {"query": "What's AAPL trading at?"},
     "outputs": {"agents": ["market_agent"]},
     "tags": ["single", "market"]},
    {"inputs": {"query": "How is the S&P 500 doing today?"},
     "outputs": {"agents": ["market_agent"]},
     "tags": ["single", "market"]},
    {"inputs": {"query": "Latest news on NVDA"},
     "outputs": {"agents": ["news_agent"]},
     "tags": ["single", "news"]},

    # -- Multi-agent: queries spanning multiple domains --
    {"inputs": {"query": "What ETFs should I hold in my 401k for retirement at 60 with $1.5M target?"},
     "outputs": {"agents": ["qa_agent", "goal_agent", "tax_agent"]},
     "tags": ["multi"]},
    {"inputs": {"query": "AAPL is up 20% — should I rebalance my $50K AAPL + $10K BND portfolio?"},
     "outputs": {"agents": ["qa_agent", "market_agent", "portfolio_agent"]},
     "tags": ["multi"]},
    {"inputs": {"query": "AAPL current price and latest earnings news?"},
     "outputs": {"agents": ["market_agent", "news_agent"]},
     "tags": ["multi"]},

    # -- Edge case: direct advice request --> must redirect to qa --
    {"inputs": {"query": "Should I sell my Tesla stock?"},
     "outputs": {"agents": ["qa_agent"]},
     "tags": ["advice_redirect"]},
    {"inputs": {"query": "Is NVDA a good buy?"},
     "outputs": {"agents": ["qa_agent"]},
     "tags": ["advice_redirect"]},

    # ── Edge case: off-topic --> must redirect ──
    {"inputs": {"query": "What's the weather in Frisco today?"},
     "outputs": {"agents": ["qa_agent"]},
     "tags": ["off_topic"]},
]