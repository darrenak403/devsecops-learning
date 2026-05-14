"""seed default admin user

Revision ID: 20260411_0003
Revises: 20260411_0002
Create Date: 2026-04-11
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260411_0003"
down_revision = "20260411_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO users (id, email, role_id, is_active, created_at, updated_at)
        SELECT
          '11111111-1111-1111-1111-111111111111',
          'admin@gmail.com',
          roles.id,
          true,
          now(),
          now()
        FROM roles
        WHERE roles.name = 'admin'
        ON CONFLICT (email)
        DO UPDATE SET
          role_id = EXCLUDED.role_id,
          is_active = true,
          updated_at = now()
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email = 'admin@gmail.com'")
