"""Embeddings utilities."""

from langchain_community.embeddings import HuggingFaceEmbeddings
from src.config import EMBEDDING_MODEL

def get_embedding_model():
    """
    Initializes and returns the HuggingFace embedding model.
    """
    model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return model
