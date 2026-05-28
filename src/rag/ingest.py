"""
ingest.py — Building the Finnie knowledge base from declared sources.

Reads all declared knowledge sources, downloads/loads their content, splits the content into 
smaller chunks, creates embeddings for those chunks, and saves them into Chroma vector database.

Clears the existing Chroma collection before re-ingesting, so output is deterministic.
"""

import shutil
from pathlib import Path

from langchain_chroma import Chroma

from src.core.config import RAG_CONFIG, embeddings
from src.rag.chunking import chunk_documents
from src.rag.loaders import load_documents_for_source
from src.rag.sources import SOURCES
from src.utils.logger import setup_logger

logger = setup_logger("finnie.rag.ingest")


def main() -> None:
    persist_dir = Path(RAG_CONFIG.get("persist_dir", "./chroma_db"))
    collection_name = RAG_CONFIG.get("collection_name", "finnie_kb")

    # 1. Reset Chroma so re-runs are deterministic
    if persist_dir.exists():
        logger.info("Removing existing Chroma directory: %s", persist_dir)
        shutil.rmtree(persist_dir)

    # 2. Load + chunk every source
    all_chunks = []
    for source in SOURCES:
        docs = load_documents_for_source(source)
        chunks = chunk_documents(docs)
        all_chunks.extend(chunks)

    logger.info("Total chunks across all sources: %d", len(all_chunks))

    if not all_chunks:
        logger.error("No chunks to ingest. Check source URLs.")
        return

    # 3. Embed + persist
    logger.info("Embedding and persisting to %s ...", persist_dir)
    Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=str(persist_dir),
    )
    logger.info("Done. Knowledge base built at %s", persist_dir)


if __name__ == "__main__":
    main()