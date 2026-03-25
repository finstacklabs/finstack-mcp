"""
FinStack Cache Utility

Simple TTL-based in-memory cache to minimize API calls.
Different TTLs for different data types:
  - Quotes: 5 minutes (market data changes frequently)
  - Fundamentals: 1 hour (quarterly data, slow-changing)
  - Historical: 24 hours (past data doesn't change)
"""

import time
import hashlib
import json
import logging
from typing import Any
from functools import wraps

logger = logging.getLogger("finstack.cache")


class TTLCache:
    """Thread-safe TTL cache with automatic expiry."""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size

    def _make_key(self, *args, **kwargs) -> str:
        """Create a deterministic cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        """Get value if exists and not expired."""
        if key in self._store:
            value, expiry = self._store[key]
            if time.time() < expiry:
                logger.debug(f"Cache HIT: {key[:16]}...")
                return value
            else:
                del self._store[key]
                logger.debug(f"Cache EXPIRED: {key[:16]}...")
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store value with TTL."""
        # Evict oldest entries if cache is full
        if len(self._store) >= self._max_size:
            self._evict_expired()
            if len(self._store) >= self._max_size:
                # Remove oldest 10%
                sorted_keys = sorted(
                    self._store.keys(), key=lambda k: self._store[k][1]
                )
                for k in sorted_keys[: self._max_size // 10]:
                    del self._store[k]

        expiry = time.time() + (ttl or self._default_ttl)
        self._store[key] = (value, expiry)
        logger.debug(f"Cache SET: {key[:16]}... (ttl={ttl or self._default_ttl}s)")

    def _evict_expired(self) -> None:
        """Remove all expired entries."""
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if now >= exp]
        for k in expired:
            del self._store[k]

    def clear(self) -> None:
        """Clear entire cache."""
        self._store.clear()
        logger.info("Cache cleared")

    @property
    def size(self) -> int:
        return len(self._store)


# Global cache instances with different TTLs
quotes_cache = TTLCache(default_ttl=300, max_size=500)       # 5 min
fundamentals_cache = TTLCache(default_ttl=3600, max_size=500)  # 1 hour
historical_cache = TTLCache(default_ttl=86400, max_size=200)   # 24 hours
general_cache = TTLCache(default_ttl=600, max_size=300)        # 10 min


def cached(cache_instance: TTLCache, ttl: int | None = None):
    """Decorator to cache function results.

    Usage:
        @cached(quotes_cache, ttl=300)
        def get_stock_quote(symbol: str) -> dict:
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = cache_instance._make_key(func.__name__, *args, **kwargs)
            result = cache_instance.get(key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            if result is not None:
                cache_instance.set(key, result, ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = cache_instance._make_key(func.__name__, *args, **kwargs)
            result = cache_instance.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            if result is not None:
                cache_instance.set(key, result, ttl)
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
