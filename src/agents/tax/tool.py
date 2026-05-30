"""
src/agents/tax/tool.py — Tax knowledge-base search tool for the Tax Education agent.

Same Chroma store as the Q&A agent, filtered to category='tax_education'.
"""

from src.utils.logger import setup_logger
from src.core.config import RAG_CONFIG, embeddings

from langchain_chroma import Chroma
from langchain_community.tools import tool

logger = setup_logger("finnie.agents.tax.tool")

# We will reuse the same Chroma store as the Q&A tool - one KB with many filtered views
_store = Chroma(
    collection_name=RAG_CONFIG.get("collection_name", "finnie_kb"),
    embedding_function=embeddings,
    persist_directory=RAG_CONFIG.get("persist_dir", ".\chroma_db")
)

@tool
def tax_education_search(
    query: str,
    top_k: int = 5
) -> list[dict]:
    """Search Finnie's tax-education knowledge base.

        Use this tool BEFORE answering ANY tax question. Ground your answer
        in the chunks it returns, and cite the source_urls.

        Args:
            query: A clear, focused tax question. Rephrase user input if needed
                for better retrieval (e.g., "401k limits?" → "What are the
                401(k) contribution limits?").
            top_k: Number of chunks to return. Default 5.

        Returns:
            A list of dicts, each with:
            - text:        the chunk's content
            - source_url:  where the chunk came from (cite this)
            - source_name: short source identifier (e.g., "irs_tax_education")
            - category:    always "tax_education" for this tool
            - relevance:   similarity score 0.0 to 1.0; higher is more relevant
            Returns [] on failure or no matches.
    """
        
    logger.info("Tax KB search: q=%r k=%d", query, top_k)

    try:
        results = _store.similarity_search_with_relevance_scores(
            query=query,
            k=top_k,
            filter={"category": "tax_education"},
        )
    except Exception as e:
        logger.error("Tax KB search failed: %s: %s", type(e).__name__, e)
        return []
    
    if not results:
        logger.warning("Tax KB search returned no results for query: %r", query[:80])
        return []
    
    # return as a list of custom dicts
    ouput: list[dict] = []
    for doc, score in results:
        ouput.append({
            "text": doc.page_content,
            "source_url": doc.metadata.get("source_url", ""),
            "source_name": doc.metadata.get("source_name", ""),
            "category": doc.metadata.get("source_url", "tax_education"),
            "relevance": round(float(score), 4),
        })
    
    logger.info("Tax KB search: returned %d chunks", len(ouput))

    return ouput

# Convenient list for binding to the LLM / building ToolNodes
tax_tools_list = [tax_education_search]