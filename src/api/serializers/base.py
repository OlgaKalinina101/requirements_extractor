"""Base serialization utilities."""

from datetime import datetime
from typing import Optional


def _iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO format string, or None if dt is None."""
    return dt.isoformat() if dt else None
