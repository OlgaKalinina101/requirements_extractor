"""Requirement CRUD operations."""

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from src.database.models import Requirement, RequirementLink
from src.models import RequirementType

logger = logging.getLogger("api")


def delete_requirement(db: Session, requirement_id: int) -> bool:
    """Hard-delete a requirement by ID. Returns True if deleted."""
    req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not req:
        return False
    db.delete(req)
    db.commit()
    return True


def get_all_requirements(
    db: Session,
    project_id: Optional[int] = None,
    document_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    req_type: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
):
    """Get all requirements across all documents with optional filters."""
    from src.database.models import Document, Project

    q = (
        db.query(Requirement)
        .join(Document, Requirement.document_id == Document.id)
        .outerjoin(Project, Document.project_id == Project.id)
        .options(
            joinedload(Requirement.document),
            joinedload(Requirement.section),
            joinedload(Requirement.parent),
            joinedload(Requirement.children),
            joinedload(Requirement.outgoing_links).joinedload(RequirementLink.target_requirement),
            joinedload(Requirement.incoming_links).joinedload(RequirementLink.source_requirement),
        )
    )
    if project_id is not None:
        q = q.filter(Document.project_id == project_id)
    if document_id is not None:
        q = q.filter(Requirement.document_id == document_id)
    if assignee_id is not None:
        q = q.filter(Requirement.assignee_id == assignee_id)
    if discipline:
        q = q.filter(Requirement.discipline == discipline)
    if status:
        q = q.filter(Requirement.status == status)
    if req_type:
        q = q.filter(Requirement.type == req_type)
    if priority:
        q = q.filter(Requirement.priority == priority)
    if search:
        q = q.filter(Requirement.text.ilike(f"%{search}%"))
    q = q.order_by(Document.project_id, Requirement.document_id, Requirement.id)
    return q.offset(skip).limit(limit).all()


def _next_manual_requirement_id(db: Session, document_id: int) -> str:
    """Generate next REQ-MAN-XXX ID for manually added requirements."""
    import re
    existing = (
        db.query(Requirement.requirement_id)
        .filter(Requirement.document_id == document_id)
        .filter(Requirement.requirement_id.like("REQ-MAN-%"))
        .all()
    )
    max_num = 0
    for (rid,) in existing:
        m = re.search(r"REQ-MAN-(\d+)$", rid or "")
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"REQ-MAN-{max_num + 1:03d}"


def create_requirement(
    db: Session,
    document_id: int,
    requirement_id: str,
    text: str,
    ai_suggested: str,
    section_id: Optional[int] = None,
    type: Optional[Any] = None,
    priority: Optional[Any] = None,
    page_number: Optional[int] = None,
    bbox: Optional[dict] = None,
) -> Requirement:
    """Create a new requirement record."""
    type_str = None
    if type is not None:
        type_str = type.value if hasattr(type, "value") else str(type)
    priority_str = None
    if priority is not None:
        priority_str = priority.value if hasattr(priority, "value") else str(priority)

    db_requirement = Requirement(
        document_id=document_id,
        section_id=section_id,
        requirement_id=requirement_id,
        text=text,
        ai_suggested=ai_suggested,
        type=type_str,
        priority=priority_str,
        page_number=page_number,
        bbox=bbox,
        status="pending",
        lifecycle_status="extracted",
    )
    db.add(db_requirement)
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


def get_requirement(db: Session, requirement_id: int) -> Optional[Requirement]:
    """Get requirement by ID."""
    return (
        db.query(Requirement)
        .options(
            joinedload(Requirement.section),
            joinedload(Requirement.parent),
            joinedload(Requirement.children),
            joinedload(Requirement.outgoing_links).joinedload(RequirementLink.target_requirement),
            joinedload(Requirement.incoming_links).joinedload(RequirementLink.source_requirement),
        )
        .filter(Requirement.id == requirement_id)
        .first()
    )


def get_requirements_by_document(
    db: Session,
    document_id: int,
    status: Optional[str] = None,
    type: Optional[RequirementType] = None,
    assignee_id: Optional[int] = None,
    discipline: Optional[str] = None,
    skip: int = 0,
    limit: Optional[int] = None,
):
    """Get all requirements for a document with optional filters."""
    query = (
        db.query(Requirement)
        .options(joinedload(Requirement.section))
        .filter(Requirement.document_id == document_id)
    )
    if status:
        query = query.filter(Requirement.status == status)
    if type:
        type_val = type.value if hasattr(type, "value") else type
        query = query.filter(Requirement.type == type_val)
    if assignee_id is not None:
        query = query.filter(Requirement.assignee_id == assignee_id)
    if discipline:
        query = query.filter(Requirement.discipline == discipline)
    query = query.order_by(
        Requirement.section_id.asc().nulls_last(),
        Requirement.page_number.asc().nulls_last(),
        Requirement.id.asc(),
    )
    query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def accept_requirement(db: Session, requirement_id: int) -> Optional[Requirement]:
    """Accept a requirement (mark as accepted)."""
    db_requirement = get_requirement(db, requirement_id)
    if not db_requirement:
        return None
    db_requirement.status = "accepted"
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


def reject_requirement(
    db: Session,
    requirement_id: int,
    reason: Optional[str] = None,
) -> Optional[Requirement]:
    """Reject a requirement (mark as rejected)."""
    db_requirement = get_requirement(db, requirement_id)
    if not db_requirement:
        return None
    db_requirement.status = "rejected"
    db_requirement.edit_reason = reason
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


def update_lifecycle_status(
    db: Session,
    requirement_id: int,
    lifecycle_status: str,
) -> Optional[Requirement]:
    """Update requirement lifecycle status (Draft → In Review → Approved → …)."""
    req = get_requirement(db, requirement_id)
    if not req:
        return None
    req.lifecycle_status = lifecycle_status
    db.commit()
    db.refresh(req)
    return req


def edit_requirement(
    db: Session,
    requirement_id: int,
    edited_text: str,
    reason: Optional[str] = None,
    edited_by: Optional[str] = None,
    req_type: Optional[str] = None,
    priority: Optional[str] = None,
    discipline: Optional[str] = None,
    verification_method: Optional[str] = None,
    deadline=None,
    parent_id: Optional[int] = None,
    lifecycle_status: Optional[str] = None,
) -> Optional[Requirement]:
    """Edit a requirement (mark as modified)."""
    db_requirement = get_requirement(db, requirement_id)
    if not db_requirement:
        return None
    db_requirement.status = "modified"
    db_requirement.text = edited_text
    db_requirement.human_edited = edited_text
    db_requirement.edit_reason = reason
    db_requirement.edited_by = edited_by
    db_requirement.edited_at = datetime.now()
    if req_type is not None:
        db_requirement.type = req_type
    if priority is not None:
        db_requirement.priority = priority
    if discipline is not None:
        db_requirement.discipline = discipline
    if verification_method is not None:
        db_requirement.verification_method = verification_method
    if deadline is not None:
        db_requirement.deadline = deadline
    if parent_id is not None:
        db_requirement.parent_id = parent_id
    if lifecycle_status is not None:
        db_requirement.lifecycle_status = lifecycle_status
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


def assign_requirement(
    db: Session,
    requirement_id: int,
    assignee_id: Optional[int],
) -> Optional[Requirement]:
    """Assign or unassign an executor to a requirement."""
    req = get_requirement(db, requirement_id)
    if not req:
        return None
    req.assignee_id = assignee_id
    db.commit()
    db.refresh(req)
    return req


def update_requirement_status(
    db: Session,
    requirement_id: int,
    status: str,
) -> Optional[Requirement]:
    """Update requirement execution/manager status."""
    req = get_requirement(db, requirement_id)
    if not req:
        return None
    req.status = status
    db.commit()
    db.refresh(req)
    return req


def bulk_create_requirements(
    db: Session,
    document_id: int,
    section_id: int,
    requirements: list,
) -> int:
    """Bulk create requirements for a section."""
    if not requirements:
        return 0
    requirements_data = []
    for req in requirements:
        type_str = None
        if req.type is not None:
            type_str = req.type.value if hasattr(req.type, "value") else str(req.type)
        priority_str = None
        if req.priority is not None:
            priority_str = req.priority.value if hasattr(req.priority, "value") else str(req.priority)
        requirements_data.append({
            "document_id": document_id,
            "requirement_id": req.id,
            "text": req.text,
            "ai_suggested": req.text,
            "section_id": section_id,
            "type": type_str,
            "priority": priority_str,
            "page_number": req.source_page if hasattr(req, "source_page") else req.page_number,
            "bbox": None,
            "subitems": req.subitems if hasattr(req, "subitems") else None,
            "discipline": getattr(req, "suggested_discipline", None),
            "source_quote": getattr(req, "source_quote", None),
            "lifecycle_status": "extracted",
        })
    logger.debug(f"[CRUD SAVE] Bulk inserting {len(requirements_data)} requirements")
    db.bulk_insert_mappings(Requirement, requirements_data)
    db.commit()
    return len(requirements_data)
