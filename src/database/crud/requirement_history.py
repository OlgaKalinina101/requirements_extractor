"""Requirement history (audit log) CRUD operations."""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.database.models import RequirementHistory


def create_history_entry(
    db: Session,
    requirement_id: int,
    action: str,
    user_id: Optional[int] = None,
    field_name: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    comment: Optional[str] = None,
) -> RequirementHistory:
    """Create an audit log entry for a requirement change."""
    entry = RequirementHistory(
        requirement_id=requirement_id,
        user_id=user_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        comment=comment,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_requirement_history(
    db: Session,
    requirement_id: int,
    limit: int = 100,
) -> List[RequirementHistory]:
    """Get history entries for a requirement, newest first."""
    return (
        db.query(RequirementHistory)
        .filter(RequirementHistory.requirement_id == requirement_id)
        .order_by(desc(RequirementHistory.created_at))
        .limit(limit)
        .all()
    )
