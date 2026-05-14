"""add roles table and convert users role to role_id

Revision ID: 20260411_0002
Revises: 20260411_0001
Create Date: 2026-04-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260411_0002"
down_revision = "20260411_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.execute(
        """
        INSERT INTO roles (id, name)
        VALUES
          ('00000000-0000-0000-0000-000000000001', 'admin'),
          ('00000000-0000-0000-0000-000000000002', 'user')
        ON CONFLICT (name) DO NOTHING
        """
    )

    op.add_column("users", sa.Column("role_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_users_role_id", "users", "roles", ["role_id"], ["id"])
    op.create_index("ix_users_role_id", "users", ["role_id"], unique=False)

    op.execute(
        """
        UPDATE users
        SET role_id = CASE
          WHEN role = 'admin' THEN '00000000-0000-0000-0000-000000000001'
          ELSE '00000000-0000-0000-0000-000000000002'
        END
        """
    )

    op.alter_column("users", "role_id", nullable=False)
    op.drop_column("users", "role")


def downgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=32), nullable=False, server_default="user"))

    op.execute(
        """
        UPDATE users
        SET role = CASE
          WHEN role_id = '00000000-0000-0000-0000-000000000001' THEN 'admin'
          ELSE 'user'
        END
        """
    )

    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_constraint("fk_users_role_id", "users", type_="foreignkey")
    op.drop_column("users", "role_id")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
