"""Add requirement_manager_id to projects

Revision ID: 013_add_project_requirement_manager
Revises: 012_add_requirement_links
Create Date: 2026-03-19

"""
from alembic import op
import sqlalchemy as sa


revision = '013_add_project_requirement_manager'
down_revision = '012_add_requirement_links'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE projects ADD COLUMN IF NOT EXISTS requirement_manager_id INTEGER
        REFERENCES users(id) ON DELETE SET NULL
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_projects_requirement_manager_id ON projects (requirement_manager_id)"))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_projects_requirement_manager_id"))
    conn.execute(sa.text("ALTER TABLE projects DROP COLUMN IF EXISTS requirement_manager_id"))
