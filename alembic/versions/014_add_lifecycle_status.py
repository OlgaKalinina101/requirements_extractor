"""Add lifecycle_status to requirements; replace priorities with Critical/High/Medium/Low

Revision ID: 014_add_lifecycle_status
Revises: 013_add_project_requirement_manager
Create Date: 2026-03-20

"""
from alembic import op
import sqlalchemy as sa


revision = '014_add_lifecycle_status'
down_revision = '013_add_project_requirement_manager'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Add lifecycle_status column to requirements (idempotent)
    conn.execute(sa.text(
        "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(100)"
    ))

    # 2. Replace priorities dictionary: Mandatory/Recommended/Optional → Critical/High/Medium/Low
    conn.execute(sa.text("DELETE FROM dictionary_items WHERE dict_type = 'priorities'"))
    conn.execute(sa.text("""
        INSERT INTO dictionary_items (dict_type, code, name, description, color, sort_order, is_active, created_at)
        VALUES
            ('priorities', 'Critical', 'Critical', 'Критический приоритет — должно быть выполнено',       'red-darken-2',    1, true, now()),
            ('priorities', 'High',     'High',     'Высокий приоритет — важно для основного функционала', 'orange-darken-1', 2, true, now()),
            ('priorities', 'Medium',   'Medium',   'Средний приоритет — желательно к выполнению',         'blue',            3, true, now()),
            ('priorities', 'Low',      'Low',      'Низкий приоритет — выполняется при наличии ресурсов', 'grey',            4, true, now())
    """))

    # 3. Seed lifecycle_statuses if not yet populated (idempotent)
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM dictionary_items WHERE dict_type = 'lifecycle_statuses') THEN
                INSERT INTO dictionary_items (dict_type, code, name, description, color, sort_order, is_active, created_at)
                VALUES
                    ('lifecycle_statuses', 'draft',       'Draft',       'Черновик — требование сформулировано, но не проверено',   'grey',   1, true, now()),
                    ('lifecycle_statuses', 'in_review',   'In Review',   'На рассмотрении — проходит экспертную оценку',            'orange', 2, true, now()),
                    ('lifecycle_statuses', 'approved',    'Approved',    'Утверждено — принято как официальное требование',         'green',  3, true, now()),
                    ('lifecycle_statuses', 'implemented', 'Implemented', 'Реализовано — разработка завершена',                      'blue',   4, true, now()),
                    ('lifecycle_statuses', 'verified',    'Verified',    'Верифицировано — соответствие требованию подтверждено',   'teal',   5, true, now()),
                    ('lifecycle_statuses', 'rejected',    'Rejected',    'Отклонено — требование исключено из области охвата',      'red',    6, true, now());
            END IF;
        END $$;
    """))


def downgrade():
    conn = op.get_bind()

    conn.execute(sa.text("ALTER TABLE requirements DROP COLUMN IF EXISTS lifecycle_status"))
    conn.execute(sa.text("DELETE FROM dictionary_items WHERE dict_type = 'lifecycle_statuses'"))

    # Restore original priorities
    conn.execute(sa.text("DELETE FROM dictionary_items WHERE dict_type = 'priorities'"))
    conn.execute(sa.text("""
        INSERT INTO dictionary_items (dict_type, code, name, description, color, sort_order, is_active, created_at)
        VALUES
            ('priorities', 'Mandatory',   'Mandatory',   'Обязательное требование',  'red',    1, true, now()),
            ('priorities', 'Recommended', 'Recommended', 'Рекомендуемое требование', 'orange', 2, true, now()),
            ('priorities', 'Optional',    'Optional',    'Необязательное требование','blue',   3, true, now()),
            ('priorities', 'Unknown',     'Unknown',     'Приоритет не определён',   'grey',   4, true, now())
    """))
