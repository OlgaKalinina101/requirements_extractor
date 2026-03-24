"""Add assignments table and align lifecycle_statuses with ТЗ

Creates the `assignments` table (per ТЗ: Назначения — requirement ↔ assignee
with assigned_by, assigned_at, deadline).

Updates `lifecycle_statuses` dictionary to match the ТЗ lifecycle:
  извлечено → на верификации → принято → назначено → в работе → выполнено → закрыто

Migrates existing lifecycle_status values in requirements table.

Revision ID: 018_add_assignments_and_update_lifecycle
Revises: 017_add_source_quote
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa


revision = '018_add_assignments_and_update_lifecycle'
down_revision = '017_add_source_quote'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # ── 1. Create assignments table ──────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS assignments (
            id SERIAL PRIMARY KEY,
            requirement_id INTEGER NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
            assignee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            assigned_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            assigned_at TIMESTAMP NOT NULL DEFAULT now(),
            deadline DATE,
            is_active BOOLEAN NOT NULL DEFAULT true
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_assignments_requirement_id ON assignments(requirement_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_assignments_assignee_id ON assignments(assignee_id)"
    ))

    # ── 2. Replace lifecycle_statuses dictionary with ТЗ-aligned values ──────
    conn.execute(sa.text(
        "DELETE FROM dictionary_items WHERE dict_type = 'lifecycle_statuses'"
    ))
    conn.execute(sa.text("""
        INSERT INTO dictionary_items
            (dict_type, code, name, description, color, sort_order, is_active, created_at)
        VALUES
            ('lifecycle_statuses', 'extracted',    'Извлечено',      'Требование извлечено ИИ-агентом из документа',        'grey',      1, true, now()),
            ('lifecycle_statuses', 'verification', 'На верификации', 'Проходит проверку инженером / менеджером',            'orange',    2, true, now()),
            ('lifecycle_statuses', 'accepted',     'Принято',        'Требование верифицировано и принято',                 'green',     3, true, now()),
            ('lifecycle_statuses', 'assigned',     'Назначено',      'Назначен ответственный исполнитель',                  'blue',      4, true, now()),
            ('lifecycle_statuses', 'in_progress',  'В работе',       'Исполнитель приступил к выполнению',                  'cyan',      5, true, now()),
            ('lifecycle_statuses', 'completed',    'Выполнено',      'Работа по требованию завершена',                      'teal',      6, true, now()),
            ('lifecycle_statuses', 'closed',       'Закрыто',        'Требование закрыто, жизненный цикл завершён',         'blue-grey', 7, true, now())
    """))

    # ── 3. Migrate existing lifecycle_status values in requirements ───────────
    mapping = {
        "draft": "extracted",
        "in_review": "verification",
        "approved": "accepted",
        "implemented": "in_progress",
        "verified": "completed",
        "rejected": "extracted",
    }
    for old_val, new_val in mapping.items():
        conn.execute(sa.text(
            "UPDATE requirements SET lifecycle_status = :new WHERE lifecycle_status = :old"
        ), {"old": old_val, "new": new_val})

    # Set lifecycle_status for requirements that have none
    conn.execute(sa.text(
        "UPDATE requirements SET lifecycle_status = 'extracted' WHERE lifecycle_status IS NULL"
    ))


def downgrade():
    conn = op.get_bind()

    # Restore old lifecycle values
    reverse_mapping = {
        "extracted": "draft",
        "verification": "in_review",
        "accepted": "approved",
        "assigned": "approved",
        "in_progress": "implemented",
        "completed": "verified",
        "closed": "verified",
    }
    for new_val, old_val in reverse_mapping.items():
        conn.execute(sa.text(
            "UPDATE requirements SET lifecycle_status = :old WHERE lifecycle_status = :new"
        ), {"old": old_val, "new": new_val})

    # Restore old lifecycle_statuses dictionary
    conn.execute(sa.text(
        "DELETE FROM dictionary_items WHERE dict_type = 'lifecycle_statuses'"
    ))
    conn.execute(sa.text("""
        INSERT INTO dictionary_items
            (dict_type, code, name, description, color, sort_order, is_active, created_at)
        VALUES
            ('lifecycle_statuses', 'draft',       'Draft',       'Черновик',           'grey',   1, true, now()),
            ('lifecycle_statuses', 'in_review',   'In Review',   'На рассмотрении',    'orange', 2, true, now()),
            ('lifecycle_statuses', 'approved',    'Approved',    'Утверждено',         'green',  3, true, now()),
            ('lifecycle_statuses', 'implemented', 'Implemented', 'Реализовано',        'blue',   4, true, now()),
            ('lifecycle_statuses', 'verified',    'Verified',    'Верифицировано',     'teal',   5, true, now()),
            ('lifecycle_statuses', 'rejected',    'Rejected',    'Отклонено',          'red',    6, true, now())
    """))

    # Drop assignments table
    conn.execute(sa.text("DROP TABLE IF EXISTS assignments"))
