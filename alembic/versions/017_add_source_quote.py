"""Add source_quote column to requirements table

Revision ID: 017_add_source_quote
Revises: 016_add_document_pages
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa

revision = '017_add_source_quote'
down_revision = '016_add_document_pages'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'requirements',
        sa.Column('source_quote', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column('requirements', 'source_quote')
