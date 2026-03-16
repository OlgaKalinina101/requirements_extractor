"""Dictionary item serialization for API responses."""

from typing import Any, Dict

from .base import _iso


def dict_item_to_dict(item) -> Dict[str, Any]:
    """Convert DictionaryItem model to API response dict."""
    return {
        "id": item.id,
        "dict_type": item.dict_type,
        "code": item.code,
        "name": item.name,
        "description": item.description,
        "color": item.color,
        "sort_order": item.sort_order,
        "is_active": item.is_active,
        "created_at": _iso(item.created_at),
    }
