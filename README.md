# 🔍 RAG Content Generation Agent

> A modular, **scalable** Retrieval-Augmented Generation system for grounded multi-format content generation — powered by semantic search, **Gemini 2.5 Flash**, and an async **FastAPI** service layer.

---

## What It Does

Instead of letting an LLM hallucinate freely, this system:

1. **Retrieves** relevant chunks from your document corpus via semantic search
2. **Injects** that context into the prompt (no free-form generation)
3. **Generates** grounded content in multiple formats — blog posts, tweets, and LinkedIn posts
4. **Evaluates** output quality automatically using RAGAS metrics
5. **Serves** content via a scalable async API with caching, rate limiting, and batch processing

**Knowledge domain:** Answer Engine Optimization (AEO) & Google AI Overviews (GEO) — a timely, multi-faceted topic ideal for stress-testing retrieval quality.

---

## Architecture

```
                         ┌─────────────────────────────┐
                         │   FastAPI Server (async)     │
                         │   - Rate limiting (per-IP)   │
                         │   - Request validation       │
                         │   - Multi-worker (Uvicorn)   │
                         └────────────┬────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                  │
              POST /generate   POST /generate/batch   GET /health
                    │                 │                  │
                    └─────────────────┼──────────────────┘
                                      │
                              ┌───────▼───────┐
                              │  Query Cache   │  ← LRU + TTL (avoid redundant LLM calls)
                              │  (in-memory)   │
                              └───────┬────────┘
                                      │ cache miss
                                      ▼
                    ┌──────────────────────────────────┐
                    │      Retrieval Pipeline           │
                    │  ChromaDB → Top-K semantic search │
                    └────────────────┬─────────────────┘
                                     │
                              Context + Query
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                 │
                    ▼                ▼                 ▼
              Blog (async)    Tweet (async)    LinkedIn (async)   ← Concurrent generation
                    │                │                 │
                    └────────────────┼─────────────────┘
                                     │
                              Gemini 2.5 Flash
                                     │
                                     ▼
                              RAGAS Evaluation
                        Faithfulness · Relevancy · Recall
```

---

## Scale-Oriented Design

| Feature | Implementation | Why It Matters |
|---|---|---|
| **Async API** | FastAPI + Uvicorn workers | Handles concurrent requests without blocking |
| **Concurrent generation** | `asyncio.gather` for blog/tweet/linkedin | 3x faster per request vs sequential |
| **Response caching** | Thread-safe LRU cache with TTL | Eliminates redundant LLM calls for repeated queries |
| **Batch endpoint** | `/generate/batch` (up to 10 queries) | Reduces HTTP overhead for bulk processing |
| **Rate limiting** | Per-IP sliding window (30 RPM) | Prevents abuse and API quota exhaustion |
| **Multi-worker** | `uvicorn --workers 4` | Utilizes multiple CPU cores |
| **Health checks** | `/health` with cache stats and uptime | Load balancer and monitoring integration |
| **Configurable** | Environment variables for all settings | Tunable per deployment environment |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| API Framework | FastAPI + Uvicorn |
| Document Loading | LangChain Document Loaders |
| Text Splitting | LangChain `RecursiveCharacterTextSplitter` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | ChromaDB (persistent, local) |
| LLM | Google Gemini 2.5 Flash |
| Caching | Custom LRU with TTL (thread-safe) |
| Evaluation | RAGAS Framework |
| Config | `python-dotenv` |

---

## Project Structure

```
rag-content-agent/
├── main.py                  # CLI pipeline entry point
├── server.py                # FastAPI server (scalable API)
├── requirements.txt
├── .env                     # GOOGLE_API_KEY (never commit this)
├── src/
│   ├── config.py            # Environment & config setup
│   ├── ingest.py            # Document loading
│   ├── chunking.py          # Semantic text splitting
│   ├── embeddings.py        # Embedding generation & caching
│   ├── vector_store.py      # ChromaDB init & management
│   ├── retriever.py         # LangChain retriever wrapper
│   ├── generator.py         # Gemini 2.5 Flash generation
│   ├── prompts.py           # Prompt templates per format
│   ├── cache.py             # LRU cache with TTL
│   └── evaluator.py         # RAGAS evaluation
├── data/raw/                # Input documents (TXT, MD, PDF)
├── chroma_db/               # Persistent vector storage
└── outputs/
    ├── blog_output.txt
    ├── tweet_output.txt
    ├── linkedin_output.txt
    └── evaluation_results.json
```

---

## Quickstart

### 1. Install

```bash
git clone https://github.com/jaskiratkalra26/RAG-Content-Agent.git
cd rag-content-agent
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

Get your key at [Google AI Studio](https://aistudio.google.com/app/apikey).

### 3. Run

**Option A: CLI Pipeline** (single run, local output)

```bash
python main.py
python main.py --eval
python main.py --query "What is AEO and why does it matter?"
```

**Option B: API Server** (scalable, multi-user)

```bash
# Development (single worker)
uvicorn server:app --reload

# Production (multi-worker)
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## API Reference

### `POST /generate` — Single Query

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "How is AEO different from SEO?", "formats": ["blog", "tweet", "linkedin"]}'
```

**Response:**
```json
{
  "query": "How is AEO different from SEO?",
  "blog": "...",
  "tweet": "...",
  "linkedin": "...",
  "cached": false,
  "generation_time_seconds": 12.4
}
```

### `POST /generate/batch` — Batch Processing

```bash
curl -X POST http://localhost:8000/generate/batch \
  -H "Content-Type: application/json" \
  -d '{"queries": ["What is AEO?", "How does GEO work?"], "formats": ["blog", "tweet"]}'
```

### `GET /health` — Health Check

```json
{
  "status": "healthy",
  "retriever_ready": true,
  "cache_stats": {"size": 5, "max_size": 200, "hit_rate": 0.62},
  "uptime_seconds": 3600.0
}
```

Interactive API docs available at `http://localhost:8000/docs` (Swagger UI).

---

## Evaluation

Output is automatically scored using **RAGAS** across three metrics:

| Metric | What It Measures |
|---|---|
| **Faithfulness** | Does output stay grounded in retrieved context? (hallucination check) |
| **Answer Relevancy** | Does output address the user's query? |
| **Context Recall** | Did retrieval surface all necessary information? |

**Score interpretation:** `≥ 0.90` excellent · `0.80–0.89` good · `0.70–0.79` needs improvement · `< 0.70` requires intervention

### Example Output (`evaluation_results.json`)

```json
{
    "overall_metrics": {
        "faithfulness": 1.0,
        "answer_relevancy": 0.75,
        "context_recall": 1.0
    },
    "query_wise_evaluation": [
        {
            "question": "What is AEO?",
            "faithfulness": 1.0,
            "answer_relevancy": 0.82,
            "context_recall": 1.0
        },
        {
            "question": "How is AEO different from SEO?",
            "faithfulness": 1.0,
            "answer_relevancy": 0.68,
            "context_recall": 1.0
        }
    ]
}
```

---

## Hallucination Mitigation

This system reduces hallucinations through layered defenses:

- **Explicit grounding instruction** — `"Use ONLY the provided context"` in every prompt
- **Semantic chunking** — preserves paragraph/sentence boundaries; no arbitrary splits
- **Chunk overlap (150 chars)** — facts spanning chunk boundaries stay contextualized
- **Top-K = 5** — enough context richness without introducing contradictory noise
- **RAGAS faithfulness monitoring** — low scores trigger targeted debugging

---

## Key Design Decisions

**Why `all-MiniLM-L6-v2`?** Lightweight (~33M params), fast CPU inference, trained on 215M sentence pairs — excellent semantic quality for 800-char chunks.

**Why chunk size 800 / overlap 150?** ~150–200 words per chunk covers a coherent idea; 20% overlap prevents facts from being split across boundaries.

**Why Top-K = 5?** ~4000 characters of context — sufficient for comprehensive grounding without noise diluting retrieval signal.

**Why Gemini 2.5 Flash?** 1M token context window, fastest inference in its class, free tier available, actively maintained.

**Why FastAPI?** Async-native, auto-generates OpenAPI docs, built-in validation via Pydantic, production-proven with Uvicorn workers.

---

## Scaling Path

| Concern | Current | Production Path |
|---|---|---|
| API Layer | FastAPI + Uvicorn (multi-worker) | Kubernetes pods + horizontal scaling |
| Vector DB | ChromaDB (local) | Pinecone / Qdrant / Weaviate (managed) |
| Caching | In-memory LRU | Redis / Memcached (distributed) |
| Retrieval | Dense-only | Hybrid: dense + BM25 + reranking |
| Generation | Concurrent (asyncio) | Task queue (Celery + Redis) |
| Rate Limiting | In-memory per-IP | API gateway (Kong / AWS API Gateway) |
| Monitoring | `/health` endpoint | Prometheus + Grafana |

---

## Limitations

- **Retrieval-bound:** If the answer isn't in your documents, the system won't fabricate it — but it also can't answer
- **API rate limits:** Gemini free tier is 15 RPM; throttling delays are baked in
- **Keyword edge cases:** Proper names / product IDs may retrieve poorly — hybrid search would help
- **Embedding language quality:** `all-MiniLM-L6-v2` is optimized for English; use `multilingual-e5-large` for other languages
- **Cache scope:** In-memory cache does not persist across server restarts (Redis would solve this)

---

## Key Learnings

- Evaluation is non-negotiable — RAGAS transforms subjective quality into trackable metrics
- Chunk boundaries matter more than most tutorials suggest — semantic splits consistently outperform arbitrary splits
- Explicit grounding instructions in prompts (`"Use ONLY..."`) measurably reduce hallucinations
- Concurrent async generation delivers 3x throughput improvement over sequential calls
- Response caching at the query level eliminates the most common source of redundant LLM cost

---

## Skills Demonstrated

✅ Full-stack AI system design (pipeline → ML → generation → evaluation)
✅ Scalable API architecture with FastAPI and async concurrency
✅ Prompt engineering for grounding and hallucination reduction
✅ Evaluation-driven development with quantitative metrics
✅ Caching, rate limiting, and batch processing for production readiness
✅ Modular architecture with separation of concerns
✅ Production mindset — logging, error handling, scalability planning