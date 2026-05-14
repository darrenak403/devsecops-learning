from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.otp_verification import OTPVerification
from app.models.user import User
from app.schemas.stats import OTPVerificationHistoryItem


class StatsService:
    def get_otp_verification_stats(self, db: Session) -> tuple[int, int, int]:
        verified_users_stmt = select(func.count(User.id)).where(User.course_access_purchase_count > 0)
        total_key_purchases_stmt = select(func.coalesce(func.sum(User.course_access_purchase_count), 0))
        total_success_stmt = select(func.count(OTPVerification.id))

        verified_users = db.execute(verified_users_stmt).scalar_one()
        total_key_purchases = db.execute(total_key_purchases_stmt).scalar_one()
        total_success = db.execute(total_success_stmt).scalar_one()

        return int(verified_users or 0), int(total_key_purchases or 0), int(total_success or 0)

    def get_otp_verification_history(
        self,
        db: Session,
        *,
        user_id: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[int, list[OTPVerificationHistoryItem]]:
        stmt = (
            select(
                OTPVerification.user_id,
                User.email,
                func.count(OTPVerification.id).label("verification_count"),
                func.max(OTPVerification.created_at).label("last_verified_at"),
            )
            .join(User, User.id == OTPVerification.user_id)
            .group_by(OTPVerification.user_id, User.email)
            .order_by(func.max(OTPVerification.created_at).desc())
        )

        if user_id:
            stmt = stmt.where(OTPVerification.user_id == user_id)

        count_stmt = (
            select(func.count(func.distinct(OTPVerification.user_id)))
            .select_from(OTPVerification)
            .join(User, User.id == OTPVerification.user_id)
        )
        if user_id:
            count_stmt = count_stmt.where(OTPVerification.user_id == user_id)

        total_users = int(db.execute(count_stmt).scalar_one() or 0)
        offset = (page - 1) * limit
        rows = db.execute(stmt.offset(max(0, offset)).limit(limit)).all()
        items = [
            OTPVerificationHistoryItem(
                user_id=str(row.user_id),
                email=row.email,
                verification_count=int(row.verification_count or 0),
                last_verified_at=row.last_verified_at,
            )
            for row in rows
        ]
        return total_users, items

    async def get_otp_verification_history_async(
        self,
        db: AsyncSession,
        *,
        user_id: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[int, list[OTPVerificationHistoryItem]]:
        stmt = (
            select(
                OTPVerification.user_id,
                User.email,
                func.count(OTPVerification.id).label("verification_count"),
                func.max(OTPVerification.created_at).label("last_verified_at"),
            )
            .join(User, User.id == OTPVerification.user_id)
            .group_by(OTPVerification.user_id, User.email)
            .order_by(func.max(OTPVerification.created_at).desc())
        )
        if user_id:
            stmt = stmt.where(OTPVerification.user_id == user_id)

        count_stmt = (
            select(func.count(func.distinct(OTPVerification.user_id)))
            .select_from(OTPVerification)
            .join(User, User.id == OTPVerification.user_id)
        )
        if user_id:
            count_stmt = count_stmt.where(OTPVerification.user_id == user_id)

        total_users = int((await db.execute(count_stmt)).scalar_one() or 0)
        offset = (page - 1) * limit
        rows = (await db.execute(stmt.offset(max(0, offset)).limit(limit))).all()
        return total_users, [
            OTPVerificationHistoryItem(
                user_id=str(row.user_id),
                email=row.email,
                verification_count=int(row.verification_count or 0),
                last_verified_at=row.last_verified_at,
            )
            for row in rows
        ]


stats_service = StatsService()
