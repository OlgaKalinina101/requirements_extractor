"""JSON registry export from database data."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from .utils import group_requirements_by_sections

logger = logging.getLogger("api")


def _req_to_dict(req, section_number=None, section_title=None) -> Dict[str, Any]:
    """Serialize a single requirement to a JSON-safe dict."""
    assignee_name = None
    if hasattr(req, "assignee") and req.assignee:
        assignee_name = req.assignee.full_name or req.assignee.email

    outgoing = []
    for link in (getattr(req, "outgoing_links", None) or []):
        target = getattr(link, "target_requirement", None)
        outgoing.append({
            "link_type": link.link_type,
            "requirement_id": target.requirement_id if target else None,
        })

    incoming = []
    for link in (getattr(req, "incoming_links", None) or []):
        source = getattr(link, "source_requirement", None)
        incoming.append({
            "link_type": link.link_type,
            "requirement_id": source.requirement_id if source else None,
        })

    return {
        "id": req.requirement_id,
        "text": req.human_edited or req.text,
        "type": req.type,
        "priority": req.priority,
        "lifecycle_status": getattr(req, "lifecycle_status", None),
        "status": req.status,
        "discipline": getattr(req, "discipline", None),
        "verification_method": getattr(req, "verification_method", None),
        "deadline": req.deadline.isoformat() if getattr(req, "deadline", None) else None,
        "assignee": assignee_name,
        "page_number": req.page_number,
        "section_number": section_number,
        "section_title": section_title,
        "subitems": req.subitems or [],
        "human_edited": req.human_edited,
        "edit_reason": req.edit_reason,
        "links": {"outgoing": outgoing, "incoming": incoming},
    }


def build_json_registry(document, sections: List, all_requirements: List) -> Dict[str, Any]:
    """Build JSON registry structure from document, sections, and requirements."""
    registry = {
        "document": {
            "filename": document.filename,
            "document_type": getattr(document, "document_type", None),
            "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
            "total_requirements": len(all_requirements),
            "total_sections": len(sections),
        },
        "sections": [],
        "requirements_without_section": [],
    }

    section_reqs, orphans = group_requirements_by_sections(sections, all_requirements)
    for section in sections:
        section_data = {
            "number": section.section_number,
            "title": section.title,
            "page_start": section.page_start,
            "page_end": section.page_end,
            "requirements": [
                _req_to_dict(req, section.section_number, section.title)
                for req in section_reqs[section.id]
            ],
        }
        registry["sections"].append(section_data)

    registry["requirements_without_section"] = [
        _req_to_dict(req) for req in orphans
    ]

    return registry


def export_json_to_temp_file(
    document, sections: List, all_requirements: List
) -> Path:
    """Build JSON registry and save to temporary file. Returns path to temp file."""
    registry = build_json_registry(document, sections, all_requirements)
    temp_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(registry, temp_file, ensure_ascii=False, indent=2)
    temp_file.close()
    logger.info(f"[EXPORT] JSON registry generated: {temp_file.name}")
    return Path(temp_file.name)
