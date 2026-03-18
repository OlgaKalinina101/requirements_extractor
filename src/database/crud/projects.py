"""Project CRUD operations."""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload, load_only
from sqlalchemy import func

from src.database.models import Project, Document, Requirement


def create_project(
    db: Session,
    name: str,
    code: Optional[str] = None,
    description: Optional[str] = None,
    requirement_manager_id: Optional[int] = None,
) -> Project:
    """Create a new project."""
    db_project = Project(
        name=name,
        code=code,
        description=description,
        status="active",
        requirement_manager_id=requirement_manager_id,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_project(db: Session, project_id: int) -> Optional[Project]:
    """Get project by ID."""
    return (
        db.query(Project)
        .options(joinedload(Project.requirement_manager))
        .filter(Project.id == project_id)
        .first()
    )


def get_project_by_code(db: Session, code: str) -> Optional[Project]:
    """Get project by unique code."""
    return db.query(Project).filter(Project.code == code).first()


def get_all_projects(db: Session, skip: int = 0, limit: int = 100, project_id: Optional[int] = None) -> List[Project]:
    """Get all projects with pagination. Optionally filter by project_id (single project)."""
    q = db.query(Project).options(
        joinedload(Project.documents).load_only(Document.id),
        joinedload(Project.requirement_manager),
    )
    if project_id is not None:
        q = q.filter(Project.id == project_id)
    return q.order_by(Project.updated_at.desc()).offset(skip).limit(limit).all()


def get_project_counts(db: Session, project_ids: List[int]) -> Dict[int, Dict[str, int]]:
    """Return doc/req counts for a list of project IDs."""
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
    """Return requirement counts for a list of document IDs."""
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
    requirement_manager_id: Optional[int] = None,
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
    if requirement_manager_id is not None:
        db_project.requirement_manager_id = requirement_manager_id if requirement_manager_id else None
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
