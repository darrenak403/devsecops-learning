from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from app.schemas.stats import OTPVerificationHistoryItem


class SignInRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    course_access_token: str | None = None
    token_type: str = "bearer"
    role: str
    email: EmailStr


class SessionStatusResponse(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    is_active: bool
    course_access_active: bool = False
    course_access_expires_at: datetime | None = None


class UserItemResponse(BaseModel):
    id: str
    # str (not EmailStr) so admin list/detail do not 500 on legacy or odd stored emails
    email: str
    role: str
    is_active: bool
    course_access_active: bool = False
    course_access_version: int = 0
    course_access_verified_at: datetime | None = None
    course_access_revoked_at: datetime | None = None
    blocked_at: datetime | None = None
    blocked_reason: str | None = None
    blocked_by_user_id: str | None = None
    last_generated_otp: str | None = None
    created_at: datetime


class BlockUserRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class UserListResponse(BaseModel):
    total_users: int
    offset: int
    limit: int
    users: list[UserItemResponse]


class UserDetailResponse(BaseModel):
    user: UserItemResponse
    otp_verification_history: OTPVerificationHistoryItem | None = None
