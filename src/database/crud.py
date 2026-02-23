"""CRUD operations for database models.

This module provides database operations for documents, sections,
requirements, and coverage metrics.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from src.database.models import (
    Project,
    Document,
    Section,
    Requirement,
    CoverageMetrics,
)
from src.models import RequirementType, RequirementPriority


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
    return db.query(Project).order_by(Project.updated_at.desc()).offset(skip).limit(limit).all()


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


def _resolve_requirement_type(value) -> Optional[RequirementType]:
    """Convert various type representations to RequirementType enum."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[CRUD] _resolve_requirement_type called with: {value!r} (type: {type(value).__name__})")
    
    if value is None:
        return None
    if isinstance(value, RequirementType):
        logger.info(f"[CRUD] Already RequirementType enum: {value}")
        return value
    if isinstance(value, str):
        try:
            result = RequirementType[value]
            logger.info(f"[CRUD] Converted string '{value}' to enum by name: {result}")
            return result
        except KeyError:
            pass
        try:
            result = RequirementType(value)
            logger.info(f"[CRUD] Converted string '{value}' to enum by value: {result}")
            return result
        except ValueError:
            pass
        mapping = {
            "technical": RequirementType.TECHNICAL,
            "organizational": RequirementType.ORGANIZATIONAL,
            "documentation": RequirementType.DOCUMENTATION,
            "functional": RequirementType.FUNCTIONAL,
            "non_functional": RequirementType.NON_FUNCTIONAL,
            "nonfunctional": RequirementType.NON_FUNCTIONAL,
            "other": RequirementType.OTHER,
        }
        result = mapping.get(value.lower(), RequirementType.OTHER)
        logger.info(f"[CRUD] Converted string '{value}' via mapping: {result}")
        return result
    logger.warning(f"[CRUD] Could not convert {value!r}, returning OTHER")
    return RequirementType.OTHER


def _resolve_requirement_priority(value) -> Optional[RequirementPriority]:
    """Convert various priority representations to RequirementPriority enum."""
    if value is None:
        return None
    if isinstance(value, RequirementPriority):
        return value
    if isinstance(value, str):
        try:
            return RequirementPriority[value]
        except KeyError:
            pass
        try:
            return RequirementPriority(value)
        except ValueError:
            pass
        mapping = {
            "mandatory": RequirementPriority.MANDATORY,
            "recommended": RequirementPriority.RECOMMENDED,
            "optional": RequirementPriority.OPTIONAL,
        }
        return mapping.get(value.lower(), RequirementPriority.MANDATORY)
    return RequirementPriority.MANDATORY


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
    return db.query(Requirement).filter(Requirement.id == requirement_id).first()


def get_requirements_by_document(
    db: Session,
    document_id: int,
    status: Optional[str] = None,
    type: Optional[RequirementType] = None,
    skip: int = 0,
    limit: int = 1000,
) -> List[Requirement]:
    """Get all requirements for a document with optional filters.
    
    Args:
        db: Database session
        document_id: Document ID
        status: Filter by status (optional)
        type: Filter by type (optional)
        skip: Number of records to skip
        limit: Maximum number of records to return
    
    Returns:
        List of Requirement instances
    """
    query = db.query(Requirement).filter(Requirement.document_id == document_id)
    
    if status:
        query = query.filter(Requirement.status == status)
    if type:
        query = query.filter(Requirement.type == type)
    
    return query.offset(skip).limit(limit).all()


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
    
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


# ========== Coverage Metrics CRUD ==========

def create_or_update_coverage_metrics(
    db: Session,
    document_id: int,
    total_pages: int,
    processed_pages: int,
    skipped_pages: Optional[List[int]] = None,
    requirements_count: int = 0,
    requirements_by_type: Optional[Dict[str, int]] = None,
) -> CoverageMetrics:
    """Create or update coverage metrics for a document.
    
    Args:
        db: Database session
        document_id: Document ID
        total_pages: Total pages in document
        processed_pages: Number of processed pages
        skipped_pages: List of skipped page numbers (optional)
        requirements_count: Total number of requirements
        requirements_by_type: Dictionary with counts by type (optional)
    
    Returns:
        Created or updated CoverageMetrics instance
    """
    # Check if metrics already exist
    existing = db.query(CoverageMetrics).filter(
        CoverageMetrics.document_id == document_id
    ).first()
    
    coverage_percent = (processed_pages / total_pages * 100) if total_pages > 0 else 0.0
    
    if existing:
        # Update existing
        existing.total_pages = total_pages
        existing.processed_pages = processed_pages
        existing.skipped_pages = skipped_pages
        existing.coverage_percent = coverage_percent
        existing.requirements_count = requirements_count
        existing.requirements_by_type = requirements_by_type
        existing.calculated_at = datetime.now()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        db_metrics = CoverageMetrics(
            document_id=document_id,
            total_pages=total_pages,
            processed_pages=processed_pages,
            skipped_pages=skipped_pages,
            coverage_percent=coverage_percent,
            requirements_count=requirements_count,
            requirements_by_type=requirements_by_type,
        )
        db.add(db_metrics)
        db.commit()
        db.refresh(db_metrics)
        return db_metrics


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
