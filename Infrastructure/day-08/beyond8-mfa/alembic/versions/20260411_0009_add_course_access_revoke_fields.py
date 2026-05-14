"""add course access revoke fields

Revision ID: 20260411_0009
Revises: 20260411_0008
Create Date: 2026-04-11
"""

from alembic import op

revision = "20260411_0009"
down_revision = "20260411_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_version INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_revoked_at TIMESTAMPTZ")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_course_access_revoked_at ON users (course_access_revoked_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_course_access_revoked_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS course_access_revoked_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS course_access_version")
