"""Ingest raw documents into the pipeline."""

import logging
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from src.config import DATA_PATH

logger = logging.getLogger(__name__)

def load_pdf(file_path):
    """Loads a PDF file and returns its pages as LangChain Document objects."""
    loader = PyPDFLoader(file_path)
    return loader.load()

def load_text(file_path):
    """Loads a generic text file."""
    loader = TextLoader(file_path, encoding='utf-8')
    return loader.load()

def load_documents(directory_path=DATA_PATH):
    """
    Scans the given directory, detects file types, and loads all supported 
    files (PDF, TXT, MD). Returns a combined list of Document objects.
    """
    documents = []
    
    # Check if directory exists
    if not os.path.exists(directory_path):
        logger.warning("Directory not found: %s", directory_path)
        return documents

    # Iterate through all files in the given directory
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
            
        try:
            # File type detection and loading
            if filename.lower().endswith(".pdf"):
                documents.extend(load_pdf(file_path))
            elif filename.lower().endswith(".txt"):
                documents.extend(load_text(file_path))
            elif filename.lower().endswith(".md"):
                documents.extend(load_text(file_path))
            else:
                logger.info("Skipping unsupported file type: %s", filename)
        except Exception:
            logger.exception("Error loading file: %s", filename)
            
    return documents

if __name__ == "__main__":
    docs = load_documents()
    logger.info("Loaded %s documents.", len(docs))
