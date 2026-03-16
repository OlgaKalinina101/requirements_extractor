"""Add requirement_history table for audit log

Revision ID: 008_add_requirement_history
Revises: 007_add_dictionary_items
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa


revision = '008_add_requirement_history'
down_revision = '007_add_dictionary_items'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'requirement_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requirement_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=True),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_requirement_history_id', 'requirement_history', ['id'])
    op.create_index('ix_requirement_history_requirement_id', 'requirement_history', ['requirement_id'])
    op.create_index('ix_requirement_history_created_at', 'requirement_history', ['created_at'])


def downgrade():
    op.drop_index('ix_requirement_history_created_at', table_name='requirement_history')
    op.drop_index('ix_requirement_history_requirement_id', table_name='requirement_history')
    op.drop_index('ix_requirement_history_id', table_name='requirement_history')
    op.drop_table('requirement_history')
