"""Prompt templates — loaded from DB (with YAML fallback).

Primary source: `prompts` table in database.
Fallback: prompts.yaml (used when DB row is absent or DB is unavailable).
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

PROMPTS_FILE = Path(__file__).parent / "prompts.yaml"


def _load_yaml() -> Dict[str, Dict[str, Any]]:
    try:
        if not PROMPTS_FILE.exists():
            return {}
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        logger.error("Failed to load prompts.yaml: %s", exc)
        return {}


def _yaml_to_cfg(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a YAML entry to the unified config dict format."""
    instruction = raw.get("instruction", raw.get("system", ""))
    response_format = raw.get("response_format", "")
    system = (instruction + "\n\n" + response_format).rstrip() if response_format else instruction
    return {
        "name": raw.get("name", ""),
        "version": raw.get("version", ""),
        "temperature": raw.get("temperature"),
        "max_tokens": raw.get("max_tokens"),
        "instruction": instruction,
        "response_format": response_format,
        "system": system,
        "user_template": raw.get("user_template", ""),
    }


class PromptLoader:
    """Loads and caches prompt templates. Reads from DB when a session is provided,
    otherwise falls back to prompts.yaml."""

    def __init__(self, prompts_file: Path = None):
        self.prompts_file = prompts_file or PROMPTS_FILE
        self._prompts: Dict[str, Dict[str, Any]] = {}
        self._load_from_yaml()

    def _load_from_yaml(self) -> None:
        raw = _load_yaml()
        self._prompts = {key: _yaml_to_cfg(cfg) for key, cfg in raw.items()}
        logger.info("Loaded %d prompt templates from YAML", len(self._prompts))

    def load_from_db(self, db) -> None:
        """Replace cached prompts with data from the DB (per-request call)."""
        try:
            from src.database.crud.prompts import get_all_prompts
            rows = get_all_prompts(db)
            if not rows:
                return
            yaml_data = _load_yaml()
            for row in rows:
                instruction = row.instruction or ""
                response_format = row.response_format or ""
                system = (instruction + "\n\n" + response_format).rstrip() if response_format else instruction
                self._prompts[row.key] = {
                    "name": row.name or row.key,
                    "version": row.version or "",
                    "temperature": row.temperature,
                    "max_tokens": row.max_tokens,
                    "instruction": instruction,
                    "response_format": response_format,
                    "system": system,
                    "user_template": row.user_template or "",
                }
            logger.debug("Loaded %d prompt templates from DB", len(rows))
        except Exception as exc:
            logger.warning("Could not load prompts from DB, using YAML: %s", exc)

    def get_prompt(self, name: str) -> Optional[Dict[str, Any]]:
        return self._prompts.get(name)

    def format_prompt(self, name: str, **kwargs) -> tuple[str, str]:
        """Return (system_message, user_message) with variables substituted."""
        prompt_config = self.get_prompt(name)
        if not prompt_config:
            raise ValueError(f"Prompt template '{name}' not found")

        system_template = prompt_config.get("system", "")
        user_template = prompt_config.get("user_template", "")

        try:
            system_message = system_template.format(**kwargs) if system_template else ""
            user_message = user_template.format(**kwargs) if user_template else ""
        except KeyError as e:
            logger.error("Missing variable %s for prompt '%s'", e, name)
            raise ValueError(f"Missing required variable {e} for prompt '{name}'")

        return system_message, user_message


# ---------------------------------------------------------------------------
# Global singleton (YAML-backed, used by background tasks / startup)
# ---------------------------------------------------------------------------
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


def get_prompt_loader_db(db) -> PromptLoader:
    """Return a PromptLoader populated from the DB for the current request."""
    loader = PromptLoader()
    loader.load_from_db(db)
    return loader


def reload_prompts() -> None:
    global _prompt_loader
    _prompt_loader = PromptLoader()
