"""Add document_pages table for per-page text and bounding boxes

Revision ID: 016_add_document_pages
Revises: 015_prompts_table
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '016_add_document_pages'
down_revision = '015_prompts_table'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS document_pages (
            id          SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            page_number INTEGER NOT NULL,
            raw_text    TEXT,
            text_blocks JSONB,
            is_ocr      BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_document_pages_document_id
            ON document_pages (document_id)
    """))
    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_document_pages_doc_page
            ON document_pages (document_id, page_number)
    """))


def downgrade():
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS document_pages"))
