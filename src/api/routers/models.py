"""API endpoints for AI model catalog."""

from fastapi import APIRouter

router = APIRouter(tags=["models"])


@router.get("/models")
def list_models():
    """Return available AI models for extraction (id and display name)."""
    from src.openrouter_client import get_available_models

    models = get_available_models()
    return [{"id": k, "name": v.name} for k, v in models.items()]
