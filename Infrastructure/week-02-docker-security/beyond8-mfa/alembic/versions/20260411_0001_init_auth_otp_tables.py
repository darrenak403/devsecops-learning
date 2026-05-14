"""init auth otp tables

Revision ID: 20260411_0001
Revises:
Create Date: 2026-04-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260411_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="learner"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "otp_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("otp_value", sa.String(length=32), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("otp_hint", sa.String(length=32), nullable=False),
        sa.Column("issued_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_otp_tokens_is_active", "otp_tokens", ["is_active"], unique=False)
    op.create_index("ix_otp_tokens_expires_at", "otp_tokens", ["expires_at"], unique=False)

    op.create_table(
        "otp_verifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("otp_token_id", sa.String(length=36), nullable=False),
        sa.Column("course_key", sa.String(length=100), nullable=False, server_default="default-course"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["otp_token_id"], ["otp_tokens.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("otp_token_id", name="uq_otp_verifications_otp_token_id"),
    )
    op.create_index("ix_otp_verifications_user_id", "otp_verifications", ["user_id"], unique=False)
    op.create_index("ix_otp_verifications_course_key", "otp_verifications", ["course_key"], unique=False)
    op.create_index("ix_otp_verifications_created_at", "otp_verifications", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_otp_verifications_created_at", table_name="otp_verifications")
    op.drop_index("ix_otp_verifications_course_key", table_name="otp_verifications")
    op.drop_index("ix_otp_verifications_user_id", table_name="otp_verifications")
    op.drop_table("otp_verifications")

    op.drop_index("ix_otp_tokens_expires_at", table_name="otp_tokens")
    op.drop_index("ix_otp_tokens_is_active", table_name="otp_tokens")
    op.drop_table("otp_tokens")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
