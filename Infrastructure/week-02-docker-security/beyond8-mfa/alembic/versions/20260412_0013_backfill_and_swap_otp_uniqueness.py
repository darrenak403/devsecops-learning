"""backfill and swap otp uniqueness to per-user

Revision ID: 20260412_0013
Revises: 20260412_0012
Create Date: 2026-04-12
"""

from alembic import op

revision = "20260412_0013"
down_revision = "20260412_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at ASC, id ASC) - 1 AS seq
            FROM otp_verifications
        )
        UPDATE otp_verifications ov
        SET otp_rotate_count = ranked.seq
        FROM ranked
        WHERE ov.id = ranked.id
        """
    )

    op.execute(
        """
        UPDATE users u
        SET otp_rotate_count = COALESCE(v.next_counter, 0)
        FROM (
            SELECT user_id, MAX(otp_rotate_count) + 1 AS next_counter
            FROM otp_verifications
            GROUP BY user_id
        ) v
        WHERE u.id = v.user_id
        """
    )

    op.execute("ALTER TABLE otp_verifications ALTER COLUMN otp_rotate_count SET NOT NULL")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_otp_verifications_user_counter ON otp_verifications (user_id, otp_rotate_count)"
    )

    op.execute("DROP INDEX IF EXISTS ix_otp_verifications_window_id")
    op.execute("ALTER TABLE otp_verifications DROP CONSTRAINT IF EXISTS uq_otp_verifications_window_id")
    op.execute("CREATE INDEX IF NOT EXISTS ix_otp_verifications_window_id ON otp_verifications (window_id)")


def downgrade() -> None:
    raise RuntimeError("Irreversible migration: per-user OTP allows duplicate window_id across users")
