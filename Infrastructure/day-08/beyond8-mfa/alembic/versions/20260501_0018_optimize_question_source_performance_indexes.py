"""add composite indexes for question source performance

Revision ID: 20260501_0018
Revises: 20260429_0017
Create Date: 2026-05-01 00:25:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260501_0018"
down_revision = "20260429_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_subject_sources_active "
        "ON question_sources(subject_id, is_deleted, parse_status, uploaded_at DESC, id DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_questions_source_ordinal "
        "ON questions(source_id, ordinal)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_stats_source_user "
        "ON question_source_user_stats(source_id, user_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_user_stats_source_user")
    op.execute("DROP INDEX IF EXISTS idx_questions_source_ordinal")
    op.execute("DROP INDEX IF EXISTS idx_subject_sources_active")
