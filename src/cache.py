"""In-memory LRU cache with TTL for query results.

Avoids redundant LLM calls for repeated or similar queries,
reducing latency and API cost at scale.
"""

import time
import hashlib
import logging
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)


class QueryCache:
    """Thread-safe LRU cache with time-to-live expiration.
    
    Designed for high-concurrency environments where multiple
    users may submit identical or similar queries.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    @staticmethod
    def _make_key(query: str) -> str:
        """Creates a normalized cache key from query text."""
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def get(self, query: str) -> dict | None:
        """Retrieves cached result if it exists and hasn't expired."""
        key = self._make_key(query)
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self._ttl:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    self._hits += 1
                    logger.info("Cache HIT for query (hits=%d, misses=%d)", self._hits, self._misses)
                    return entry["data"]
                else:
                    # Expired entry
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    def set(self, query: str, data: dict) -> None:
        """Stores a result in the cache, evicting oldest if at capacity."""
        key = self._make_key(query)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = {
                "data": data,
                "timestamp": time.time()
            }
            # Evict oldest entries if over capacity
            while len(self._cache) > self._max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.debug("Cache evicted entry: %s", evicted_key[:12])
    
    def clear(self) -> None:
        """Clears all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def stats(self) -> dict:
        """Returns cache performance statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0
            }
