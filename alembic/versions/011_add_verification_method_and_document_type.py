"""Add verification_method to requirements and document_type to documents

Revision ID: 011_add_verification_document_type
Revises: 010_add_parent_id
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa


revision = '011_add_verification_document_type'
down_revision = '010_add_parent_id'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Widen alembic_version.version_num to fit long revision IDs (VARCHAR(32) is too short)
    conn.execute(sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)"))
    # Idempotent: add columns only if they don't exist (handles partial runs)
    conn.execute(sa.text("ALTER TABLE requirements ADD COLUMN IF NOT EXISTS verification_method VARCHAR(100)"))
    conn.execute(sa.text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type VARCHAR(100)"))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE documents DROP COLUMN IF EXISTS document_type"))
    conn.execute(sa.text("ALTER TABLE requirements DROP COLUMN IF EXISTS verification_method"))
