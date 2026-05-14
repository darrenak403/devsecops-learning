"""add user block fields

Revision ID: 20260411_0006
Revises: 20260411_0005
Create Date: 2026-04-11
"""

from alembic import op
import sqlalchemy as sa

revision = "20260411_0006"
down_revision = "20260411_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_reason VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_by_user_id VARCHAR(36)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_blocked_by_user_id ON users (blocked_by_user_id)")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_users_blocked_by_user_id_users'
            ) THEN
                ALTER TABLE users
                ADD CONSTRAINT fk_users_blocked_by_user_id_users
                FOREIGN KEY (blocked_by_user_id) REFERENCES users (id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_blocked_by_user_id_users")
    op.execute("DROP INDEX IF EXISTS ix_users_blocked_by_user_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS blocked_by_user_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS blocked_reason")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS blocked_at")
