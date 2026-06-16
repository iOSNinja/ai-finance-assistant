"""Smoke test: search the freshly-built Chroma KB."""

from langchain_chroma import Chroma

from src.core.config import RAG_CONFIG, embeddings

store = Chroma(
    collection_name=RAG_CONFIG["collection_name"],
    embedding_function=embeddings,
    persist_directory=RAG_CONFIG["persist_dir"],
)

queries = [
    "What is an ETF?",
    "How does compound interest work?",
    "Roth IRA vs Traditional IRA",
    "What is asset allocation?",
]

for q in queries:
    print(f"\nQuery: {q}")
    results = store.similarity_search(q, k=3)
    for i, doc in enumerate(results, 1):
        title = doc.metadata.get("source_url", "?")
        cat = doc.metadata.get("category", "?")
        print(f"  {i}. [{cat}] {title}")
        print(f"     {doc.page_content[:120].strip()}...")
