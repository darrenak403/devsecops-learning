"""add per-user otp counter fields

Revision ID: 20260412_0012
Revises: 20260411_0011
Create Date: 2026-04-12
"""

from alembic import op

revision = "20260412_0012"
down_revision = "20260411_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_rotate_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS otp_rotate_count INTEGER")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_otp_verifications_user_id_rotate_count ON otp_verifications (user_id, otp_rotate_count)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_otp_verifications_user_id_rotate_count")
    op.execute("ALTER TABLE otp_verifications DROP COLUMN IF EXISTS otp_rotate_count")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS otp_rotate_count")
