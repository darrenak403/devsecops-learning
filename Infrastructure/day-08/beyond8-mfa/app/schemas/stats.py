from datetime import datetime

from pydantic import BaseModel


class OTPStatsResponse(BaseModel):
    verified_users: int
    total_key_purchases: int
    total_successful_verifications: int


class OTPVerificationHistoryItem(BaseModel):
    user_id: str
    email: str
    verification_count: int
    last_verified_at: datetime | None = None


class OTPVerificationHistoryResponse(BaseModel):
    total_users: int
    page: int
    limit: int
    total_pages: int
    items: list[OTPVerificationHistoryItem]
