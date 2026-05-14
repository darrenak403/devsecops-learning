import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt

from app.core.config import settings

SAFE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_access_token(subject: str, role: str, email: str, session_id: str) -> str:
    issued_at = datetime.now(timezone.utc)
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "email": email,
        "iat": int(issued_at.timestamp()),
        "exp": expire,
    }
    payload["sid"] = session_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_course_access_token(
    subject: str,
    email: str,
    course_access_version: int = 0,
    expires_at: datetime | None = None,
    session_id: str | None = None,
) -> str:
    issued_at = datetime.now(timezone.utc)
    expire = expires_at if expires_at is not None else (datetime.now(timezone.utc) + timedelta(days=settings.course_access_token_expire_days))
    if expire.tzinfo is None:
        expire = expire.replace(tzinfo=timezone.utc)
    else:
        expire = expire.astimezone(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "email": email,
        "role": "course_viewer",
        "iat": int(issued_at.timestamp()),
        "cav": int(course_access_version),
        "course_access_ttl_days": settings.course_access_token_expire_days,
        "course_access_expires_at": int(expire.timestamp()),
        "exp": expire,
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def is_course_access_payload_active(
    payload: Dict[str, Any],
    *,
    expected_course_access_active: bool,
    expected_course_access_version: int,
    revoked_at: datetime | None,
) -> bool:
    if not expected_course_access_active:
        return False

    token_version = int(payload.get("cav", 0))
    if token_version != int(expected_course_access_version):
        return False

    if revoked_at is None:
        return True

    token_iat = payload.get("iat")
    if token_iat is None:
        return False
    try:
        token_iat_int = int(token_iat)
    except (TypeError, ValueError):
        return False

    revoked_ts = int(revoked_at.timestamp())
    return token_iat_int > revoked_ts


# ---------------------------------------------------------------------------
# Stateless HMAC OTP helpers
# ---------------------------------------------------------------------------


def _otp_raw_from_digest(digest_hex: str) -> str:
    """
    Map 12 hex nibbles (first 48 bits of HMAC) to safe-character OTP string.
    Format: <PREFIX>-XXXX-XXXX-XXXX  (same style as before)
    """
    # Use first 12 hex chars → 6 bytes → convert each nibble to SAFE_CHARS index
    nibbles = [int(c, 16) for c in digest_hex[:12]]
    # Each nibble is 0-15; SAFE_CHARS has 31 chars — map uniformly
    chars = "".join(SAFE_CHARS[n % len(SAFE_CHARS)] for n in nibbles)
    return f"{settings.key_prefix}-{chars[0:4]}-{chars[4:8]}-{chars[8:12]}"


def generate_otp_for_user_window(user_id: str, otp_rotate_count: int, window_id: int | None = None) -> str:
    """Deterministically generate OTP bound to a specific user and counter."""
    message = f"otp:{user_id}:{otp_rotate_count}".encode()
    digest = hmac.new(settings.jwt_secret_key.encode(), message, hashlib.sha256).hexdigest()
    return _otp_raw_from_digest(digest)


def verify_otp_for_user_window(
    otp_raw: str,
    user_id: str,
    otp_rotate_count: int,
    window_id: int | None = None,
) -> bool:
    expected = generate_otp_for_user_window(
        user_id=user_id,
        otp_rotate_count=otp_rotate_count,
        window_id=window_id,
    )
    return hmac.compare_digest(
        otp_raw.strip().upper(),
        expected.strip().upper(),
    )
