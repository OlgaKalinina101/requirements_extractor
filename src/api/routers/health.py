"""Health and root endpoints."""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint providing API information."""
    return {
        "name": "PDF Requirements Extractor API",
        "version": "3.0.0",
        "status": "running",
    }


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
