"""Add requirement_links table for relations between requirements

Revision ID: 012_add_requirement_links
Revises: 011_add_verification_document_type
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa


revision = '012_add_requirement_links'
down_revision = '011_add_verification_document_type'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Idempotent: create table if not exists (handles partial runs from previous container rebuilds)
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS requirement_links (
            id SERIAL PRIMARY KEY,
            source_requirement_id INTEGER NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
            target_requirement_id INTEGER NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
            link_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_requirement_links_source_requirement_id ON requirement_links (source_requirement_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_requirement_links_target_requirement_id ON requirement_links (target_requirement_id)"))
    # Add unique constraint only if it doesn't exist
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_requirement_links_source_target_type'
                AND conrelid = 'requirement_links'::regclass
            ) THEN
                ALTER TABLE requirement_links
                ADD CONSTRAINT uq_requirement_links_source_target_type
                UNIQUE (source_requirement_id, target_requirement_id, link_type);
            END IF;
        END $$;
    """))


def downgrade():
    op.drop_constraint('uq_requirement_links_source_target_type', 'requirement_links', type_='unique')
    op.drop_index('ix_requirement_links_target_requirement_id', table_name='requirement_links')
    op.drop_index('ix_requirement_links_source_requirement_id', table_name='requirement_links')
    op.drop_table('requirement_links')
