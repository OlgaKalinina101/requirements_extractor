"""Remove ENUM constraints and use VARCHAR

Revision ID: 002_remove_enums
Revises: 001_initial_schema
Create Date: 2026-02-21 22:06:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_remove_enums'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Change type and priority columns to VARCHAR
    op.execute("ALTER TABLE requirements ALTER COLUMN type TYPE VARCHAR(50)")
    op.execute("ALTER TABLE requirements ALTER COLUMN priority TYPE VARCHAR(50)")
    
    # Drop the ENUM types (CASCADE will handle dependencies)
    op.execute("DROP TYPE IF EXISTS requirementtype CASCADE")
    op.execute("DROP TYPE IF EXISTS requirementpriority CASCADE")


def downgrade():
    # Recreate ENUM types
    op.execute("""
        CREATE TYPE requirementtype AS ENUM (
            'Техническое',
            'Организационное',
            'Документационное',
            'Функциональное',
            'Нефункциональное',
            'Прочее'
        )
    """)
    
    op.execute("""
        CREATE TYPE requirementpriority AS ENUM (
            'Обязательно',
            'Желательно',
            'Опционально'
        )
    """)
    
    # Convert VARCHAR back to ENUM
    op.execute("ALTER TABLE requirements ALTER COLUMN type TYPE requirementtype USING type::requirementtype")
    op.execute("ALTER TABLE requirements ALTER COLUMN priority TYPE requirementpriority USING priority::requirementpriority")
