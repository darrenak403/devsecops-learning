"""In-memory pagination helpers for list payloads."""

from __future__ import annotations

import math
from typing import Any, Sequence, TypeVar

T = TypeVar("T")


def paginate_slice(sequence: Sequence[T], *, page: int, limit: int) -> dict[str, Any]:
    """Slice ``sequence`` into a page; ``page`` and ``limit`` are 1-based page / page size."""
    safe_limit = max(1, int(limit))
    safe_page = max(1, int(page))
    total = len(sequence)
    total_pages = math.ceil(total / safe_limit) if total > 0 else 0
    offset = (safe_page - 1) * safe_limit
    items = list(sequence[offset : offset + safe_limit])
    return {
        "items": items,
        "page": safe_page,
        "limit": safe_limit,
        "total": total,
        "totalPages": total_pages,
        "hasNext": total > 0 and safe_page < total_pages,
        "hasPrevious": safe_page > 1 and total > 0,
    }


DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
