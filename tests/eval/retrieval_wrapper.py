"""
test/eval/retrieveal_wrapper.py - Calls RAG tools directly, bypassingthe LLM.

"""

from typing import Any

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class FinnieRetrievalWrapper:
    """Calls QA & Tax RAG tools directly."""

    def __init__(self):
        # Imports here (not at module top) to load/init ChromaDB once as it is expensive
        from src.agents.qa.tool import finance_qa_search
        from src.agents.tax.tool import tax_education_search

        self._qa_search = finance_qa_search
        self._tax_search = tax_education_search
        logger.info("Retrieval wrapper initialized")

    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Run a retrieval query and return the retrieved chunks."""
        query = inputs["query"]
        agent = inputs["agent"]
        category = inputs["category"]

        try:
            if agent == "qa":
                # qa_search is a tool, decorated with @tool, hence we need to call viam.invoke()
                chunks = self._qa_search.invoke({
                    "query": query,
                    "category": category,
                    "top_k": 5,
                })
            elif agent == "tax":
                chunks = self._tax_search.invoke({
                    "query": query,
                    "top_k": 5,
                })
            else:
                logger.warning("Unknown agent type", extra={"agent": agent})
                return {"chunks": [], "error": f"Unknown agent: {agent}"}
            
        except Exception as e:
            logger.error("Retrieval failed",
                         extra={"error_type": type(e).__name__, "error": str(e)})
            return {"chunks": [], "error": f"{type(e).__name__}: {e}"}

        # Normalizing return shape to ease consumption by the evaluators.
        return {
            "chunks": chunks,
            "chunk_count": len(chunks),
            "agent": agent,
        }