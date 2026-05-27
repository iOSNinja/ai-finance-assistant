"""
config.py — LLM, embeddings, and OpenAI client setup for Finnie.
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
def _get(name: str, yaml_path: tuple[str, ...]) -> str:
    if val := os.getenv(name):
        return val
    val = _config
    for key in yaml_path:
        val = val[key]
    return val

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in your .env file or environment.")

MODEL = _get("OPENAI_MODEL", ("llm", "model"))
EMBEDDING_MODEL = _get("OPENAI_EMBEDDING_MODEL", ("llm", "embedding_model"))

openai_client = OpenAI(api_key=OPENAI_API_KEY)
llm = ChatOpenAI(model=MODEL, temperature=0.2)
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
