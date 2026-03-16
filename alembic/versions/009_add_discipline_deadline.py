"""Add discipline and deadline to requirements

Revision ID: 009_add_discipline_deadline
Revises: 008_add_requirement_history
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa


revision = '009_add_discipline_deadline'
down_revision = '008_add_requirement_history'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('requirements', sa.Column('discipline', sa.String(100), nullable=True))
    op.add_column('requirements', sa.Column('deadline', sa.Date(), nullable=True))
    op.create_index('ix_requirements_discipline', 'requirements', ['discipline'])


def downgrade():
    op.drop_index('ix_requirements_discipline', table_name='requirements')
    op.drop_column('requirements', 'deadline')
    op.drop_column('requirements', 'discipline')
