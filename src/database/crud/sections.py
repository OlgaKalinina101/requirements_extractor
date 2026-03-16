"""Section CRUD operations."""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.database.models import Section


def create_section(
    db: Session,
    document_id: int,
    section_number: Optional[str] = None,
    title: Optional[str] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
) -> Section:
    """Create a new section record."""
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
    """Get all sections for a document."""
    return db.query(Section).filter(Section.document_id == document_id).all()
