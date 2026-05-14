import sys
import os

# Fix for Vercel/Root execution: ensure project root is on PYTHONPATH for `app.*` imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.bootstrap import run_startup_bootstrap
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.middleware.docs_basic_auth import DocsBasicAuthMiddleware
from app.middleware.performance import add_request_timing_header
from app.middleware.performance_metrics import performance_metrics_middleware
from app.db.session import SessionLocal
from app.schemas.api_response import error_response
from app.services.cache_warming_service import cache_warming_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    should_bootstrap = settings.run_startup_bootstrap and os.getenv("VERCEL") != "1"

    if SessionLocal is not None and should_bootstrap:
        db = SessionLocal()
        try:
            run_startup_bootstrap(db)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    if AsyncSessionLocal is not None:
        async with AsyncSessionLocal() as async_db:
            await cache_warming_service.warm_subjects_cache(async_db)
    yield

app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs" if settings.api_docs_enabled else None,
    openapi_url="/api/openapi.json" if settings.api_docs_enabled else None,
    redoc_url="/api/redoc" if settings.api_docs_enabled else None,
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
async def root_health():
    return {"service": settings.app_name, "status": "ok"}

if not settings.database_url:
    raise RuntimeError("DATABASE_URL is required for Supabase Postgres connection")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.middleware("http")(add_request_timing_header)
app.middleware("http")(performance_metrics_middleware)

if settings.docs_basic_auth_enabled:
    app.add_middleware(
        DocsBasicAuthMiddleware,
        username=settings.docs_basic_auth_user.strip(),
        password=settings.docs_basic_auth_password.strip(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    payload = error_response(
        message="Dữ liệu đầu vào không hợp lệ",
        code=422,
        data=exc.errors(),
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(_: Request, exc: ResponseValidationError):
    """Avoid opaque 500 when response_model validation fails (e.g. legacy DB shapes)."""
    payload = error_response(
        message="Dữ liệu phản hồi không hợp lệ",
        code=500,
        data=exc.errors(),
    )
    return JSONResponse(status_code=500, content=payload.model_dump())


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        response = JSONResponse(status_code=exc.status_code, content=exc.detail)
    else:
        message = exc.detail if isinstance(exc.detail, str) else "Yêu cầu thất bại"
        payload = error_response(message=message, code=exc.status_code, data=None)
        response = JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    auth_clear_details = {"Could not validate credentials", "Tài khoản đã bị khóa", "Phiên đăng nhập không còn hợp lệ."}
    should_clear_auth_cookie = (exc.status_code in {401, 403}) and isinstance(exc.detail, str) and exc.detail in auth_clear_details
    if should_clear_auth_cookie:
        response.delete_cookie("auth_token", path="/")
        response.delete_cookie("refresh_token", path="/")

    return response


@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception):
    payload = error_response(message="Lỗi hệ thống nghiêm trọng", code=500, data=None)
    return JSONResponse(status_code=500, content=payload.model_dump())

app.include_router(api_router, prefix=settings.api_prefix)
