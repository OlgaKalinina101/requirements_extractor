"""Document CRUD operations."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.database.models import Document


def create_document(
    db: Session,
    filename: str,
    file_path: str,
    total_pages: Optional[int] = None,
    project_id: Optional[int] = None,
    model_used: Optional[str] = None,
) -> Document:
    """Create a new document record."""
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
    """Get document by ID."""
    return db.query(Document).filter(Document.id == document_id).first()


def get_all_documents(db: Session, skip: int = 0, limit: int = 100) -> List[Document]:
    """Get all documents with pagination."""
    return db.query(Document).offset(skip).limit(limit).all()


def update_document_status(
    db: Session,
    document_id: int,
    status: str,
    total_pages: Optional[int] = None,
) -> Optional[Document]:
    """Update document status."""
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
