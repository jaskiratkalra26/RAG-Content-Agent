"""Configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_NAME = "rag-content-agent"

# Data Path Configuration
DATA_PATH = os.path.join("data", "raw")
OUTPUT_PATH = "outputs"
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Chunking Settings for LangChain TextSplitter
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Vector Database and Embedding Settings
CHROMA_PATH = "chroma_db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 5

# Generation Settings
GEMINI_MODEL_NAME = "gemini-2.5-flash"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Server Settings (FastAPI)
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
SERVER_WORKERS = int(os.getenv("SERVER_WORKERS", "4"))

# Cache Settings
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "200"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL", "3600"))

