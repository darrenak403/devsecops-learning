"""drop course_key from otp_verifications

Revision ID: 20260411_0004
Revises: 20260411_0003
Create Date: 2026-04-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260411_0004"
down_revision = "20260411_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_otp_verifications_course_key", table_name="otp_verifications")
    op.drop_column("otp_verifications", "course_key")


def downgrade() -> None:
    op.add_column(
        "otp_verifications",
        sa.Column("course_key", sa.String(length=100), nullable=False, server_default="default-course"),
    )
    op.create_index("ix_otp_verifications_course_key", "otp_verifications", ["course_key"], unique=False)
