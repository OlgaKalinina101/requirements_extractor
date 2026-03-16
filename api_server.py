"""Entry point for PDF Requirements Extractor API.

This module provides the uvicorn entry point. The FastAPI application
is defined in src.api.app.
"""

from src.api.app import app

if __name__ == "__main__":
    import uvicorn

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        timeout_keep_alive=300,
        timeout_graceful_shutdown=30,
    )
    server = uvicorn.Server(config)
    server.run()
