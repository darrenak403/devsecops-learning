"""add last_generated_otp field to users

Revision ID: 20260412_0014
Revises: 20260412_0013
Create Date: 2026-04-12
"""

from alembic import op
import sqlalchemy as sa

revision = "20260412_0014"
down_revision = "20260412_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_generated_otp", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_generated_otp")
