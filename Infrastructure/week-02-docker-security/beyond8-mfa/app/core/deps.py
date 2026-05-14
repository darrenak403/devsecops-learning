from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token, is_course_access_payload_active
from app.crud import crud_user
from app.db.session import get_db
from app.models.user import User

auth_bearer_scheme = HTTPBearer(auto_error=False, scheme_name="auth-token")
course_access_header_scheme = APIKeyHeader(
    name="x-course-access-token",
    auto_error=False,
    scheme_name="beyond8-course-access",
)
_AUTH_TOKEN_COOKIE_CANDIDATES = ("auth_token",)
_COURSE_ACCESS_COOKIE_CANDIDATES = ("beyond8_course_access",)


def _is_seed_admin_email(user: User) -> bool:
    """Bootstrap admin may log in from multiple devices; skip single-session enforcement."""
    expected = (settings.seed_admin_email or "").strip().lower()
    if not expected:
        return False
    raw = getattr(user, "email", None) or ""
    return raw.strip().lower() == expected


def _extract_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
    *,
    detail: str,
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )
    return credentials.credentials


def _extract_cookie_or_bearer_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    *,
    cookie_names: tuple[str, ...],
    detail: str,
) -> str:
    # Prefer explicit Bearer header first.
    # This avoids stale/invalid auth cookie shadowing a valid Authorization header
    # when clients call cross-origin session-status right after login.
    if credentials is not None and credentials.scheme.lower() == "bearer" and credentials.credentials:
        return credentials.credentials

    for cookie_name in cookie_names:
        cookie_token = request.cookies.get(cookie_name)
        if cookie_token:
            return cookie_token
    return _extract_bearer_token(credentials, detail=detail)


def _extract_course_access_token(
    request: Request,
    header_token: str | None,
    *,
    detail: str,
) -> str:
    for cookie_name in _COURSE_ACCESS_COOKIE_CANDIDATES:
        cookie_token = request.cookies.get(cookie_name)
        if cookie_token:
            return cookie_token
    if header_token:
        return header_token
    # Backward-compatible fallback for clients still sending course token as Bearer.
    authorization = request.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        maybe_token = authorization[7:].strip()
        if maybe_token:
            return maybe_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(auth_bearer_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    token = _extract_cookie_or_bearer_token(
        request,
        credentials,
        cookie_names=_AUTH_TOKEN_COOKIE_CANDIDATES,
        detail=credentials_exception.detail,
    )
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        session_id: str | None = payload.get("sid")
        # Keep auth/session token separate from course-access token.
        # course_viewer token must only be accepted by get_current_course_user.
        if user_id is None or role == "course_viewer" or not session_id:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = crud_user.get_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa",
        )
    if not _is_seed_admin_email(user):
        if not user.active_session_id or user.active_session_id != session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên đăng nhập không còn hợp lệ.",
            )

    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role_name != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user


def get_current_course_user(
    request: Request,
    db: Session = Depends(get_db),
    course_access_token: str | None = Depends(course_access_header_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked course access token",
    )
    token = _extract_course_access_token(
        request,
        course_access_token,
        detail=credentials_exception.detail,
    )
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        session_id: str | None = payload.get("sid")
        if user_id is None or role != "course_viewer":
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = crud_user.get_by_id(db, user_id)
    # Collapse user-not-found and inactive into one 401 response.
    if user is None or not user.is_active:
        raise credentials_exception

    if not is_course_access_payload_active(
        payload,
        expected_course_access_active=user.course_access_active,
        expected_course_access_version=user.course_access_version,
        revoked_at=user.course_access_revoked_at,
    ):
        raise credentials_exception
    if (
        session_id
        and not _is_seed_admin_email(user)
        and (not user.active_session_id or session_id != user.active_session_id)
    ):
        raise credentials_exception

    return user


def require_course_access(
    current_user: User = Depends(get_current_user),
    course_user: User = Depends(get_current_course_user),
) -> User:
    if course_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked course access token",
        )
    return current_user
