"""Add subitems column to requirements table

Revision ID: 004_add_subitems
Revises: 003_add_projects
Create Date: 2026-03-06 20:45:00

"""
from alembic import op
import sqlalchemy as sa


revision = '004_add_subitems'
down_revision = '003_add_projects'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('requirements', sa.Column('subitems', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('requirements', 'subitems')
