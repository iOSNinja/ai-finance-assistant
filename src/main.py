"""
src/main.py - Finnie, an AI Finance Assistant entry point.

Run from terminal:
    uv run FinnieAIFinanceAssistant       # text-only interactive loop
"""

from src.workflow.graph import build_graph
from src.utils.logger import setup_logger

logger = setup_logger("finnie.main")

class FinnieAIFinanceAssistant:
    """Application entry point"""

    def __init__(self):
        self.graph = build_graph()
