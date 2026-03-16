"""Comment serialization for API responses."""

from typing import Any, Dict, Optional

from .base import _iso


def comment_to_dict(comment, user=None) -> Dict[str, Any]:
    """Convert Comment model to API response dict."""
    author_name = None
    if user:
        author_name = user.full_name or user.email
    return {
        "id": comment.id,
        "requirement_id": comment.requirement_id,
        "user_id": comment.user_id,
        "author_name": author_name,
        "text": comment.text,
        "created_at": _iso(comment.created_at),
    }
