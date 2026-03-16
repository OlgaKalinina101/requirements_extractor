"""FastAPI application factory and configuration."""

import logging
import os
from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.logger import setup_logger
from src.database.database import init_db, SessionLocal, db_session
from src.database import crud

# Setup logging
setup_logger(name="api", log_file=Path("logs/api.log"), level="INFO")
setup_logger(name="src.openrouter_client", log_file=Path("logs/openrouter.log"), level="INFO")
setup_logger(name="src.requirements_extractor", log_file=Path("logs/extractor.log"), level="INFO")
setup_logger(name="src.pdf_processor", log_file=Path("logs/pdf.log"), level="INFO")

logger = logging.getLogger("api")


def _seed_admin_if_needed() -> None:
    """Ensure the default admin user exists and has the password from env vars."""
    from src.auth.password import hash_password

    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD", "changeme")
    name = os.getenv("ADMIN_NAME", "Администратор")

    with db_session() as db:
        existing = crud.get_user_by_email(db, email)
        if existing:
            crud.update_user_password(db, existing.id, hash_password(password))
            logger.info(f"Admin password synced from env: {email}")
        else:
            crud.create_user(
                db,
                email=email,
                hashed_password=hash_password(password),
                full_name=name,
                role="admin",
            )
            logger.info(f"Created default admin user: {email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — runs startup and shutdown logic."""
    try:
        init_db()
        _seed_admin_if_needed()
        _seed_db = SessionLocal()
        try:
            crud.seed_dictionary_defaults(_seed_db)
        finally:
            _seed_db.close()
    except Exception as e:
        logger.error(f"Startup error: {e}")
        logger.warning("Continuing — some features may not work")
    logger.info("WebSocket logging system initialized")
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PDF Requirements Extractor API - OpenRouter",
        description="Extract requirements from technical specifications using OpenRouter AI models (Claude, GPT, Gemini, Qwen)",
        version="3.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from src.api.routers import (
        health_router,
        auth_router,
        users_router,
        websocket_router,
        extraction_router,
        documents_router,
        requirements_router,
        projects_router,
        dashboard_router,
        download_router,
        dictionaries_router,
        comments_router,
    )

    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(users_router, prefix="/api/users")
    app.include_router(websocket_router, prefix="/ws")
    app.include_router(extraction_router, prefix="/api/extract")
    app.include_router(documents_router, prefix="/api/documents")
    app.include_router(requirements_router, prefix="/api/requirements")
    app.include_router(projects_router, prefix="/api/projects")
    app.include_router(dashboard_router, prefix="/api/dashboard")
    app.include_router(download_router, prefix="/api/download")
    app.include_router(dictionaries_router, prefix="/api/dictionaries")
    app.include_router(comments_router, prefix="/api/comments")

    return app


app = create_app()
