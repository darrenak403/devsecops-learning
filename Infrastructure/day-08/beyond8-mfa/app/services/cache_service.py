from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self) -> None:
        self._client = None
        if not settings.redis_enabled:
            return
        if not settings.upstash_redis_rest_url or not settings.upstash_redis_rest_token:
            logger.warning("REDIS_ENABLED=true but Upstash credentials are missing. Cache disabled.")
            return
        try:
            from upstash_redis import Redis

            self._client = Redis(
                url=settings.upstash_redis_rest_url,
                token=settings.upstash_redis_rest_token,
            )
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            logger.warning("Failed to initialize Upstash Redis client: %s", exc)
            self._client = None

    def _key(self, key: str) -> str:
        prefix = (settings.key_prefix or "").strip()
        if not prefix:
            return key
        return f"{prefix}:{key}"

    def _seconds_until_next_midnight(self) -> int:
        now = datetime.now()
        next_midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        seconds = int((next_midnight - now).total_seconds())
        return max(seconds, 1)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def get_json(self, key: str) -> Any | None:
        if not self._client:
            return None
        try:
            raw_value = self._client.get(self._key(key))
            if raw_value is None:
                return None
            if isinstance(raw_value, (dict, list, int, float, bool)):
                return raw_value
            return json.loads(raw_value)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:  # pragma: no cover
            logger.warning("Redis deserialize failed for key %s: %s", key, exc)
            return None
        except Exception as exc:  # pragma: no cover - network/runtime failures
            logger.warning("Redis GET failed for key %s: %s", key, exc)
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        if not self._client:
            return
        try:
            ttl_to_midnight = self._seconds_until_next_midnight()
            effective_ttl = min(max(ttl_seconds, 1), ttl_to_midnight)
            self._client.set(self._key(key), json.dumps(value, ensure_ascii=False), ex=effective_ttl)
        except Exception as exc:  # pragma: no cover
            logger.warning("Redis SET failed for key %s: %s", key, exc)

    def get_int(self, key: str, default: int = 1) -> int:
        raw_value = self.get_json(key)
        if raw_value is None:
            return default
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return default

    def bump_version(self, key: str) -> int:
        if not self._client:
            return 1
        namespaced_key = self._key(key)
        try:
            next_value = self._client.incr(namespaced_key)
            # Version keys also expire at midnight to prevent key growth over time.
            self._client.expire(namespaced_key, self._seconds_until_next_midnight())
            return int(next_value)
        except Exception as exc:  # pragma: no cover
            logger.warning("Redis INCR failed for key %s: %s", key, exc)
            return 1


cache_service = CacheService()
