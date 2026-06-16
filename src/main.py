"""
src/main.py — Finnie AI Finance Assistant CLI entry point.

Run from terminal:
    uv run python -m src.main
"""

from dotenv import load_dotenv

load_dotenv()

import uuid

from src.utils.logger import setup_logger
from src.workflow.graph import build_graph

logger = setup_logger(__name__)


class FinnieAIFinanceAssistant:
    """Interactive CLI for the Finnie multi-agent system."""

    BANNER = (
        "\nFinnie — AI Finance Assistant\n"
        "Educational financial guidance grounded in a curated knowledge base.\n"
        "Type 'reset' to start a new conversation. Type 'quit' or 'exit' to leave.\n"
    )

    def __init__(self) -> None:
        logger.info("Building graph...")
        self.graph = build_graph()

        # Each session gets a unique thread_id so the checkpointer can scope memory
        self.thread_id = str(uuid.uuid4())
        logger.info("Session ready", extra={"thread_id": self.thread_id[:8]})

    def _new_session(self) -> None:
        """Start a fresh conversation thread (clears memory)."""
        self.thread_id = str(uuid.uuid4())
        logger.info("New session", extra={"thread_id": self.thread_id[:8]})

    def ask(self, query: str, surface: str = "cli") -> str:
        """Run one query end-to-end through the graph and return the final answer."""

        config = {
            "configurable": {"thread_id": self.thread_id},
            "tags": ["env:dev", f"surface:{surface}", "version:v1"],
            "metadata": {
                "thread_id": self.thread_id[:8],
                "user_query_length": len(query),
            },
            "run_name": f"finnie.query: {query[:60]}",  # sets the title of the top-level trace in the dashboard. Without it, traces all look like LangGraph.
        }
        # Reset per-turn buffers so previous-turn state doesn't leak in
        initial_state = {
            "user_query": query,
            "route": [],
            "is_finance_query": True,
            # Reset ALL per-agent buffers + responses each turn
            "qa_messages": [],
            "tax_messages": [],
            "goal_messages": [],
            "portfolio_messages": [],
            "market_messages": [],
            "news_messages": [],
            "qa_response": "",
            "tax_response": "",
            "goal_response": "",
            "portfolio_response": "",
            "market_response": "",
            "news_response": "",
            "final_answer": "",
        }
        try:
            final = self.graph.invoke(initial_state, config=config)
        except Exception as e:
            logger.error(
                "Graph invocation failed", extra={"error_type": type(e).__name__, "error": str(e)}
            )
            return "Sorry, something went wrong while processing your question. Please try again."
        return final.get("final_answer", "(no answer produced)")

    def run_interactive(self) -> None:
        """Read-eval-print loop."""
        print(self.BANNER)
        while True:
            try:
                query = input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                return

            if not query:
                continue
            if query.lower() in {"quit", "exit"}:
                print("Goodbye.")
                return
            if query.lower() == "reset":
                self._new_session()
                print("(memory cleared)")
                continue

            answer = self.ask(query)
            print(f"\nFinnie: {answer}\n")


def main() -> None:
    """Module entry point for `uv run python -m src.main`."""
    app = FinnieAIFinanceAssistant()
    app.run_interactive()


if __name__ == "__main__":
    main()
