"""
chunking.py — Document chunking for the RAG pipeline.

Uses RecursiveCharacterTextSplitter, which splits on natural boundaries
(paragraph > sentence > word > char). Chunk size and overlap are read
from config.yaml's rag section.
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.config import RAG_CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("finnie.rag.chunking")

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=RAG_CONFIG.get("chunk_size", 1000),
    chunk_overlap=RAG_CONFIG.get("chunk_overlap", 200),
    separators=["\n\n", "\n", ". ", " ", ""],
)

def chunk_documents(docs: list[Document]) -> list[Document]:
    """Split documents into RAG-sized chunks, preserving metadata."""
    chunks = _splitter.split_documents(docs)
    logger.info("Documents chunked", extra={"input_docs": len(docs), "output_chunks": len(chunks)})
    return chunks
