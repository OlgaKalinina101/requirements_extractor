"""Add projects table, project_id FK to documents, model_used to documents

Revision ID: 003_add_projects
Revises: 002_remove_enums
Create Date: 2026-02-23 01:30:00

"""
from alembic import op
import sqlalchemy as sa


revision = '003_add_projects'
down_revision = '002_remove_enums'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(100), nullable=True, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_projects_id', 'projects', ['id'])
    op.create_index('ix_projects_code', 'projects', ['code'])

    op.add_column('documents', sa.Column('project_id', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('model_used', sa.String(100), nullable=True))
    op.create_foreign_key(
        'fk_documents_project_id',
        'documents', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    op.drop_constraint('fk_documents_project_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'model_used')
    op.drop_column('documents', 'project_id')
    op.drop_index('ix_projects_code', 'projects')
    op.drop_index('ix_projects_id', 'projects')
    op.drop_table('projects')
