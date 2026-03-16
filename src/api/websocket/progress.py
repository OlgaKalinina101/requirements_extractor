"""Progress and metric broadcasting for WebSocket clients."""

import logging
from datetime import datetime
from typing import Any, Optional

from .manager import manager as default_manager

logger = logging.getLogger("api")


async def send_progress(
    step: str,
    progress: int,
    message: str,
    section_id: Optional[int] = None,
    manager=None,
    **kwargs,
) -> None:
    """Send progress update to all connected WebSocket clients."""
    mgr = manager or default_manager
    progress_msg = {
        "type": "progress",
        "step": step,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }
    if section_id is not None:
        progress_msg["section_id"] = section_id
    progress_msg.update(kwargs)

    logger.info(f"[PROGRESS] {progress}% - {message}" + (f" (section {section_id})" if section_id else ""))

    if len(mgr.active_connections) > 0:
        await mgr.send_message(progress_msg)
    else:
        logger.warning("[PROGRESS] No active WebSocket connections!")


async def send_metric(
    metric_name: str,
    value: Any,
    section: Optional[str] = None,
    manager=None,
    **kwargs,
) -> None:
    """Send structured metric to all connected WebSocket clients."""
    mgr = manager or default_manager
    metric_msg = {
        "type": "metric",
        "metric_name": metric_name,
        "value": value,
        "timestamp": datetime.now().isoformat(),
    }
    if section is not None:
        metric_msg["section"] = section
    metric_msg.update(kwargs)

    logger.debug(f"[METRIC] {metric_name}={value}" + (f" section={section}" if section else ""))

    if len(mgr.active_connections) > 0:
        await mgr.send_message(metric_msg)
