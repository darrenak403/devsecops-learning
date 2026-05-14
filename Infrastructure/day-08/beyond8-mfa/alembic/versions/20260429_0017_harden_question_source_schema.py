"""harden question source schema and indexes

Revision ID: 20260429_0017
Revises: 20260426_0016
Create Date: 2026-04-29 10:55:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260429_0017"
down_revision = "20260426_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id VARCHAR(36) PRIMARY KEY,
            slug VARCHAR(64) UNIQUE NOT NULL,
            code VARCHAR(32) UNIQUE NOT NULL,
            name VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS question_sources (
            id VARCHAR(36) PRIMARY KEY,
            subject_id VARCHAR(36) NOT NULL REFERENCES subjects(id),
            exam_code VARCHAR(64) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            checksum_sha256 VARCHAR(71) NOT NULL,
            raw_storage_key VARCHAR(255),
            uploaded_by VARCHAR(255),
            uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            parse_status VARCHAR(16) NOT NULL,
            parse_warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
            question_count INTEGER NOT NULL DEFAULT 0,
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            deleted_reason TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id VARCHAR(36) PRIMARY KEY,
            source_id VARCHAR(36) NOT NULL REFERENCES question_sources(id),
            ordinal INTEGER NOT NULL,
            stem TEXT NOT NULL,
            options_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            answers_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            answer_text TEXT NOT NULL,
            image_url TEXT,
            normalized_hash VARCHAR(71) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS question_source_user_stats (
            id VARCHAR(36) PRIMARY KEY,
            source_id VARCHAR(36) NOT NULL REFERENCES question_sources(id) ON DELETE CASCADE,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            in_progress_count INTEGER NOT NULL DEFAULT 0,
            completed_count INTEGER NOT NULL DEFAULT 0,
            current_question_ordinal INTEGER NOT NULL DEFAULT 0,
            attempted_question_ordinals JSONB NOT NULL DEFAULT '[]'::jsonb,
            completed_attempts INTEGER NOT NULL DEFAULT 0,
            completion_rate_percent INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(source_id, user_id)
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_question_sources_subject_exam_checksum ON question_sources(subject_id, exam_code, checksum_sha256)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_questions_source_id ON questions(source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_questions_normalized_hash ON questions(normalized_hash)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_questions_source_ordinal ON questions(source_id, ordinal)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_question_source_user_stats_user_id ON question_source_user_stats(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_question_source_user_stats_source_id ON question_source_user_stats(source_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_question_sources_subject_status_deleted_uploaded "
        "ON question_sources(subject_id, parse_status, is_deleted, uploaded_at DESC, id DESC)"
    )
    op.execute("ALTER TABLE question_source_user_stats ADD COLUMN IF NOT EXISTS current_question_ordinal INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE question_source_user_stats ADD COLUMN IF NOT EXISTS attempted_question_ordinals JSONB NOT NULL DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE question_source_user_stats ADD COLUMN IF NOT EXISTS completed_attempts INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS image_url TEXT")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_question_sources_subject_status_deleted_uploaded")
