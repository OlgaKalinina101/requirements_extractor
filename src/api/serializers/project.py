"""Project serialization for API responses."""

from typing import Any, Dict, List

from .base import _iso
from .document import document_to_list_item


def project_to_dict(
    p,
    doc_count: int = 0,
    req_count: int = 0,
    *,
    include_counts: bool = True,
) -> Dict[str, Any]:
    """Convert Project model to API response dict with optional counts."""
    result = {
        "id": p.id,
        "name": p.name,
        "code": p.code,
        "description": p.description,
        "status": p.status,
        "created_at": _iso(p.created_at),
        "updated_at": _iso(p.updated_at),
    }
    if include_counts:
        result["documents_count"] = doc_count
        result["requirements_count"] = req_count
    return result


def project_with_docs(
    p, documents: List, req_counts: Dict[int, int]
) -> Dict[str, Any]:
    """Convert Project with documents to full API response dict."""
    docs_data = []
    for doc in documents:
        req_count = req_counts.get(doc.id, 0)
        docs_data.append(document_to_list_item(doc, requirements_count=req_count))
    return {
        "id": p.id,
        "name": p.name,
        "code": p.code,
        "description": p.description,
        "status": p.status,
        "created_at": _iso(p.created_at),
        "updated_at": _iso(p.updated_at),
        "documents": docs_data,
    }
