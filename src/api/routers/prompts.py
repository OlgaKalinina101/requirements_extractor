"""Prompts API — admin-only view of extraction prompts."""

from fastapi import APIRouter, Depends

from src.auth.dependencies import require_admin
from src.prompts import get_prompt_loader

router = APIRouter(tags=["prompts"])

PROMPT_KEYS = ["requirement_extractor_text", "requirement_extractor_image"]


@router.get("")
async def get_prompts(_current=Depends(require_admin)):
    """Return extraction prompts for admin view. Admin only."""
    loader = get_prompt_loader()
    result = []
    for key in PROMPT_KEYS:
        cfg = loader.get_prompt(key)
        if cfg:
            result.append({
                "id": key,
                "name": cfg.get("name", key),
                "version": cfg.get("version", ""),
                "temperature": cfg.get("temperature"),
                "max_tokens": cfg.get("max_tokens"),
                "system": cfg.get("system", ""),
                "user_template": cfg.get("user_template", ""),
            })
    return {"prompts": result}
