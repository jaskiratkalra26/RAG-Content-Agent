"""Retriever functionality."""

from src.config import TOP_K

def retrieve_context(query, vectordb, k=TOP_K):
    """
    Retrieves the top-k relevant document chunks from the vector database.
    """
    # Create the retriever from the vector database
    retriever = vectordb.as_retriever(search_kwargs={"k": k})
    
    # Retrieve documents related to the query
    retrieved_docs = retriever.invoke(query)
    
    return retrieved_docs
