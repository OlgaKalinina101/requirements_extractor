"""Add missing FK indexes for performance

Revision ID: 005_add_indexes
Revises: 004_add_subitems
Create Date: 2026-03-06 21:00:00

"""
from alembic import op


revision = '005_add_indexes'
down_revision = '004_add_subitems'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_requirements_document_id', 'requirements', ['document_id'])
    op.create_index('ix_requirements_section_id', 'requirements', ['section_id'])
    op.create_index('ix_documents_project_id', 'documents', ['project_id'])
    op.create_index('ix_sections_document_id', 'sections', ['document_id'])


def downgrade():
    op.drop_index('ix_requirements_document_id', table_name='requirements')
    op.drop_index('ix_requirements_section_id', table_name='requirements')
    op.drop_index('ix_documents_project_id', table_name='documents')
    op.drop_index('ix_sections_document_id', table_name='sections')
