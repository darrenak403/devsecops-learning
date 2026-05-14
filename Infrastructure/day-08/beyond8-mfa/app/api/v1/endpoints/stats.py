from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.helpers.stats_helpers import build_otp_history_response, build_otp_stats_response
from app.core.deps import get_current_admin
from app.db.session import get_db
from app.schemas.api_response import ApiResponse
from app.schemas.stats import OTPStatsResponse, OTPVerificationHistoryResponse

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/otp-verifications", response_model=ApiResponse[OTPStatsResponse])
def otp_verification_stats(_=Depends(get_current_admin), db: Session = Depends(get_db)):
    return build_otp_stats_response(db)


@router.get("/otp-verifications/history", response_model=ApiResponse[OTPVerificationHistoryResponse])
def otp_verification_history(
    _=Depends(get_current_admin),
    db: Session = Depends(get_db),
    user_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return build_otp_history_response(db, user_id=user_id, page=page, limit=limit)
