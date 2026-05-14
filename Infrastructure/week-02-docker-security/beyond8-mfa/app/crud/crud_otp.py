"""CRUD helpers for per-user stateless OTP."""

from datetime import datetime, timezone

from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from app.models.otp_verification import OTPVerification
from app.models.user import User


class CRUDOTP:
    def ensure_otp_verification_columns(self, db: Session) -> None:
        db.execute(text("ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS otp_rotate_count INTEGER"))

    # ------------------------------------------------------------------
    # Per-user rotation helpers
    # ------------------------------------------------------------------

    def get_user_rotate_count(self, db: Session, user_id: str) -> int:
        stmt = select(User.otp_rotate_count).where(User.id == user_id).limit(1)
        current = db.execute(stmt).scalar_one_or_none()
        if current is None:
            raise ValueError("User not found")
        return int(current)

    def get_user_rotate_count_for_update(self, db: Session, user_id: str) -> int:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .with_for_update(of=User)
            .limit(1)
        )
        user = db.execute(stmt).scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")
        return int(user.otp_rotate_count)

    def increment_user_rotate_count(self, db: Session, user_id: str) -> int:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .with_for_update(of=User)
            .limit(1)
        )
        user = db.execute(stmt).scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        user.otp_rotate_count = int(user.otp_rotate_count or 0) + 1
        db.add(user)
        db.flush()
        return int(user.otp_rotate_count)

    def save_last_generated_otp(self, db: Session, user_id: str, otp_value: str) -> None:
        stmt = select(User).where(User.id == user_id).limit(1)
        user = db.execute(stmt).scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")
        user.last_generated_otp = otp_value
        db.add(user)
        db.flush()

    def is_counter_used(self, db: Session, user_id: str, otp_rotate_count: int) -> bool:
        stmt = (
            select(OTPVerification)
            .where(OTPVerification.user_id == user_id, OTPVerification.otp_rotate_count == otp_rotate_count)
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none() is not None

    def record_verification(
        self,
        db: Session,
        user_id: str,
        window_id: int,
        otp_rotate_count: int,
    ) -> OTPVerification:
        record = OTPVerification(
            user_id=user_id,
            window_id=window_id,
            otp_rotate_count=otp_rotate_count,
            created_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.flush()
        return record

    # ------------------------------------------------------------------
    # Cooldown helper (per-user rate limiting)
    # ------------------------------------------------------------------

    def get_latest_user_verification(self, db: Session, user_id: str) -> OTPVerification | None:
        stmt = (
            select(OTPVerification)
            .where(OTPVerification.user_id == user_id)
            .order_by(desc(OTPVerification.created_at))
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()


crud_otp = CRUDOTP()
