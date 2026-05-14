"""add course access purchase window fields

Revision ID: 20260411_0011
Revises: 20260411_0010
Create Date: 2026-04-11
"""

from datetime import datetime, timedelta, timezone

from alembic import op
from sqlalchemy import text

revision = "20260411_0011"
down_revision = "20260411_0010"
branch_labels = None
depends_on = None


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_period_started_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_period_expires_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_purchase_count INTEGER NOT NULL DEFAULT 0")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_course_access_period_expires_at ON users (course_access_period_expires_at)"
    )

    bind = op.get_bind()
    users = bind.execute(text("SELECT id, course_access_verified_at FROM users")).mappings().all()

    for user in users:
        user_id = user["id"]
        purchase_count = 0
        period_started_at = None
        period_expires_at = None

        verification_times = bind.execute(
            text("SELECT created_at FROM otp_verifications WHERE user_id = :user_id ORDER BY created_at ASC"),
            {"user_id": user_id},
        ).scalars().all()

        for verified_at in verification_times:
            verified_at_utc = _as_utc(verified_at)
            if verified_at_utc is None:
                continue

            if period_expires_at is None or verified_at_utc >= period_expires_at:
                purchase_count += 1
                period_started_at = verified_at_utc
                period_expires_at = verified_at_utc + timedelta(days=30)

        if purchase_count == 0 and user["course_access_verified_at"] is not None:
            fallback_started_at = _as_utc(user["course_access_verified_at"])
            if fallback_started_at is not None:
                purchase_count = 1
                period_started_at = fallback_started_at
                period_expires_at = fallback_started_at + timedelta(days=30)

        bind.execute(
            text(
                """
                UPDATE users
                SET
                    course_access_purchase_count = :purchase_count,
                    course_access_period_started_at = :period_started_at,
                    course_access_period_expires_at = :period_expires_at
                WHERE id = :user_id
                """
            ),
            {
                "user_id": user_id,
                "purchase_count": purchase_count,
                "period_started_at": period_started_at,
                "period_expires_at": period_expires_at,
            },
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_course_access_period_expires_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS course_access_purchase_count")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS course_access_period_expires_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS course_access_period_started_at")
