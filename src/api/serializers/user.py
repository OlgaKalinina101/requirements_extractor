"""User serialization for API responses."""

from typing import Any, Dict

from .base import _iso


def user_to_dict(user) -> Dict[str, Any]:
    """Convert User model to API response dict."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": _iso(user.created_at),
    }
