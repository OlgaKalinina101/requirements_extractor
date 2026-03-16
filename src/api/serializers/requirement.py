"""Requirement serialization for API responses."""

from typing import Any, Dict

from .base import _iso


def requirement_to_dict(req) -> Dict[str, Any]:
    """Convert Requirement model to full API response dict."""
    return {
        "id": req.id,
        "requirement_id": req.requirement_id,
        "text": req.text,
        "type": req.type,
        "priority": req.priority,
        "page_number": req.page_number,
        "status": req.status,
        "subitems": req.subitems or [],
        "assignee_id": req.assignee_id,
        "ai_suggested": req.ai_suggested,
        "human_edited": req.human_edited,
        "edit_reason": req.edit_reason,
        "edited_by": req.edited_by,
        "edited_at": _iso(req.edited_at),
        "document_id": req.document_id,
        "section_id": req.section_id,
        "section_number": req.section.section_number if req.section else None,
        "section_title": req.section.title if req.section else None,
        "created_at": _iso(req.created_at),
    }


def requirement_to_list_item(req) -> Dict[str, Any]:
    """Convert Requirement model to list item dict (for document requirements)."""
    return {
        "id": req.id,
        "requirement_id": req.requirement_id,
        "text": req.text,
        "type": req.type,
        "priority": req.priority,
        "page_number": req.page_number,
        "status": req.status,
        "assignee_id": req.assignee_id,
        "ai_suggested": req.ai_suggested,
        "human_edited": req.human_edited,
        "edit_reason": req.edit_reason,
        "edited_at": _iso(req.edited_at),
        "section_id": req.section_id,
        "section_number": req.section.section_number if req.section else None,
        "section_title": req.section.title if req.section else None,
        "subitems": req.subitems if hasattr(req, "subitems") else None,
        "created_at": _iso(req.created_at),
    }


def requirement_summary(req) -> Dict[str, Any]:
    """Convert Requirement to summary dict (for accept/reject/edit responses)."""
    return {
        "id": req.id,
        "requirement_id": req.requirement_id,
        "text": req.text,
        "status": req.status,
        "ai_suggested": req.ai_suggested,
        "human_edited": getattr(req, "human_edited", None),
        "edit_reason": getattr(req, "edit_reason", None),
        "edited_by": getattr(req, "edited_by", None),
        "edited_at": _iso(getattr(req, "edited_at", None)),
    }
