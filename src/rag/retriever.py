"""
src/rag/retriever.py — Generic, agent-agnostic KB search.

Used by the Streamlit UI's Knowledge tab and any future "browse the KB"
needs that aren't tied to a specific agent's scope.

Why this exists: the per-agent tools (finance_qa_search, tax_education_search)
constrain category via Literal types. Those constraints exist to prevent
LLMs from misusing the tools, but they get in the way when you want a
generic UI-level search across ALL categories.
"""

from langchain_chroma import Chroma

from src.core.config import RAG_CONFIG, embeddings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_store = Chroma(
    collection_name=RAG_CONFIG.get("collection_name", "finnie_kb"),
    embedding_function=embeddings,
    persist_directory=RAG_CONFIG.get("persist_dir", "./chroma_db"),
)


def kb_search(query: str, category: str | None = None, top_k: int = 5) -> list[dict]:
    """Search the entire Finnie KB. No Literal constraint on category.

    Args:
        query: The search query (semantic).
        category: Optional category filter — any string. None means search all.
        top_k: How many chunks to return.

    Returns:
        A list of dicts with keys: text, source_url, source_name, category, relevance.
        Returns [] on failure or no matches.
    """
    logger.info("kb_search: q=%r category=%s k=%d", query[:80], category, top_k)

    where = {"category": category} if category else None

    try:
        results = _store.similarity_search_with_relevance_scores(
            query=query, k=top_k, filter=where,
        )
    except Exception as e:
        logger.error("kb_search failed: %s: %s", type(e).__name__, e)
        return []

    return [
        {
            "text":        doc.page_content,
            "source_url":  doc.metadata.get("source_url", ""),
            "source_name": doc.metadata.get("source_name", ""),
            "category":    doc.metadata.get("category", ""),
            "relevance":   round(float(score), 4),
        }
        for doc, score in results
    ]