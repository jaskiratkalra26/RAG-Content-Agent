"""Chunking utilities."""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.config import CHUNK_SIZE, CHUNK_OVERLAP

def split_documents(documents):
    """
    Splits a list of standard LangChain Document objects into smaller chunks.
    Uses RecursiveCharacterTextSplitter with settings defined in config.py.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    
    # Generate and return chunks
    chunks = text_splitter.split_documents(documents)
    return chunks
