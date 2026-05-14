"""stateless otp refactor

Revision ID: 20260411_0005
Revises: 20260411_0004
Create Date: 2026-04-11

Changes:
- Drop otp_verifications (old schema with otp_token_id FK)
- Drop otp_tokens table (no longer needed — OTP is stateless HMAC)
- Create otp_state table (singleton: persist rotate_count)
- Create otp_verifications table (new schema: window_id instead of otp_token_id)
"""

from alembic import op
import sqlalchemy as sa

revision = "20260411_0005"
down_revision = "20260411_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw DDL with IF EXISTS to safely handle any index/table state
    # (PostgreSQL requires this to avoid aborting the transaction on missing objects)

    # 1. Drop old otp_verifications (has FK → otp_tokens)
    op.execute("DROP TABLE IF EXISTS otp_verifications CASCADE")

    # 2. Drop otp_tokens (no longer needed — OTP is now stateless HMAC)
    op.execute("DROP TABLE IF EXISTS otp_tokens CASCADE")

    # 3. Create singleton otp_state table
    op.create_table(
        "otp_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rotate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Seed the one-and-only row
    op.execute("INSERT INTO otp_state (id, rotate_count, updated_at) VALUES (1, 0, NOW())")

    # 4. Re-create otp_verifications with new schema
    op.create_table(
        "otp_verifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("window_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("window_id", name="uq_otp_verifications_window_id"),
    )
    op.create_index("ix_otp_verifications_user_id", "otp_verifications", ["user_id"], unique=False)
    op.create_index("ix_otp_verifications_window_id", "otp_verifications", ["window_id"], unique=True)
    op.create_index("ix_otp_verifications_created_at", "otp_verifications", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_otp_verifications_created_at", table_name="otp_verifications")
    op.drop_index("ix_otp_verifications_window_id", table_name="otp_verifications")
    op.drop_index("ix_otp_verifications_user_id", table_name="otp_verifications")
    op.drop_table("otp_verifications")
    op.drop_table("otp_state")

    # Recreate otp_tokens
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

    # Recreate old otp_verifications
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
