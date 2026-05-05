"""
Lightweight In-Memory Cache
----------------------------
Thread-safe TTL cache for reducing database load and enabling
graceful degradation when MongoDB is unavailable.

Usage:
    from app.services.cache import cache

    cache.set("branch_loads", data)          # store with default TTL
    cache.set("branch_loads", data, ttl=600) # store with 10-minute TTL
    result = cache.get("branch_loads")       # returns None if expired/missing
"""

import logging
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 300  # 5 minutes


class InMemoryCache:
    """Simple dict-backed cache with per-key TTL, thread safety, and hit/miss tracking."""

    def __init__(self, default_ttl: int = _DEFAULT_TTL_SECONDS):
        self._store: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
        # ── observability counters ────────────────────────────────
        self._hits = 0
        self._misses = 0
        self._sets = 0

    # ── public API ────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """Return cached value or None if missing / expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() > entry["expires_at"]:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry["data"]

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Store *data* under *key* with a TTL (seconds)."""
        ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            self._store[key] = {
                "data": data,
                "created_at": time.time(),
                "expires_at": time.time() + ttl,
            }
            self._sets += 1

    def invalidate(self, key: str) -> None:
        """Remove a single key."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Drop everything."""
        with self._lock:
            self._store.clear()

    def info(self) -> dict:
        """Return cache stats for the health endpoint."""
        with self._lock:
            now = time.time()
            active = {
                k: round(v["expires_at"] - now, 1)
                for k, v in self._store.items()
                if v["expires_at"] > now
            }
            total_requests = self._hits + self._misses
            return {
                "active_keys": len(active),
                "keys_ttl": active,
                "hits": self._hits,
                "misses": self._misses,
                "sets": self._sets,
                "hit_rate": round(self._hits / total_requests * 100, 1) if total_requests else 0.0,
            }


# ── module-level singleton ────────────────────────────────────────────
cache = InMemoryCache()
