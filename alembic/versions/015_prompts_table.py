"""Add prompts table with seed from prompts.yaml

Revision ID: 015_prompts_table
Revises: 014_add_lifecycle_status
Create Date: 2026-03-20

"""
import os
import yaml
from pathlib import Path
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '015_prompts_table'
down_revision = '014_add_lifecycle_status'
branch_labels = None
depends_on = None

YAML_PATH = Path(__file__).parent.parent.parent / "src" / "prompts.yaml"


def _load_yaml():
    try:
        with open(YAML_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def upgrade():
    conn = op.get_bind()

    # 1. Create prompts table (idempotent)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS prompts (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(200),
            version VARCHAR(50),
            instruction TEXT,
            response_format TEXT,
            user_template TEXT,
            temperature FLOAT,
            max_tokens INTEGER,
            updated_at TIMESTAMP
        )
    """))

    # 2. Seed from prompts.yaml (ON CONFLICT DO NOTHING — idempotent)
    data = _load_yaml()
    for key, cfg in data.items():
        instruction = cfg.get("instruction", cfg.get("system", ""))
        response_format = cfg.get("response_format", "")
        user_template = cfg.get("user_template", "")
        name = cfg.get("name", key)
        version = cfg.get("version", "")
        temperature = cfg.get("temperature")
        max_tokens = cfg.get("max_tokens")

        conn.execute(text("""
            INSERT INTO prompts (key, name, version, instruction, response_format, user_template, temperature, max_tokens, updated_at)
            VALUES (:key, :name, :version, :instruction, :response_format, :user_template, :temperature, :max_tokens, NOW())
            ON CONFLICT (key) DO NOTHING
        """), {
            "key": key,
            "name": name,
            "version": version,
            "instruction": instruction,
            "response_format": response_format,
            "user_template": user_template,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })


def downgrade():
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS prompts"))
