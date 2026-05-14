"""add course access active fields

Revision ID: 20260411_0010
Revises: 20260411_0009
Create Date: 2026-04-11
"""

from alembic import op

revision = "20260411_0010"
down_revision = "20260411_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_active BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_verified_at TIMESTAMPTZ")
    op.execute(
        """
        UPDATE users
        SET course_access_active = TRUE
        WHERE course_access_active = FALSE
          AND COALESCE(course_access_version, 0) > 0
          AND course_access_revoked_at IS NULL
          AND is_active = TRUE
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS course_access_verified_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS course_access_active")
