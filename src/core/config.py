"""
config.py — Centralized configs for YAML, LLM, embeddings, and OpenAI client setup for Finnie.
env var > yaml > hardcoded default(fall back)
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()

# Load yaml config (lives at repo root, two levels up from src/core/)
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"
with CONFIG_PATH.open() as f:
    _config = yaml.safe_load(f)

# env var > yaml > error
def _get(name: str, yaml_path: tuple[str, ...], default=None) -> str:
    if val := os.getenv(name):
        return val
    node = _config
    for key in yaml_path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in your .env file or environment.")

# Settings
MODEL = _get("OPENAI_MODEL", ("llm", "model"))
JUDEG_MODEL = _get("OPENAI_JUDGE_MODEL", ("llm", "judge_model"), default="gpt-4o")
EMBEDDING_MODEL = _get("OPENAI_EMBEDDING_MODEL", ("llm", "embedding_model"))
RAG_CONFIG = _config.get("rag", {})
MARKET_CONFIG = _config.get("market", {})
NEWS_CONFIG = _config.get("news", {})
LANGSMITH_CONFIG = _config.get("langsmith", {})

# If the user has set the tracing env var, ensure project name is also set.
# Defaults to the value from config.yaml.
if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_CONFIG.get(
            "project", "finnie-ai-finance-assistant"
        )

# Initializations
openai_client = OpenAI(api_key=OPENAI_API_KEY)
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

#  Cost Tracking - install one callback on the production LLM
from src.observability.cost_callback import CostTrackingCallback

# Create the module-level _cost_callback singleton
_cost_callback = CostTrackingCallback()

llm = ChatOpenAI(
    model=MODEL, 
    temperature=0.2,
    callbacks=[_cost_callback],
)
judge_llm = ChatOpenAI(model=JUDEG_MODEL, temperature=0) # no tracking — eval-only

