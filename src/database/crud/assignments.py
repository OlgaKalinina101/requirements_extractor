"""Assignment CRUD operations."""

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from src.database.models import Assignment


def create_assignment(
    db: Session,
    requirement_id: int,
    assignee_id: int,
    assigned_by_id: int,
    deadline: Optional[date] = None,
) -> Assignment:
    """Create a new assignment record, deactivating any previous active assignment."""
    db.query(Assignment).filter(
        Assignment.requirement_id == requirement_id,
        Assignment.is_active.is_(True),
    ).update({"is_active": False})

    assignment = Assignment(
        requirement_id=requirement_id,
        assignee_id=assignee_id,
        assigned_by_id=assigned_by_id,
        deadline=deadline,
        is_active=True,
    )
    db.add(assignment)
    db.flush()
    return assignment


def deactivate_assignments(db: Session, requirement_id: int) -> int:
    """Deactivate all assignments for a requirement (unassign)."""
    count = (
        db.query(Assignment)
        .filter(
            Assignment.requirement_id == requirement_id,
            Assignment.is_active.is_(True),
        )
        .update({"is_active": False})
    )
    db.flush()
    return count


def get_active_assignment(db: Session, requirement_id: int) -> Optional[Assignment]:
    """Get the current active assignment for a requirement."""
    return (
        db.query(Assignment)
        .filter(
            Assignment.requirement_id == requirement_id,
            Assignment.is_active.is_(True),
        )
        .first()
    )


def get_assignment_history(db: Session, requirement_id: int) -> List[Assignment]:
    """Get full assignment history for a requirement (newest first)."""
    return (
        db.query(Assignment)
        .filter(Assignment.requirement_id == requirement_id)
        .order_by(Assignment.assigned_at.desc())
        .all()
    )
