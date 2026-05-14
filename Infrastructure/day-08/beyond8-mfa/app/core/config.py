import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

# Always merged with CORS_ORIGINS so production env cannot accidentally drop known admin / local origins.
_BUILTIN_CORS_ORIGINS: tuple[str, ...] = (
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://100.69.71.17:3000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://source.beyond8.io.vn",
    "https://mfa.beyond8.io.vn",
    "https://hoctot.beyond8.io.vn",
)


def _parse_cors_origins_raw(raw: str) -> List[str]:
    normalized: List[str] = []
    for raw_item in raw.split(","):
        candidate = raw_item.strip().strip("\"'").rstrip("/")
        if not candidate:
            continue
        if candidate not in normalized:
            normalized.append(candidate)
    return normalized


class Settings(BaseSettings):
    app_name: str = "Beyond8 Auth Service"
    api_prefix: str = Field(default="/api", alias="API_PREFIX")
    expose_api_docs: bool = Field(default=True, alias="EXPOSE_API_DOCS")
    docs_basic_auth_user: str = Field(default="", alias="DOCS_BASIC_AUTH_USER")
    docs_basic_auth_password: str = Field(default="", alias="DOCS_BASIC_AUTH_PASSWORD")

    database_url: str = Field(default="", alias="DATABASE_URL")
    async_database_url: str = Field(default="", alias="ASYNC_DATABASE_URL")
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    db_pool_recycle_seconds: int = Field(default=3600, alias="DB_POOL_RECYCLE_SECONDS")
    db_pool_pre_ping: bool = Field(default=True, alias="DB_POOL_PRE_PING")
    enable_query_optimization: bool = Field(default=True, alias="ENABLE_QUERY_OPTIMIZATION")
    enable_async_database: bool = Field(default=True, alias="ENABLE_ASYNC_DATABASE")
    sql_slow_query_ms: int = Field(default=200, alias="SQL_SLOW_QUERY_MS")
    http_slow_request_ms: int = Field(default=500, alias="HTTP_SLOW_REQUEST_MS")

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=52560000, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    course_access_token_expire_days: int = 30

    otp_ttl_seconds: int = 60
    otp_length: int = 6
    otp_refresh_cooldown_seconds: int = 60

    seed_admin_email: str = "admin@gmail.com"
    run_startup_bootstrap: bool = Field(default=True, alias="RUN_STARTUP_BOOTSTRAP")

    key_prefix: str = Field(default="BY8", alias="KEY_PREFIX")
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")
    upstash_redis_rest_url: str = Field(default="", alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_rest_token: str = Field(default="", alias="UPSTASH_REDIS_REST_TOKEN")
    cors_origins: str = Field(
        default="",
        alias="CORS_ORIGINS",
        description="Extra origins (comma-separated), merged with built-in defaults (mfa/source/hoctot/localhost).",
    )

    model_config = SettingsConfigDict(env_file=_env_path, env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        merged = list(_BUILTIN_CORS_ORIGINS) + _parse_cors_origins_raw(self.cors_origins)
        out: List[str] = []
        for origin in merged:
            if origin not in out:
                out.append(origin)
        return out

    @property
    def docs_basic_auth_enabled(self) -> bool:
        """Khi set cả user + password: bật /api/docs nhưng chỉ vào được sau Basic Auth."""
        u = self.docs_basic_auth_user.strip()
        p = self.docs_basic_auth_password.strip()
        return bool(u and p)

    @property
    def api_docs_enabled(self) -> bool:
        """Public docs (EXPOSE_API_DOCS) hoặc docs riêng có Basic Auth."""
        return self.expose_api_docs or self.docs_basic_auth_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
