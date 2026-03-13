"""CRUD operations for database models.

This module provides database operations for documents, sections,
requirements, and coverage metrics.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

logger = logging.getLogger("api")  # Use api logger so it outputs to console

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, select

from src.database.models import (
    Project,
    Document,
    Section,
    Requirement,
    CoverageMetrics,
    User,
    Comment,
    DictionaryItem,
)
from src.models import RequirementType


# ========== User CRUD ==========


def create_user(
    db: Session,
    email: str,
    hashed_password: str,
    full_name: Optional[str] = None,
    role: str = "user",
) -> User:
    """Create a new user."""
    db_user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """List all users."""
    return db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()


def update_user(
    db: Session,
    user_id: int,
    *,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[User]:
    """Update user fields."""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    if full_name is not None:
        user.full_name = full_name
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


# ========== Project CRUD ==========

def create_project(
    db: Session,
    name: str,
    code: Optional[str] = None,
    description: Optional[str] = None,
) -> Project:
    """Create a new project."""
    db_project = Project(
        name=name,
        code=code,
        description=description,
        status="active",
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_project(db: Session, project_id: int) -> Optional[Project]:
    """Get project by ID."""
    return db.query(Project).filter(Project.id == project_id).first()


def get_project_by_code(db: Session, code: str) -> Optional[Project]:
    """Get project by unique code."""
    return db.query(Project).filter(Project.code == code).first()


def get_all_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
    """Get all projects with pagination."""
    return (
        db.query(Project)
        .options(joinedload(Project.documents).load_only(Document.id))
        .order_by(Project.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_project_counts(db: Session, project_ids: List[int]) -> Dict[int, Dict[str, int]]:
    """Return doc/req counts for a list of project IDs in two queries (no N+1)."""
    doc_counts = (
        db.query(Document.project_id, func.count(Document.id).label("doc_count"))
        .filter(Document.project_id.in_(project_ids))
        .group_by(Document.project_id)
        .all()
    )
    req_counts = (
        db.query(Document.project_id, func.count(Requirement.id).label("req_count"))
        .join(Requirement, Requirement.document_id == Document.id)
        .filter(Document.project_id.in_(project_ids))
        .group_by(Document.project_id)
        .all()
    )
    result: Dict[int, Dict[str, int]] = {pid: {"doc_count": 0, "req_count": 0} for pid in project_ids}
    for pid, count in doc_counts:
        result[pid]["doc_count"] = count
    for pid, count in req_counts:
        result[pid]["req_count"] = count
    return result


def get_document_req_counts(db: Session, document_ids: List[int]) -> Dict[int, int]:
    """Return requirement counts for a list of document IDs in one query (no N+1)."""
    rows = (
        db.query(Requirement.document_id, func.count(Requirement.id).label("req_count"))
        .filter(Requirement.document_id.in_(document_ids))
        .group_by(Requirement.document_id)
        .all()
    )
    return {doc_id: count for doc_id, count in rows}


def update_project(
    db: Session,
    project_id: int,
    name: Optional[str] = None,
    code: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Project]:
    """Update a project."""
    db_project = get_project(db, project_id)
    if not db_project:
        return None
    
    if name is not None:
        db_project.name = name
    if code is not None:
        db_project.code = code
    if description is not None:
        db_project.description = description
    if status is not None:
        db_project.status = status
    
    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, project_id: int) -> bool:
    """Delete a project and all its documents (CASCADE)."""
    db_project = get_project(db, project_id)
    if not db_project:
        return False
    db.delete(db_project)
    db.commit()
    return True


def get_documents_by_project(db: Session, project_id: int) -> List[Document]:
    """Get all documents for a project."""
    return db.query(Document).filter(Document.project_id == project_id).order_by(Document.uploaded_at.desc()).all()


# ========== Document CRUD ==========

def create_document(
    db: Session,
    filename: str,
    file_path: str,
    total_pages: Optional[int] = None,
    project_id: Optional[int] = None,
    model_used: Optional[str] = None,
) -> Document:
    """Create a new document record.
    
    Args:
        db: Database session
        filename: Original filename
        file_path: Path to stored PDF file
        total_pages: Total number of pages (optional)
        project_id: Project ID (optional)
        model_used: AI model used for extraction (optional)
    
    Returns:
        Created Document instance
    """
    db_document = Document(
        filename=filename,
        file_path=file_path,
        status="pending",
        total_pages=total_pages,
        project_id=project_id,
        model_used=model_used,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


def get_document(db: Session, document_id: int) -> Optional[Document]:
    """Get document by ID.
    
    Args:
        db: Database session
        document_id: Document ID
    
    Returns:
        Document instance or None if not found
    """
    return db.query(Document).filter(Document.id == document_id).first()


def get_all_documents(db: Session, skip: int = 0, limit: int = 100) -> List[Document]:
    """Get all documents with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
    
    Returns:
        List of Document instances
    """
    return db.query(Document).offset(skip).limit(limit).all()


def update_document_status(
    db: Session,
    document_id: int,
    status: str,
    total_pages: Optional[int] = None,
) -> Optional[Document]:
    """Update document status.
    
    Args:
        db: Database session
        document_id: Document ID
        status: New status (pending, processing, completed, failed)
        total_pages: Total pages (optional)
    
    Returns:
        Updated Document instance or None if not found
    """
    db_document = get_document(db, document_id)
    if not db_document:
        return None
    
    db_document.status = status
    if total_pages is not None:
        db_document.total_pages = total_pages
    if status == "completed":
        db_document.processed_at = datetime.now()
    
    db.commit()
    db.refresh(db_document)
    return db_document


# ========== Section CRUD ==========

def create_section(
    db: Session,
    document_id: int,
    section_number: Optional[str] = None,
    title: Optional[str] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
) -> Section:
    """Create a new section record.
    
    Args:
        db: Database session
        document_id: Document ID
        section_number: Section number
        title: Section title
        page_start: Starting page number
        page_end: Ending page number
    
    Returns:
        Created Section instance
    """
    db_section = Section(
        document_id=document_id,
        section_number=section_number,
        title=title,
        page_start=page_start,
        page_end=page_end,
    )
    db.add(db_section)
    db.commit()
    db.refresh(db_section)
    return db_section


def get_sections_by_document(db: Session, document_id: int) -> List[Section]:
    """Get all sections for a document.
    
    Args:
        db: Database session
        document_id: Document ID
    
    Returns:
        List of Section instances
    """
    return db.query(Section).filter(Section.document_id == document_id).all()


# ========== Requirement CRUD ==========

def create_requirement(
    db: Session,
    document_id: int,
    requirement_id: str,
    text: str,
    ai_suggested: str,
    section_id: Optional[int] = None,
    type: Optional[Any] = None,  # Can be enum, string, or None
    priority: Optional[Any] = None,  # Can be enum, string, or None
    page_number: Optional[int] = None,
    bbox: Optional[Dict[str, Any]] = None,
) -> Requirement:
    """Create a new requirement record.
    
    Args:
        db: Database session
        document_id: Document ID
        requirement_id: Unique requirement identifier
        text: Requirement text
        ai_suggested: Original AI-suggested text
        section_id: Section ID (optional)
        type: Requirement type (optional, any format)
        priority: Requirement priority (optional, any format)
        page_number: Page number (optional)
        bbox: Bounding box coordinates (optional)
    
    Returns:
        Created Requirement instance
    """
    # Convert enum to string value if needed
    type_str = None
    if type is not None:
        if hasattr(type, 'value'):
            type_str = type.value
        else:
            type_str = str(type)
    
    priority_str = None
    if priority is not None:
        if hasattr(priority, 'value'):
            priority_str = priority.value
        else:
            priority_str = str(priority)
    
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
    )
    db.add(db_requirement)
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


def get_requirement(db: Session, requirement_id: int) -> Optional[Requirement]:
    """Get requirement by ID.
    
    Args:
        db: Database session
        requirement_id: Requirement ID
    
    Returns:
        Requirement instance or None if not found
    """
    return (
        db.query(Requirement)
        .options(joinedload(Requirement.section))
        .filter(Requirement.id == requirement_id)
        .first()
    )


def get_requirements_by_document(
    db: Session,
    document_id: int,
    status: Optional[str] = None,
    type: Optional[RequirementType] = None,
    assignee_id: Optional[int] = None,
    skip: int = 0,
    limit: Optional[int] = None,
) -> List[Requirement]:
    """Get all requirements for a document with optional filters.

    Section relationship is eagerly loaded so callers can access
    req.section.section_number / req.section.title without extra queries.

    Args:
        db: Database session
        document_id: Document ID
        status: Filter by status (optional)
        type: Filter by type (optional)
        skip: Number of records to skip
        limit: Maximum records to return; None means no limit (used for exports)

    Returns:
        List of Requirement instances (with .section pre-loaded)
    """
    query = (
        db.query(Requirement)
        .options(joinedload(Requirement.section))
        .filter(Requirement.document_id == document_id)
    )

    if status:
        query = query.filter(Requirement.status == status)
    if type:
        query = query.filter(Requirement.type == type)
    if assignee_id is not None:
        query = query.filter(Requirement.assignee_id == assignee_id)

    query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def accept_requirement(
    db: Session,
    requirement_id: int,
) -> Optional[Requirement]:
    """Accept a requirement (mark as accepted).
    
    Args:
        db: Database session
        requirement_id: Requirement ID
    
    Returns:
        Updated Requirement instance or None if not found
    """
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
    """Reject a requirement (mark as rejected).
    
    Args:
        db: Database session
        requirement_id: Requirement ID
        reason: Rejection reason (optional)
    
    Returns:
        Updated Requirement instance or None if not found
    """
    db_requirement = get_requirement(db, requirement_id)
    if not db_requirement:
        return None
    
    db_requirement.status = "rejected"
    db_requirement.edit_reason = reason
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


def edit_requirement(
    db: Session,
    requirement_id: int,
    edited_text: str,
    reason: Optional[str] = None,
    edited_by: Optional[str] = None,
    req_type: Optional[str] = None,
    priority: Optional[str] = None,
) -> Optional[Requirement]:
    """Edit a requirement (mark as modified).
    
    Args:
        db: Database session
        requirement_id: Requirement ID
        edited_text: New requirement text
        reason: Reason for editing (optional)
        edited_by: User who edited (optional)
    
    Returns:
        Updated Requirement instance or None if not found
    """
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
    
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


# ========== Coverage Metrics CRUD ==========

def get_coverage_metrics(db: Session, document_id: int) -> Optional[CoverageMetrics]:
    """Get coverage metrics for a document.
    
    Args:
        db: Database session
        document_id: Document ID
    
    Returns:
        CoverageMetrics instance or None if not found
    """
    return db.query(CoverageMetrics).filter(
        CoverageMetrics.document_id == document_id
    ).first()


def create_coverage_metrics(
    db: Session,
    document_id: int,
    total_pages: int,
    processed_pages: int,
    skipped_pages: List[int],
    coverage_percent: float,
    requirements_count: int
) -> CoverageMetrics:
    """Create coverage metrics for a document.
    
    Args:
        db: Database session
        document_id: Document ID
        total_pages: Total number of pages in document
        processed_pages: Number of pages with requirements
        skipped_pages: List of page numbers that were skipped
        coverage_percent: Percentage of pages processed (0-100)
        requirements_count: Total number of requirements extracted
    
    Returns:
        Created CoverageMetrics instance
    """
    metrics = CoverageMetrics(
        document_id=document_id,
        total_pages=total_pages,
        processed_pages=processed_pages,
        skipped_pages=skipped_pages,
        coverage_percent=coverage_percent,
        requirements_count=requirements_count,
        calculated_at=datetime.now(timezone.utc)
    )
    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    return metrics


def bulk_create_requirements(
    db: Session,
    document_id: int,
    section_id: int,
    requirements: List[Any]
) -> int:
    """Bulk create requirements for a section (OPTIMIZED for speed).
    
    Args:
        db: Database session
        document_id: Document ID
        section_id: Section ID
        requirements: List of Requirement objects from src.models
    
    Returns:
        Number of requirements created
    """
    if not requirements:
        return 0
    
    # Prepare bulk insert data
    requirements_data = []
    for req in requirements:
        # Convert enum to string value if needed
        type_str = None
        if req.type is not None:
            if hasattr(req.type, 'value'):
                type_str = req.type.value
            else:
                type_str = str(req.type)
        
        priority_str = None
        if req.priority is not None:
            if hasattr(req.priority, 'value'):
                priority_str = req.priority.value
            else:
                priority_str = str(req.priority)
        
        requirements_data.append({
            'document_id': document_id,
            'requirement_id': req.id,
            'text': req.text,
            'ai_suggested': req.text,  # Original AI text
            'section_id': section_id,
            'type': type_str,
            'priority': priority_str,
            'page_number': req.source_page if hasattr(req, 'source_page') else req.page_number,
            'bbox': None,
            'subitems': req.subitems if hasattr(req, 'subitems') else None,
        })
    
    logger.debug(f"[CRUD SAVE] Bulk inserting {len(requirements_data)} requirements")
    # Bulk insert using SQLAlchemy
    db.bulk_insert_mappings(Requirement, requirements_data)
    db.commit()
    
    return len(requirements_data)


# ========== Comments CRUD ==========


def create_comment(db: Session, requirement_id: int, user_id: int, text: str) -> Comment:
    """Add a comment to a requirement."""
    comment = Comment(requirement_id=requirement_id, user_id=user_id, text=text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comments(db: Session, requirement_id: int) -> List[Comment]:
    """List all comments for a requirement, oldest first."""
    return (
        db.query(Comment)
        .filter(Comment.requirement_id == requirement_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


def delete_comment(db: Session, comment_id: int, user_id: int) -> bool:
    """Delete a comment. Only author can delete. Returns True if deleted."""
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.user_id == user_id).first()
    if not comment:
        return False
    db.delete(comment)
    db.commit()
    return True


# ========== Dictionary CRUD ==========

VALID_DICT_TYPES = {"requirement_types", "priorities", "statuses"}


def get_dictionary_items(db: Session, dict_type: str) -> List[DictionaryItem]:
    """Get all items for a given dictionary type, ordered by sort_order."""
    return (
        db.query(DictionaryItem)
        .filter(DictionaryItem.dict_type == dict_type)
        .order_by(DictionaryItem.sort_order.asc(), DictionaryItem.id.asc())
        .all()
    )


def get_dictionary_item(db: Session, item_id: int) -> Optional[DictionaryItem]:
    return db.query(DictionaryItem).filter(DictionaryItem.id == item_id).first()


def create_dictionary_item(db: Session, dict_type: str, data: Dict[str, Any]) -> DictionaryItem:
    item = DictionaryItem(
        dict_type=dict_type,
        code=data.get("code"),
        name=data["name"],
        description=data.get("description"),
        color=data.get("color"),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_dictionary_item(db: Session, item_id: int, data: Dict[str, Any]) -> Optional[DictionaryItem]:
    item = db.query(DictionaryItem).filter(DictionaryItem.id == item_id).first()
    if not item:
        return None
    for field in ("code", "name", "description", "color", "sort_order", "is_active"):
        if field in data:
            setattr(item, field, data[field])
    db.commit()
    db.refresh(item)
    return item


def delete_dictionary_item(db: Session, item_id: int) -> bool:
    item = db.query(DictionaryItem).filter(DictionaryItem.id == item_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def seed_dictionary_defaults(db: Session) -> None:
    """Populate dictionaries with default values if they are empty."""
    defaults = {
        "requirement_types": [
            {"code": "Supply",         "name": "Supply",         "description": "Состав поставки, перечень оборудования", "color": "blue-darken-1", "sort_order": 1},
            {"code": "Technical",      "name": "Technical",      "description": "Технические параметры и характеристики",  "color": "cyan-darken-1",  "sort_order": 2},
            {"code": "Functional",     "name": "Functional",     "description": "Функциональное поведение системы",        "color": "green-darken-1", "sort_order": 3},
            {"code": "Performance",    "name": "Performance",    "description": "Производительность и метрики",            "color": "teal-darken-1",  "sort_order": 4},
            {"code": "Safety",         "name": "Safety",         "description": "Безопасность и защита",                  "color": "red-darken-1",   "sort_order": 5},
            {"code": "Documentation",  "name": "Documentation",  "description": "Документирование и отчётность",          "color": "brown",          "sort_order": 6},
            {"code": "Interface",      "name": "Interface",      "description": "Интерфейсы и протоколы",                 "color": "purple",         "sort_order": 7},
            {"code": "Constraint",     "name": "Constraint",     "description": "Ограничения и граничные условия",        "color": "orange-darken-1","sort_order": 8},
            {"code": "Process",        "name": "Process",        "description": "Процессы и рабочие процедуры",           "color": "lime-darken-2",  "sort_order": 9},
            {"code": "Unknown",        "name": "Unknown",        "description": "Тип не определён",                      "color": "grey",           "sort_order": 10},
        ],
        "priorities": [
            {"code": "Mandatory",    "name": "Mandatory",    "description": "Обязательное требование",    "color": "red",    "sort_order": 1},
            {"code": "Recommended",  "name": "Recommended",  "description": "Рекомендуемое требование",  "color": "orange", "sort_order": 2},
            {"code": "Optional",     "name": "Optional",     "description": "Необязательное требование", "color": "blue",   "sort_order": 3},
            {"code": "Unknown",      "name": "Unknown",      "description": "Приоритет не определён",    "color": "grey",   "sort_order": 4},
        ],
        "statuses": [
            {"code": "pending",     "name": "На рассмотрении", "description": "Ожидает проверки менеджером",  "color": "orange", "sort_order": 1},
            {"code": "accepted",    "name": "Принято",         "description": "Требование подтверждено",      "color": "green",  "sort_order": 2},
            {"code": "rejected",    "name": "Отклонено",       "description": "Требование отклонено",         "color": "red",    "sort_order": 3},
            {"code": "modified",    "name": "Изменено",        "description": "Требование отредактировано",   "color": "blue",   "sort_order": 4},
            {"code": "in_progress", "name": "В работе",        "description": "Исполнитель приступил",        "color": "cyan",   "sort_order": 5},
            {"code": "done",        "name": "Выполнено",       "description": "Исполнитель завершил",         "color": "teal",   "sort_order": 6},
            {"code": "blocked",     "name": "Заблокировано",   "description": "Выполнение заблокировано",     "color": "grey",   "sort_order": 7},
        ],
    }
    for dict_type, items in defaults.items():
        existing = db.query(DictionaryItem).filter(DictionaryItem.dict_type == dict_type).count()
        if existing == 0:
            for item_data in items:
                db.add(DictionaryItem(dict_type=dict_type, **item_data))
    db.commit()

