from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import create_course_access_token
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.api_response import ApiResponse, success_response
from app.schemas.auth import SessionStatusResponse, SignInRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post("/signup", response_model=ApiResponse[bool])
def signup(payload: SignInRequest, db: Session = Depends(get_db)):
    response_ok = auth_service.signup(db, payload.email)
    return success_response(data=response_ok, message="Đăng ký thành công")


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login_alias(payload: SignInRequest, db: Session = Depends(get_db)):
    token, user, session_id = auth_service.signin(db, payload.email)
    expires_at = user.course_access_period_expires_at
    has_active_course_access = bool(
        user.course_access_active
        and expires_at is not None
        and (
            (expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at.astimezone(timezone.utc))
            > datetime.now(timezone.utc)
        )
    )
    course_access_token = (
        create_course_access_token(
            subject=user.id,
            email=user.email,
            course_access_version=user.course_access_version,
            expires_at=expires_at,
            session_id=session_id,
        )
        if has_active_course_access
        else None
    )
    if course_access_token is None:
        logger.info(
            "login_without_course_token user_id=%s active=%s expires_at=%s now_utc=%s",
            user.id,
            user.course_access_active,
            expires_at.isoformat() if expires_at is not None else None,
            datetime.now(timezone.utc).isoformat(),
        )
    response_data = TokenResponse(
        access_token=token,
        course_access_token=course_access_token,
        role=user.role_name,
        email=user.email,
    )
    return success_response(data=response_data, message="Đăng nhập thành công")


@router.get("/session-status", response_model=ApiResponse[SessionStatusResponse])
def session_status(current_user: User = Depends(get_current_user)):
    expires_at = current_user.course_access_period_expires_at
    expires_at_utc = (
        expires_at.replace(tzinfo=timezone.utc) if expires_at is not None and expires_at.tzinfo is None else expires_at
    )
    response_data = SessionStatusResponse(
        user_id=current_user.id,
        email=current_user.email,
        role=current_user.role_name,
        is_active=current_user.is_active,
        course_access_active=bool(
            current_user.course_access_active
            and expires_at_utc is not None
            and expires_at_utc > datetime.now(timezone.utc)
        ),
        course_access_expires_at=expires_at,
    )
    return success_response(data=response_data, message="Phiên đăng nhập hợp lệ")
