from __future__ import annotations

import logging
import time

from fastapi import Request

from app.core.config import settings

logger = logging.getLogger(__name__)


async def performance_metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
    if duration_ms >= settings.http_slow_request_ms:
        logger.warning("slow_request path=%s duration_ms=%.2f", request.url.path, duration_ms)
    return response
