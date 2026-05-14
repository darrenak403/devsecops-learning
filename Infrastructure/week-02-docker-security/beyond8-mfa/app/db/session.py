import logging
import time

from sqlalchemy import create_engine, event
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = (
    create_engine(
        settings.database_url,
        pool_pre_ping=settings.db_pool_pre_ping,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_use_lifo=True,
    )
    if settings.database_url
    else None
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None
logger = logging.getLogger(__name__)

_resolved_async_db_url = settings.async_database_url or (
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if settings.database_url.startswith("postgresql://")
    else settings.database_url
)
try:
    async_engine = (
        create_async_engine(
            _resolved_async_db_url,
            pool_pre_ping=settings.db_pool_pre_ping,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle_seconds,
            pool_use_lifo=True,
            echo=False,
        )
        if _resolved_async_db_url
        else None
    )
except InvalidRequestError:
    async_engine = None
AsyncSessionLocal = (
    async_sessionmaker(bind=async_engine, expire_on_commit=False, autoflush=False, autocommit=False)
    if async_engine
    else None
)


def _register_query_timing_hooks() -> None:
    if engine is None:
        return

    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(_, __, ___, ____, context, _____):  # pragma: no cover
        context._query_start_time = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def _after_cursor_execute(_, __, statement, ___, context, ____):  # pragma: no cover
        start = getattr(context, "_query_start_time", None)
        if start is None:
            return
        duration_ms = (time.perf_counter() - start) * 1000
        if duration_ms >= settings.sql_slow_query_ms:
            compact_sql = " ".join(statement.strip().split())
            logger.warning("slow_sql duration_ms=%.2f query=%s", duration_ms, compact_sql[:300])


_register_query_timing_hooks()


def _register_async_query_timing_hooks() -> None:
    if async_engine is None:
        return

    @event.listens_for(async_engine.sync_engine, "before_cursor_execute")
    def _before_async_cursor_execute(_, __, ___, ____, context, _____):  # pragma: no cover
        context._query_start_time = time.perf_counter()

    @event.listens_for(async_engine.sync_engine, "after_cursor_execute")
    def _after_async_cursor_execute(_, __, statement, ___, context, ____):  # pragma: no cover
        start = getattr(context, "_query_start_time", None)
        if start is None:
            return
        duration_ms = (time.perf_counter() - start) * 1000
        if duration_ms >= settings.sql_slow_query_ms:
            compact_sql = " ".join(statement.strip().split())
            logger.warning("slow_async_sql duration_ms=%.2f query=%s", duration_ms, compact_sql[:300])


_register_async_query_timing_hooks()


def get_db():
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is missing. Configure Supabase Postgres connection in .env")

    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db():
    if AsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL is missing. Configure Supabase Postgres connection in .env")

    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
