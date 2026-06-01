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
EMBEDDING_MODEL = _get("OPENAI_EMBEDDING_MODEL", ("llm", "embedding_model"))
RAG_CONFIG = _config.get("rag", {})
MARKET_CONFIG = _config.get("market", {})
NEWS_CONFIG = _config.get("news", {})

# Initializations
openai_client = OpenAI(api_key=OPENAI_API_KEY)
llm = ChatOpenAI(model=MODEL, temperature=0.2)
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
