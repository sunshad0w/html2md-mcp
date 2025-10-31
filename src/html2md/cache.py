"""Simple in-memory cache for HTML to Markdown conversions."""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Simple in-memory cache with TTL support.

    This cache stores conversion results in memory with time-to-live (TTL)
    expiration. Useful for reducing redundant conversions of the same URLs.
    """

    def __init__(self, ttl: int = 3600) -> None:
        """
        Initialize cache.

        Args:
            ttl: Time-to-live in seconds (default: 3600 = 1 hour)
        """
        self._cache: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl
        logger.info(f"Cache initialized with TTL: {ttl} seconds")

    def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        if key not in self._cache:
            return None

        timestamp, value = self._cache[key]
        age = time.time() - timestamp

        if age > self._ttl:
            # Entry expired, remove it
            del self._cache[key]
            logger.debug(f"Cache entry expired for key: {key[:20]}...")
            return None

        logger.debug(f"Cache hit for key: {key[:20]}... (age: {age:.1f}s)")
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (time.time(), value)
        logger.debug(f"Cache entry stored for key: {key[:20]}...")

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} entries removed")

    def cleanup(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, (timestamp, _) in self._cache.items()
            if current_time - timestamp > self._ttl
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info(f"Cache cleanup: {len(expired_keys)} expired entries removed")

        return len(expired_keys)

    def size(self) -> int:
        """
        Get current cache size.

        Returns:
            Number of entries in cache
        """
        return len(self._cache)

    @property
    def ttl(self) -> int:
        """Get cache TTL in seconds."""
        return self._ttl


# Global cache instance (optional, can be enabled per request)
_global_cache: SimpleCache | None = None


def get_cache(ttl: int = 3600) -> SimpleCache:
    """
    Get or create global cache instance.

    Args:
        ttl: Time-to-live in seconds (default: 3600)

    Returns:
        Global cache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = SimpleCache(ttl=ttl)
    return _global_cache


def clear_global_cache() -> None:
    """Clear the global cache."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()
