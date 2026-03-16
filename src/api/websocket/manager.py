"""WebSocket connection manager and logging handler."""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List

from fastapi import WebSocket

logger = logging.getLogger("api")


class ConnectionManager:
    """Manages WebSocket connections for real-time communication.

    Handles multiple concurrent WebSocket connections, broadcasting messages
    to all connected clients, and cleaning up disconnected clients.
    """

    def __init__(self) -> None:
        """Initialize the connection manager with an empty connections list."""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
        else:
            logger.warning("WebSocket disconnect called but connection not in list")

    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message via WebSocket: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
                logger.info(f"Removed disconnected WebSocket. Remaining: {len(self.active_connections)}")


class WebSocketHandler(logging.Handler):
    """Custom logging handler that sends log messages via WebSocket.

    Uses thread-safe async execution to work correctly from both
    main thread and ThreadPoolExecutor threads.
    """

    def __init__(
        self,
        manager_instance: ConnectionManager,
        event_loop: asyncio.AbstractEventLoop,
    ) -> None:
        super().__init__()
        self.manager = manager_instance
        self.loop = event_loop

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by sending it via WebSocket."""
        try:
            log_entry = {
                "type": "log",
                "level": record.levelname,
                "message": self.format(record),
                "timestamp": datetime.now().isoformat(),
            }
            asyncio.run_coroutine_threadsafe(
                self.manager.send_message(log_entry),
                self.loop,
            )
        except Exception as e:
            sys.stderr.write(f"WebSocket logging error: {e}\n")


# Singleton instance
manager = ConnectionManager()
