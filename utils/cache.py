"""Query caching layer for search results."""

import logging
import hashlib
import time
from functools import wraps
from typing import Any, Callable, Dict, Tuple
from threading import RLock

logger = logging.getLogger(__name__)


class QueryCache:
    """In-memory cache for search queries with TTL support."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize query cache.

        Args:
            max_size: Maximum number of cached queries
            ttl_seconds: Time-to-live for cache entries (default: 1 hour)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.lock = RLock()
        self.hits = 0
        self.misses = 0

    def _generate_key(self, query: str, k: int) -> str:
        """
        Generate cache key from query parameters.

        Args:
            query: Search query string
            k: Number of results

        Returns:
            Hash-based cache key
        """
        cache_input = f"{query}::{k}"
        return hashlib.md5(cache_input.encode()).hexdigest()

    def get(self, query: str, k: int) -> Any | None:
        """
        Retrieve cached result if available and not expired.

        Args:
            query: Search query
            k: Number of results

        Returns:
            Cached result or None if not found/expired
        """
        key = self._generate_key(query, k)

        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None

            result, timestamp = self.cache[key]
            age = time.time() - timestamp

            # Check if expired
            if age > self.ttl_seconds:
                logger.debug(f"Cache entry expired: {key}")
                del self.cache[key]
                self.misses += 1
                return None

            self.hits += 1
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return result

    def set(self, query: str, k: int, result: Any) -> None:
        """
        Store result in cache.

        Args:
            query: Search query
            k: Number of results
            result: Search result to cache
        """
        key = self._generate_key(query, k)

        with self.lock:
            # Evict oldest if cache full
            if len(self.cache) >= self.max_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"Evicted oldest cache entry: {oldest_key}")

            self.cache[key] = (result, time.time())
            logger.debug(f"Cached result for query: {query[:50]}...")

    def clear(self) -> None:
        """Clear all cached entries."""
        with self.lock:
            self.cache.clear()
            logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        removed = 0

        with self.lock:
            expired_keys = [
                key for key, (_, timestamp) in self.cache.items()
                if (current_time - timestamp) > self.ttl_seconds
            ]

            for key in expired_keys:
                del self.cache[key]
                removed += 1

            if removed > 0:
                logger.debug(f"Cleaned up {removed} expired cache entries")

        return removed

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
                "ttl_seconds": self.ttl_seconds
            }

    def __len__(self) -> int:
        """Return number of cached entries."""
        return len(self.cache)

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return f"QueryCache({stats['size']}/{stats['max_size']}, hit_rate={stats['hit_rate_percent']}%)"


# Global cache instance
_search_cache = QueryCache(max_size=100, ttl_seconds=3600)


def cached_search(func: Callable) -> Callable:
    """
    Decorator to cache search function results.

    Usage:
        @cached_search
        def search_documents(query: str, k: int):
            ...
    """
    @wraps(func)
    def wrapper(query: str, k: int, *args, **kwargs):
        # Try to get from cache
        cached_result = _search_cache.get(query, k)
        if cached_result is not None:
            return cached_result

        # Call original function
        result = func(query, k, *args, **kwargs)

        # Store in cache
        _search_cache.set(query, k, result)

        return result

    return wrapper


def get_cache() -> QueryCache:
    """Get the global search cache instance."""
    return _search_cache


def clear_cache() -> None:
    """Clear all cached search results."""
    _search_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return _search_cache.get_stats()


def cleanup_expired_cache() -> int:
    """Clean up expired cache entries."""
    return _search_cache.cleanup_expired()
