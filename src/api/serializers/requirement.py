"""Requirement serialization for API responses."""

from typing import Any, Dict, List

from .base import _iso


def _serialize_links(links: List, is_outgoing: bool) -> List[Dict[str, Any]]:
    """Serialize requirement links for API response."""
    result = []
    for link in links:
        other = link.target_requirement if is_outgoing else link.source_requirement
        result.append({
            "id": link.id,
            "link_type": link.link_type,
            "requirement_id": other.id,
            "requirement_requirement_id": other.requirement_id,
            "requirement_text_preview": (other.text or "")[:80] + ("..." if len(other.text or "") > 80 else ""),
        })
    return result


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
        "discipline": getattr(req, "discipline", None),
        "verification_method": getattr(req, "verification_method", None),
        "deadline": req.deadline.isoformat() if getattr(req, "deadline", None) else None,
        "ai_suggested": req.ai_suggested,
        "human_edited": req.human_edited,
        "edit_reason": req.edit_reason,
        "edited_by": req.edited_by,
        "edited_at": _iso(req.edited_at),
        "document_id": req.document_id,
        "section_id": req.section_id,
        "section_number": req.section.section_number if req.section else None,
        "section_title": req.section.title if req.section else None,
        "parent_id": getattr(req, "parent_id", None),
        "parent_requirement_id": req.parent.requirement_id if getattr(req, "parent", None) and req.parent else None,
        "children": [
            {"id": c.id, "requirement_id": c.requirement_id, "text": (c.text or "")[:100] + ("..." if len(c.text or "") > 100 else "")}
            for c in (getattr(req, "children", []) or [])
        ],
        "outgoing_links": _serialize_links(getattr(req, "outgoing_links", []) or [], is_outgoing=True),
        "incoming_links": _serialize_links(getattr(req, "incoming_links", []) or [], is_outgoing=False),
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
        "discipline": getattr(req, "discipline", None),
        "verification_method": getattr(req, "verification_method", None),
        "deadline": req.deadline.isoformat() if getattr(req, "deadline", None) else None,
        "ai_suggested": req.ai_suggested,
        "human_edited": req.human_edited,
        "edit_reason": req.edit_reason,
        "edited_at": _iso(req.edited_at),
        "section_id": req.section_id,
        "section_number": req.section.section_number if req.section else None,
        "section_title": req.section.title if req.section else None,
        "parent_id": getattr(req, "parent_id", None),
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
