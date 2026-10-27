import time
from typing import Any

from pydantic import BaseModel


class CacheEntry(BaseModel):
    data: Any
    expires_at: float


class TTLCache:
    """Thread-safe in-memory TTL cache for expensive AI generation requests."""

    def __init__(self, default_ttl_seconds: int = 600) -> None:
        self.default_ttl = default_ttl_seconds
        self._cache: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() > entry.expires_at:
            self._cache.pop(key, None)
            return None
        return entry.data

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds or self.default_ttl
        self._cache[key] = CacheEntry(
            data=value,
            expires_at=time.time() + ttl,
        )

    def clear(self) -> None:
        self._cache.clear()


generation_cache = TTLCache(default_ttl_seconds=600)
