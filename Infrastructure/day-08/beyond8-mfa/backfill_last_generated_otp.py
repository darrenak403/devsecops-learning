"""Backfill last_generated_otp for all existing users."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.security import generate_otp_for_user_window
from app.db.session import SessionLocal
from app.models.user import User
from sqlalchemy import select


def main() -> None:
    db = SessionLocal()
    try:
        users = db.execute(select(User)).scalars().all()
        updated = 0
        for user in users:
            otp = generate_otp_for_user_window(
                user_id=user.id,
                otp_rotate_count=user.otp_rotate_count,
            )
            user.last_generated_otp = otp
            db.add(user)
            updated += 1
            print(f"  {user.email}: rotate_count={user.otp_rotate_count} -> {otp}")

        db.commit()
        print(f"\nBackfill hoàn tất: {updated} users đã được cập nhật.")
    except Exception as exc:
        db.rollback()
        print(f"Lỗi: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
