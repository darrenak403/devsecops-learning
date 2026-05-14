from pydantic import BaseModel, Field


class OTPVerifyRequest(BaseModel):
    otp: str = Field(min_length=6, max_length=32)


class ExternalOTPVerifyRequest(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    otp: str = Field(min_length=6, max_length=32)


class OTPGenerateResponse(BaseModel):
    otp: str
    expires_in: int | None = None
    version: int
    target_email: str


class OTPVerifyResponse(BaseModel):
    valid: bool
    message: str
    next_otp_expires_in: int | None = None
    token: str | None = None


class CourseAccessStatusResponse(BaseModel):
    active: bool
    user_id: str
    email: str
