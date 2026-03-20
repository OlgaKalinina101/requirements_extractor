"""CRUD operations for AI prompt templates."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import yaml
from sqlalchemy.orm import Session

from src.database.models import Prompt

logger = logging.getLogger(__name__)

YAML_PATH = Path(__file__).parent.parent.parent / "prompts.yaml"


def get_all_prompts(db: Session) -> List[Prompt]:
    return db.query(Prompt).order_by(Prompt.id).all()


def get_prompt_by_key(db: Session, key: str) -> Optional[Prompt]:
    return db.query(Prompt).filter(Prompt.key == key).first()


def update_prompt(db: Session, key: str, instruction: str, user_template: str) -> Optional[Prompt]:
    from datetime import datetime
    prompt = get_prompt_by_key(db, key)
    if not prompt:
        return None
    prompt.instruction = instruction
    prompt.user_template = user_template
    prompt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prompt)
    return prompt


def reset_prompt_to_yaml(db: Session, key: str) -> Optional[Prompt]:
    """Restore instruction and user_template from prompts.yaml defaults."""
    from datetime import datetime
    try:
        with open(YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.error("Failed to load prompts.yaml for reset: %s", exc)
        return None

    cfg = data.get(key)
    if not cfg:
        return None

    prompt = get_prompt_by_key(db, key)
    if not prompt:
        return None

    prompt.instruction = cfg.get("instruction", cfg.get("system", ""))
    prompt.user_template = cfg.get("user_template", "")
    prompt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prompt)
    return prompt


def seed_prompts_from_yaml(db: Session) -> None:
    """Insert missing prompts from YAML on startup (idempotent)."""
    from datetime import datetime
    try:
        with open(YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.error("Failed to seed prompts from YAML: %s", exc)
        return

    for key, cfg in data.items():
        existing = get_prompt_by_key(db, key)
        if existing:
            continue
        prompt = Prompt(
            key=key,
            name=cfg.get("name", key),
            version=cfg.get("version", ""),
            instruction=cfg.get("instruction", cfg.get("system", "")),
            response_format=cfg.get("response_format", ""),
            user_template=cfg.get("user_template", ""),
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
            updated_at=datetime.utcnow(),
        )
        db.add(prompt)
    db.commit()
