"""Add dictionary_items table for editable reference data

Revision ID: 007_add_dictionary_items
Revises: 006_add_users_auth
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa


revision = '007_add_dictionary_items'
down_revision = '006_add_users_auth'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'dictionary_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dict_type', sa.String(50), nullable=False),
        sa.Column('code', sa.String(100), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(50), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dictionary_items_id', 'dictionary_items', ['id'])
    op.create_index('ix_dictionary_items_dict_type', 'dictionary_items', ['dict_type'])


def downgrade():
    op.drop_index('ix_dictionary_items_dict_type', table_name='dictionary_items')
    op.drop_index('ix_dictionary_items_id', table_name='dictionary_items')
    op.drop_table('dictionary_items')
