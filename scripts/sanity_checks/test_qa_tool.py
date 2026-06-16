"""
Smoke test: calling the Q&A tool directly with a few queries
"""

print("Importing tool... (Chroma will load)")
from src.agents.qa.tool import finance_qa_search

print("Import done. Running queries...\n")

QUERIES = [
    ("What is an ETF?", None),
    ("Explain compound interest", None),
    ("What is asset allocation?", "portfolio_management"),
    ("What is the S&P 500?", "market_analysis"),
]

for query, category in QUERIES:
    print(f"\n{'=' * 60}")
    print(f"Q: {query} | category={category}")
    print("=" * 60)

    results = finance_qa_search.invoke({"query": query, "category": category, "top_k": 3})
    for i, r in enumerate(results, 1):
        print(f"\n  {i}. [{r['category']}] relevance={r['relevance']}")
        print(f"     {r['source_url']}")
        print(f"     {r['text'][:120].strip()}...")
