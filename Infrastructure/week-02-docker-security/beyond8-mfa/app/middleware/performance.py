import logging
import time
from collections.abc import Callable

from fastapi import Request, Response

from app.core.config import settings

logger = logging.getLogger(__name__)


async def add_request_timing_header(request: Request, call_next: Callable) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    if elapsed_ms >= settings.http_slow_request_ms:
        logger.warning(
            "slow_request method=%s path=%s duration_ms=%.2f status=%s",
            request.method,
            request.url.path,
            elapsed_ms,
            response.status_code,
        )
    return response
