"""Per-user stateless OTP service."""

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_otp_for_user_window, verify_otp_for_user_window
from app.crud import crud_otp


class OTPService:

    # ------------------------------------------------------------------
    # Generate (no DB write)
    # ------------------------------------------------------------------

    def generate_otp(self, db: Session, target_user_id: str) -> tuple[str, int | None, int]:
        """Return (otp_raw, expires_in_seconds, user_rotate_count)."""
        rotate_count = crud_otp.get_user_rotate_count(db, target_user_id)
        otp_raw = generate_otp_for_user_window(
            user_id=target_user_id,
            otp_rotate_count=rotate_count,
        )
        crud_otp.save_last_generated_otp(db, user_id=target_user_id, otp_value=otp_raw)
        db.flush()
        return otp_raw, None, rotate_count

    # ------------------------------------------------------------------
    # Verify & rotate (DB write only here)
    # ------------------------------------------------------------------

    def verify_and_rotate(
        self,
        db: Session,
        user_id: str,
        otp_raw: str,
        enforce_cooldown: bool = True,
    ) -> tuple[bool, str, int | None]:
        """
        Returns (valid, message, next_expires_in).
        On success:
          - Writes 1 row to otp_verifications (audit log).
          - Increments rotate_count → new OTP window immediately.
        On failure: zero DB writes.
        """
        now = datetime.now(timezone.utc)

        # 1. Per-user cooldown (read-only, outside heavy transaction)
        if enforce_cooldown:
            last = crud_otp.get_latest_user_verification(db, user_id)
            if last is not None:
                verify_time = (
                    last.created_at.replace(tzinfo=timezone.utc)
                    if last.created_at.tzinfo is None
                    else last.created_at
                )
                elapsed = int((now - verify_time).total_seconds())
                if elapsed < settings.otp_refresh_cooldown_seconds:
                    wait_for = settings.otp_refresh_cooldown_seconds - elapsed
                    return False, f"Bạn đã verify gần đây. Vui lòng thử lại sau {wait_for}s.", None

        # 2. One-time-use + verify under user row lock
        try:
            with db.begin_nested():
                rotate_count = crud_otp.get_user_rotate_count_for_update(db, user_id)
                window_id = rotate_count

                if not verify_otp_for_user_window(
                    otp_raw=otp_raw,
                    user_id=user_id,
                    otp_rotate_count=rotate_count,
                ):
                    return False, "OTP không hợp lệ.", None

                if crud_otp.is_counter_used(db, user_id=user_id, otp_rotate_count=rotate_count):
                    return False, "OTP này đã được sử dụng. Vui lòng lấy OTP mới từ admin.", None

                crud_otp.record_verification(
                    db,
                    user_id=user_id,
                    window_id=window_id,
                    otp_rotate_count=rotate_count,
                )
                new_rotate_count = crud_otp.increment_user_rotate_count(db, user_id=user_id)
                new_otp = generate_otp_for_user_window(
                    user_id=user_id,
                    otp_rotate_count=new_rotate_count,
                )
                crud_otp.save_last_generated_otp(db, user_id=user_id, otp_value=new_otp)

        except IntegrityError:
            return False, "OTP này đã được sử dụng. Vui lòng lấy OTP mới từ admin.", None

        return True, "Xác minh thành công. OTP mới đã được kích hoạt tự động.", None


otp_service = OTPService()
