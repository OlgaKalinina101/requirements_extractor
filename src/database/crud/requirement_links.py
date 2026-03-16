"""CRUD operations for requirement links."""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.database.models import RequirementLink, Requirement


def get_links_for_requirement(db: Session, requirement_id: int) -> List[RequirementLink]:
    """Get all links where the requirement is source or target."""
    outgoing = (
        db.query(RequirementLink)
        .filter(RequirementLink.source_requirement_id == requirement_id)
        .all()
    )
    incoming = (
        db.query(RequirementLink)
        .filter(RequirementLink.target_requirement_id == requirement_id)
        .all()
    )
    return outgoing + incoming


def get_outgoing_links(db: Session, requirement_id: int) -> List[RequirementLink]:
    """Get links where this requirement is the source."""
    return (
        db.query(RequirementLink)
        .filter(RequirementLink.source_requirement_id == requirement_id)
        .all()
    )


def get_incoming_links(db: Session, requirement_id: int) -> List[RequirementLink]:
    """Get links where this requirement is the target."""
    return (
        db.query(RequirementLink)
        .filter(RequirementLink.target_requirement_id == requirement_id)
        .all()
    )


def create_link(
    db: Session,
    source_requirement_id: int,
    target_requirement_id: int,
    link_type: str,
) -> Optional[RequirementLink]:
    """Create a link between two requirements."""
    if source_requirement_id == target_requirement_id:
        return None
    # Check both requirements exist
    src = db.query(Requirement).filter(Requirement.id == source_requirement_id).first()
    tgt = db.query(Requirement).filter(Requirement.id == target_requirement_id).first()
    if not src or not tgt:
        return None
    # Check duplicate
    existing = (
        db.query(RequirementLink)
        .filter(
            RequirementLink.source_requirement_id == source_requirement_id,
            RequirementLink.target_requirement_id == target_requirement_id,
            RequirementLink.link_type == link_type,
        )
        .first()
    )
    if existing:
        return existing
    link = RequirementLink(
        source_requirement_id=source_requirement_id,
        target_requirement_id=target_requirement_id,
        link_type=link_type,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def delete_link(db: Session, link_id: int) -> bool:
    """Delete a link by ID."""
    link = db.query(RequirementLink).filter(RequirementLink.id == link_id).first()
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True


def get_link(db: Session, link_id: int) -> Optional[RequirementLink]:
    """Get a link by ID."""
    return db.query(RequirementLink).filter(RequirementLink.id == link_id).first()
