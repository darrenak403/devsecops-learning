from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin, get_current_course_user, get_current_user
from app.core.security import create_course_access_token
from app.crud import crud_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.api_response import ApiResponse, success_response
from app.schemas.otp import CourseAccessStatusResponse, ExternalOTPVerifyRequest, OTPGenerateResponse, OTPVerifyResponse
from app.services import auth_service, otp_service

router = APIRouter(prefix="/otp", tags=["OTP"])


@router.get("/generate", response_model=ApiResponse[OTPGenerateResponse])
def generate_otp(
    target_email: str = Query(min_length=3, max_length=255),
    _admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Generate OTP for one target user.
    Each user has an independent OTP sequence.
    """
    target_user = auth_service.get_user_by_email(db, email=target_email)
    otp, expires_in, version = otp_service.generate_otp(db, target_user_id=target_user.id)
    response_data = OTPGenerateResponse(otp=otp, expires_in=expires_in, version=version, target_email=target_user.email)
    return success_response(data=response_data, message="Lấy OTP thành công")


@router.post("/verify", response_model=ApiResponse[OTPVerifyResponse])
def verify_otp(
    payload: ExternalOTPVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verify OTP submitted by an authenticated user.
    On success: records audit log row + immediately rotates OTP window.
    On failure: no DB writes.
    """
    # Trust authenticated session as source of truth.
    # payload.email is kept for backward-compatible request shape.
    _ = payload.email

    valid, message, next_expires = otp_service.verify_and_rotate(
        db,
        user_id=current_user.id,
        otp_raw=payload.otp,
    )

    issued_user = crud_user.bump_course_access_version(db, user_id=current_user.id) if valid else None
    if valid and issued_user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể cấp course access token do trạng thái người dùng đã thay đổi. Vui lòng thử lại.",
        )

    token = (
        create_course_access_token(
            subject=current_user.id,
            email=current_user.email,
            course_access_version=issued_user.course_access_version if issued_user is not None else current_user.course_access_version,
            expires_at=issued_user.course_access_period_expires_at if issued_user is not None else None,
            session_id=current_user.active_session_id,
        )
        if valid
        else None
    )
    response_data = OTPVerifyResponse(valid=valid, message=message, next_otp_expires_in=next_expires, token=token)
    return success_response(data=response_data, message="Xác minh OTP thành công" if valid else message)


@router.get("/course-access/status", response_model=ApiResponse[CourseAccessStatusResponse])
def course_access_status(current_user: User = Depends(get_current_course_user)):
    response_data = CourseAccessStatusResponse(
        active=True,
        user_id=current_user.id,
        email=current_user.email,
    )
    return success_response(data=response_data, message="Course access token hợp lệ")
