"""FastAPI server for the RAG Content Agent.

Provides async API endpoints for scalable, multi-user content generation
with concurrent processing, response caching, and rate limiting.

Usage:
    uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
"""

import os
import time
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.ingest import load_documents
from src.chunking import split_documents
from src.vector_store import create_vector_store, load_vector_store
from src.generator import generate_blog, generate_tweet, generate_linkedin_post
from src.cache import QueryCache
from src.config import OUTPUT_PATH, TOP_K

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
for logger_name in ["httpx", "urllib3", "huggingface_hub", "sentence_transformers"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global state — initialized once at startup, shared across requests
# ---------------------------------------------------------------------------
retriever = None
query_cache = QueryCache(max_size=200, ttl_seconds=3600)

# Rate limiter: tracks per-IP request timestamps
rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_RPM = 30  # requests per minute per IP


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="The topic or question to generate content for")
    formats: list[str] = Field(default=["blog", "tweet", "linkedin"], description="Content formats to generate")

class BatchGenerateRequest(BaseModel):
    queries: list[str] = Field(..., min_length=1, max_length=10, description="List of queries (max 10 per batch)")
    formats: list[str] = Field(default=["blog", "tweet", "linkedin"], description="Content formats to generate")

class GenerateResponse(BaseModel):
    query: str
    blog: Optional[str] = None
    tweet: Optional[str] = None
    linkedin: Optional[str] = None
    cached: bool = False
    generation_time_seconds: float = 0.0

class BatchGenerateResponse(BaseModel):
    results: list[GenerateResponse]
    total_time_seconds: float

class HealthResponse(BaseModel):
    status: str
    retriever_ready: bool
    cache_stats: dict
    uptime_seconds: float


# ---------------------------------------------------------------------------
# Startup / Shutdown lifecycle
# ---------------------------------------------------------------------------
startup_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the RAG pipeline once at server startup."""
    global retriever
    
    logger.info("Initializing RAG pipeline...")
    
    # Try loading existing vector store first, fall back to full ingestion
    vectordb = load_vector_store()
    if vectordb is None:
        logger.info("No existing vector store found. Running full ingestion pipeline...")
        documents = load_documents()
        if not documents:
            logger.error("No documents found in data/raw/. Server starting without retriever.")
            yield
            return
        chunks = split_documents(documents)
        vectordb = create_vector_store(chunks)
    
    retriever = vectordb.as_retriever(search_kwargs={"k": TOP_K})
    logger.info("RAG pipeline ready. Server accepting requests.")
    
    yield
    
    # Cleanup
    logger.info("Server shutting down. Clearing cache.")
    query_cache.clear()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RAG Content Agent API",
    description="Scalable, async content generation powered by RAG and Gemini 2.5 Flash",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Rate limiting middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Per-IP rate limiting to prevent abuse at scale."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Clean old timestamps and check rate
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []
    
    rate_limit_store[client_ip] = [
        ts for ts in rate_limit_store[client_ip] if now - ts < 60
    ]
    
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_RPM:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_RPM} requests per minute."
        )
    
    rate_limit_store[client_ip].append(now)
    response = await call_next(request)
    return response


# ---------------------------------------------------------------------------
# Generation helper
# ---------------------------------------------------------------------------
async def _generate_for_query(query: str, formats: list[str]) -> GenerateResponse:
    """Generates content for a single query with caching and concurrent execution."""
    if retriever is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized. No documents loaded.")
    
    # Check cache first
    cached_result = query_cache.get(query)
    if cached_result:
        return GenerateResponse(
            query=query,
            **{fmt: cached_result.get(fmt) for fmt in ["blog", "tweet", "linkedin"]},
            cached=True,
            generation_time_seconds=0.0
        )
    
    start = time.time()
    
    # Build async tasks for requested formats (concurrent generation)
    loop = asyncio.get_event_loop()
    tasks = {}
    
    if "blog" in formats:
        tasks["blog"] = loop.run_in_executor(None, generate_blog, query, retriever)
    if "tweet" in formats:
        tasks["tweet"] = loop.run_in_executor(None, generate_tweet, query, retriever)
    if "linkedin" in formats:
        tasks["linkedin"] = loop.run_in_executor(None, generate_linkedin_post, query, retriever)
    
    # Await all concurrently
    results = {}
    for fmt, task in tasks.items():
        try:
            results[fmt] = await task
        except Exception as e:
            logger.error("Generation failed for format '%s': %s", fmt, e)
            results[fmt] = f"[Error: {str(e)}]"
    
    elapsed = round(time.time() - start, 2)
    
    # Cache the result
    query_cache.set(query, results)
    
    return GenerateResponse(
        query=query,
        blog=results.get("blog"),
        tweet=results.get("tweet"),
        linkedin=results.get("linkedin"),
        cached=False,
        generation_time_seconds=elapsed
    )


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return HealthResponse(
        status="healthy",
        retriever_ready=retriever is not None,
        cache_stats=query_cache.stats(),
        uptime_seconds=round(time.time() - startup_time, 1)
    )


@app.post("/generate", response_model=GenerateResponse, tags=["Generation"])
async def generate_content(request: GenerateRequest):
    """Generate content for a single query.
    
    Supports concurrent generation of multiple formats (blog, tweet, linkedin)
    and returns cached results when available.
    """
    return await _generate_for_query(request.query, request.formats)


@app.post("/generate/batch", response_model=BatchGenerateResponse, tags=["Generation"])
async def generate_batch(request: BatchGenerateRequest):
    """Process multiple queries in a single request.
    
    Queries are processed concurrently for maximum throughput.
    Limited to 10 queries per batch to prevent resource exhaustion.
    """
    start = time.time()
    
    # Process all queries concurrently
    tasks = [
        _generate_for_query(query, request.formats)
        for query in request.queries
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any exceptions in results
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Batch query %d failed: %s", i, result)
            final_results.append(GenerateResponse(
                query=request.queries[i],
                generation_time_seconds=0.0
            ))
        else:
            final_results.append(result)
    
    return BatchGenerateResponse(
        results=final_results,
        total_time_seconds=round(time.time() - start, 2)
    )


@app.post("/cache/clear", tags=["System"])
async def clear_cache():
    """Clears the query cache. Useful after updating source documents."""
    query_cache.clear()
    return {"message": "Cache cleared successfully"}
