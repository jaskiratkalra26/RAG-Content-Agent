"""Generation logic using Gemini and LangChain."""

import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain
from src.config import GOOGLE_API_KEY, GEMINI_MODEL_NAME
from src.prompts import BLOG_PROMPT, TWEET_PROMPT, LINKEDIN_PROMPT

def _build_retrieval_chain(prompt_text: str, retriever):
    """Builds a LangChain retrieval chain."""
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL_NAME, 
        google_api_key=GOOGLE_API_KEY,
        temperature=0.7
    )
    prompt = ChatPromptTemplate.from_template(prompt_text)
    document_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, document_chain)

def generate_blog(query: str, retriever) -> str:
    """Generates a blog post based on the query and retriever."""
    chain = _build_retrieval_chain(BLOG_PROMPT, retriever)
    response = chain.invoke({"input": query})
    time.sleep(15)  # Throttle to avoid rate limits
    return response.get("answer", "")

def generate_tweet(query: str, retriever) -> str:
    """Generates a tweet based on the query and retriever."""
    chain = _build_retrieval_chain(TWEET_PROMPT, retriever)
    response = chain.invoke({"input": query})
    time.sleep(15)  # Throttle to avoid rate limits
    return response.get("answer", "")

def generate_linkedin_post(query: str, retriever) -> str:
    """Generates a LinkedIn post based on the query and retriever."""
    chain = _build_retrieval_chain(LINKEDIN_PROMPT, retriever)
    response = chain.invoke({"input": query})
    time.sleep(15)  # Throttle to avoid rate limits
    return response.get("answer", "")
