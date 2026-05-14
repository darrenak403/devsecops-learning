"""add image_url column to questions

Revision ID: 20260426_0016
Revises: 20260425_0015
Create Date: 2026-04-26
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260426_0016"
down_revision = "20260425_0015"
branch_labels = None
depends_on = None


def _questions_table_exists(connection) -> bool:
    return inspect(connection).has_table("questions")


def upgrade() -> None:
    connection = op.get_bind()
    if not _questions_table_exists(connection):
        return
    op.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS image_url TEXT")


def downgrade() -> None:
    connection = op.get_bind()
    if not _questions_table_exists(connection):
        return
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS image_url")
