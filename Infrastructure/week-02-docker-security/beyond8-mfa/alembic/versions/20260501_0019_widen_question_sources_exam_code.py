"""widen question_sources.exam_code to VARCHAR(255)

Revision ID: 20260501_0019
Revises: 20260501_0018
Create Date: 2026-05-01 15:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260501_0019"
down_revision = "20260501_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE question_sources ALTER COLUMN exam_code TYPE VARCHAR(255)")


def downgrade() -> None:
    op.execute("ALTER TABLE question_sources ALTER COLUMN exam_code TYPE VARCHAR(64)")
