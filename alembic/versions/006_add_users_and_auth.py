"""Add users, assignee, comments for auth and roles

Revision ID: 006_add_users_auth
Revises: 005_add_indexes
Create Date: 2026-03-06

"""
from alembic import op
import sqlalchemy as sa


revision = '006_add_users_auth'
down_revision = '005_add_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'])

    # 2. Add assignee_id to requirements
    op.add_column('requirements', sa.Column('assignee_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_requirements_assignee_id_users',
        'requirements',
        'users',
        ['assignee_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_requirements_assignee_id', 'requirements', ['assignee_id'])

    # 3. Create comments table
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requirement_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_comments_id', 'comments', ['id'])
    op.create_index('ix_comments_requirement_id', 'comments', ['requirement_id'])
    op.create_index('ix_comments_user_id', 'comments', ['user_id'])


def downgrade():
    op.drop_table('comments')
    op.drop_index('ix_requirements_assignee_id', table_name='requirements')
    op.drop_constraint('fk_requirements_assignee_id_users', 'requirements', type_='foreignkey')
    op.drop_column('requirements', 'assignee_id')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')
