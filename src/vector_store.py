"""Vector database functionality using ChromaDB."""

import os
import logging
from langchain_community.vectorstores import Chroma
from src.config import CHROMA_PATH
from src.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

def create_vector_store(chunks):
    """
    Creates and persists a Chroma vector database from document chunks.
    """
    embedding_model = get_embedding_model()
    
    # Ensure the target directory exists
    os.makedirs(CHROMA_PATH, exist_ok=True)
    
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=CHROMA_PATH
    )
    
    logger.info("Vector DB created successfully.")
    return vector_store

def load_vector_store():
    """
    Loads an existing Chroma vector database from disk.
    """
    embedding_model = get_embedding_model()
    
    if os.path.exists(CHROMA_PATH):
        vector_store = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embedding_model
        )
        return vector_store
    else:
        logger.error("Vector DB not found at %s", CHROMA_PATH)
        return None
