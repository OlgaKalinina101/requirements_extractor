"""Document serialization for API responses."""

from typing import Any, Dict, Optional

from .base import _iso


def document_to_dict(doc) -> Dict[str, Any]:
    """Convert Document model to full API response dict (with file_path)."""
    return {
        "id": doc.id,
        "project_id": doc.project_id,
        "filename": doc.filename,
        "file_path": doc.file_path,
        "status": doc.status,
        "total_pages": doc.total_pages,
        "model_used": doc.model_used,
        "uploaded_at": _iso(doc.uploaded_at),
        "processed_at": _iso(doc.processed_at),
    }


def document_to_list_item(doc, requirements_count: Optional[int] = None) -> Dict[str, Any]:
    """Convert Document model to list item dict (without file_path)."""
    result = {
        "id": doc.id,
        "project_id": doc.project_id,
        "filename": doc.filename,
        "status": doc.status,
        "total_pages": doc.total_pages,
        "model_used": doc.model_used,
        "uploaded_at": _iso(doc.uploaded_at),
        "processed_at": _iso(doc.processed_at),
    }
    if requirements_count is not None:
        result["requirements_count"] = requirements_count
    return result


def metrics_to_dict(metrics) -> Dict[str, Any]:
    """Convert CoverageMetrics model to API response dict."""
    return {
        "document_id": metrics.document_id,
        "total_pages": metrics.total_pages,
        "processed_pages": metrics.processed_pages,
        "skipped_pages": metrics.skipped_pages or [],
        "coverage_percent": metrics.coverage_percent,
        "requirements_count": metrics.requirements_count,
        "requirements_by_type": metrics.requirements_by_type or {},
        "calculated_at": _iso(metrics.calculated_at),
    }
