"""JSON registry export from database data."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from .utils import group_requirements_by_sections

logger = logging.getLogger("api")


def build_json_registry(document, sections: List, all_requirements: List) -> Dict[str, Any]:
    """Build JSON registry structure from document, sections, and requirements."""
    registry = {
        "document": {
            "filename": document.filename,
            "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
            "total_requirements": len(all_requirements),
            "total_sections": len(sections),
        },
        "sections": [],
    }

    section_reqs, _ = group_requirements_by_sections(sections, all_requirements)
    for section in sections:
        section_requirements = section_reqs[section.id]
        section_data = {
            "number": section.section_number,
            "title": section.title,
            "page_start": section.page_start,
            "page_end": section.page_end,
            "requirements": [
                {
                    "id": req.requirement_id,
                    "text": req.text,
                    "type": req.type,
                    "priority": req.priority,
                    "page_number": req.page_number,
                    "section_number": section.section_number,
                    "section_title": section.title,
                    "subitems": req.subitems or [],
                    "status": req.status,
                    "human_edited": req.human_edited,
                    "edit_reason": req.edit_reason,
                }
                for req in section_requirements
            ],
        }
        registry["sections"].append(section_data)

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
