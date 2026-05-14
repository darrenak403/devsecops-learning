"""add active_session_id for single browser session

Revision ID: 20260425_0015
Revises: 20260412_0014
Create Date: 2026-04-25
"""

from alembic import op

revision = "20260425_0015"
down_revision = "20260412_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS active_session_id VARCHAR(36)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_active_session_id ON users (active_session_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_active_session_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS active_session_id")
