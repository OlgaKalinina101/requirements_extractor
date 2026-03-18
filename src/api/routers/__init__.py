"""API routers."""

from .health import router as health_router
from .auth import router as auth_router
from .users import router as users_router
from .websocket import router as websocket_router
from .extraction import router as extraction_router
from .documents import router as documents_router
from .requirements import router as requirements_router
from .projects import router as projects_router
from .dashboard import router as dashboard_router
from .download import router as download_router
from .dictionaries import router as dictionaries_router
from .comments import router as comments_router
from .prompts import router as prompts_router

__all__ = [
    "health_router",
    "auth_router",
    "users_router",
    "websocket_router",
    "extraction_router",
    "documents_router",
    "requirements_router",
    "projects_router",
    "dashboard_router",
    "download_router",
    "dictionaries_router",
    "comments_router",
    "prompts_router",
]
