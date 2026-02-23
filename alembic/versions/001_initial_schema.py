"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-02-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_pages', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    
    # Create sections table
    op.create_table(
        'sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('section_number', sa.String(length=50), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sections_id'), 'sections', ['id'], unique=False)
    
    # Create requirements table
    op.create_table(
        'requirements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('requirement_id', sa.String(length=50), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('type', sa.Enum('Техническое', 'Организационное', 'Документационное', 'Функциональное', 'Нефункциональное', 'Прочее', name='requirementtype'), nullable=True),
        sa.Column('priority', sa.Enum('Обязательно', 'Желательно', 'Опционально', name='requirementpriority'), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('bbox', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('ai_suggested', sa.Text(), nullable=False),
        sa.Column('human_edited', sa.Text(), nullable=True),
        sa.Column('edit_reason', sa.Text(), nullable=True),
        sa.Column('edited_by', sa.String(length=255), nullable=True),
        sa.Column('edited_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_requirements_id'), 'requirements', ['id'], unique=False)
    op.create_index(op.f('ix_requirements_requirement_id'), 'requirements', ['requirement_id'], unique=False)
    op.create_index(op.f('ix_requirements_status'), 'requirements', ['status'], unique=False)
    
    # Create coverage_metrics table
    op.create_table(
        'coverage_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('total_pages', sa.Integer(), nullable=False),
        sa.Column('processed_pages', sa.Integer(), nullable=False),
        sa.Column('skipped_pages', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('coverage_percent', sa.Float(), nullable=False),
        sa.Column('requirements_count', sa.Integer(), nullable=False),
        sa.Column('requirements_by_type', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id')
    )
    op.create_index(op.f('ix_coverage_metrics_id'), 'coverage_metrics', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_coverage_metrics_id'), table_name='coverage_metrics')
    op.drop_table('coverage_metrics')
    op.drop_index(op.f('ix_requirements_status'), table_name='requirements')
    op.drop_index(op.f('ix_requirements_requirement_id'), table_name='requirements')
    op.drop_index(op.f('ix_requirements_id'), table_name='requirements')
    op.drop_table('requirements')
    op.drop_index(op.f('ix_sections_id'), table_name='sections')
    op.drop_table('sections')
    op.drop_index(op.f('ix_documents_id'), table_name='documents')
    op.drop_table('documents')
    op.execute('DROP TYPE IF EXISTS requirementpriority')
    op.execute('DROP TYPE IF EXISTS requirementtype')
