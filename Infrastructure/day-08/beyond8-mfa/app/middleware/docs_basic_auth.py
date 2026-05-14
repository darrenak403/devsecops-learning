"""HTTP Basic Auth for /api/docs, OpenAPI JSON, and ReDoc only."""

import base64
import secrets
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

DOCS_PATHS_PREFIX = (
    "/api/docs",
    "/api/openapi.json",
    "/api/redoc",
)


class DocsBasicAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        username: str,
        password: str,
    ) -> None:
        super().__init__(app)
        self._username = username
        self._password = password

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if not any(path == p or path.startswith(f"{p}/") for p in DOCS_PATHS_PREFIX):
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if not auth or not auth.lower().startswith("basic "):
            return _unauthorized()

        try:
            raw = base64.b64decode(auth[6:].strip()).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return _unauthorized()

        user, sep, pwd = raw.partition(":")
        if sep != ":":
            return _unauthorized()

        ok_user = secrets.compare_digest(user, self._username)
        ok_pwd = secrets.compare_digest(pwd, self._password)
        if not (ok_user and ok_pwd):
            return _unauthorized()

        return await call_next(request)


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": "Authentication required"},
        headers={"WWW-Authenticate": 'Basic realm="API Documentation"'},
    )
