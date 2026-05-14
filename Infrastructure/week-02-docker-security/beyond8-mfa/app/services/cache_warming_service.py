from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_question_source_async import crud_question_source_async
from app.services.cache_service import cache_service

_CACHE_SUBJECTS_TTL_SECONDS = 3600


class CacheWarmingService:
    async def warm_subjects_cache(self, db: AsyncSession) -> None:
        subjects = await crud_question_source_async.list_subjects_async(db)
        payload = [{"slug": s.slug, "code": s.code, "name": s.name} for s in subjects]
        cache_service.set_json("qs:subjects:v1", payload, _CACHE_SUBJECTS_TTL_SECONDS)

    async def warm_popular_subjects(self, db: AsyncSession, limit: int = 10) -> None:
        # Current data model does not track access frequency.
        # Warm a deterministic top-N by subject code as a safe default.
        subjects = await crud_question_source_async.list_subjects_async(db)
        for subject in subjects[: max(1, limit)]:
            cache_service.set_json(f"qs:subject:{subject.slug}:ver", 1, _CACHE_SUBJECTS_TTL_SECONDS)


cache_warming_service = CacheWarmingService()
