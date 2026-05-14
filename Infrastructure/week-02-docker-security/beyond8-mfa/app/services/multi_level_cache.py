from __future__ import annotations

import time
from typing import Any

from app.services.cache_service import cache_service


class MultiLevelCache:
    def __init__(self) -> None:
        self.memory_cache: dict[str, Any] = {}
        self.memory_cache_ttl: dict[str, float] = {}

    async def get(self, key: str) -> Any:
        now = time.time()
        if key in self.memory_cache and now < self.memory_cache_ttl.get(key, 0):
            return self.memory_cache[key]
        result = cache_service.get_json(key)
        if result is not None:
            self.memory_cache[key] = result
            self.memory_cache_ttl[key] = now + 60
            return result
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.memory_cache[key] = value
        self.memory_cache_ttl[key] = time.time() + min(ttl_seconds, 60)
        cache_service.set_json(key, value, ttl_seconds)

    async def invalidate(self, key: str) -> None:
        self.memory_cache.pop(key, None)
        self.memory_cache_ttl.pop(key, None)
