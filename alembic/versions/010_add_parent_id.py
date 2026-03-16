"""Add parent_id to requirements for hierarchy

Revision ID: 010_add_parent_id
Revises: 009_add_discipline_deadline
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa


revision = '010_add_parent_id'
down_revision = '009_add_discipline_deadline'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('requirements', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_requirements_parent_id',
        'requirements',
        'requirements',
        ['parent_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_requirements_parent_id', 'requirements', ['parent_id'])


def downgrade():
    op.drop_index('ix_requirements_parent_id', table_name='requirements')
    op.drop_constraint('fk_requirements_parent_id', 'requirements', type_='foreignkey')
    op.drop_column('requirements', 'parent_id')
