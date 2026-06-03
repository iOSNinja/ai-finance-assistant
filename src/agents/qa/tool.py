"""
src/agents/qa/tool.py — Knowledge-base search tool for the Q&A agent.

Exposes ONE tool, `finance_qa_search`, that the Q&A agent calls via
tool-binding. Returns retrieved chunks with metadata for citation.
The tool is the agent's only interface to the knowledge base —
the agent never talks to Chroma directly.
"""

from typing import Literal

from langchain_chroma import Chroma
from langchain_community.tools import tool

from src.core.config import RAG_CONFIG, embeddings
from src.utils.logger import setup_logger

logger = setup_logger("finnie.agents.qa.tool")

# Singleton vector store: will be loaded once at import time, reuse for process lifetime
_store = Chroma(
    collection_name=RAG_CONFIG.get("collection_name", "finnie_kb"),
    embedding_function=embeddings,
    persist_directory=RAG_CONFIG.get("persist_dir", "./chroma_db"),
)

# the tool
@tool
def finance_qa_search(
    query: str,
    category: Literal[
        "investing_basics",
        "portfolio_management",
        "market_analysis",
        "goal_planning",
    ] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Search Finnie's knowledge base for chunks relevant to a finance question.

    Use this tool BEFORE answering any educational finance question. Ground
    your answer in the chunks it returns, and cite the source_urls.

    Args:
        query: A clear, focused question. Rephrase the user's input if needed
               for better retrieval (e.g., "ETFs?" → "What is an ETF?").
        category: Optional. Filter to a specific KB category. Use it when the
                  question is clearly scoped to one topic. Leave as None when
                  unsure — searching across all categories is the safer default.
        top_k: How many chunks to return. Default 5. Smaller is cheaper;
               larger gives the agent more context.

    Returns:
        A list of dicts, each with:
          - text:        the chunk's content
          - source_url:  where the chunk came from (cite this in answers)
          - source_name: short source identifier
          - category:    which KB category the chunk belongs to
          - relevance:   similarity score in [0.0, 1.0]; higher is more relevant
        Returns [] if retrieval fails or no chunks match.
    """
    logger.info("KB search called", extra={"query": query[:80], "category": category, "top_k": top_k})

    # apply category filter for Chroma metadata if available
    where = {"category": category} if category else None

    try:
        results = _store.similarity_search_with_relevance_scores(
            query=query,
            k=top_k,
            filter=where,
        )
    except Exception as e:
        logger.error("KB search failed", extra={"error_type": type(e).__name__, "error": str(e)})
        return []
    
    if not results:
        logger.warning("KB search returned no results", extra={"query": query[:80]})
        return []
    
    # return as a list of custom dicts
    output: list[dict] = []
    for doc, score in results:
        output.append({
            "text": doc.page_content,
            "source_url": doc.metadata.get("source_url", ""),
            "source_name": doc.metadata.get("source_name", ""),
            "category": doc.metadata.get("category", ""),
            "relevance": round(float(score), 4),
        })

    logger.info("KB search returned results", extra={"chunk_count": len(output)})
    return output

# Convenient list for binding to the LLM / building ToolNodes
qa_tools_list = [finance_qa_search]