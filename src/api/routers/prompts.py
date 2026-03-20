"""Prompts API — admin-only view and editing of extraction prompts."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.auth.dependencies import require_admin
from src.database.database import get_db
from src.prompts import get_prompt_loader_db
from src.database.crud.prompts import update_prompt, reset_prompt_to_yaml
from src.api.schemas.prompts import UpdatePromptRequest

router = APIRouter(tags=["prompts"])

PROMPT_KEYS = ["requirement_extractor_text", "requirement_extractor_image"]


@router.get("")
async def get_prompts(
    db: Session = Depends(get_db),
    _current=Depends(require_admin),
):
    """Return extraction prompts for admin view. Admin only."""
    loader = get_prompt_loader_db(db)
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
                "instruction": cfg.get("instruction", ""),
                "response_format": cfg.get("response_format", ""),
                "user_template": cfg.get("user_template", ""),
            })
    return {"prompts": result}


@router.put("/{key}")
async def update_prompt_endpoint(
    key: str,
    body: UpdatePromptRequest,
    db: Session = Depends(get_db),
    _current=Depends(require_admin),
):
    """Update editable parts of a prompt. Admin only."""
    if key not in PROMPT_KEYS:
        raise HTTPException(status_code=404, detail=f"Prompt '{key}' not found")
    prompt = update_prompt(db, key, body.instruction, body.user_template)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt '{key}' not found in database")
    return {"ok": True, "key": key}


@router.post("/{key}/reset")
async def reset_prompt_endpoint(
    key: str,
    db: Session = Depends(get_db),
    _current=Depends(require_admin),
):
    """Reset a prompt's instruction and user_template to YAML defaults. Admin only."""
    if key not in PROMPT_KEYS:
        raise HTTPException(status_code=404, detail=f"Prompt '{key}' not found")
    prompt = reset_prompt_to_yaml(db, key)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt '{key}' not found")
    return {"ok": True, "key": key}
