"""Comment CRUD operations."""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.database.models import Comment


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


def get_comment(db: Session, comment_id: int) -> Optional[Comment]:
    """Get comment by ID."""
    return db.query(Comment).filter(Comment.id == comment_id).first()


def delete_comment(db: Session, comment_id: int, user_id: int) -> bool:
    """Delete a comment. Only author can delete. Returns True if deleted."""
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.user_id == user_id).first()
    if not comment:
        return False
    db.delete(comment)
    db.commit()
    return True


def delete_comment_by_id(db: Session, comment_id: int) -> bool:
    """Delete a comment by ID (admin force-delete). Returns True if deleted."""
    comment = get_comment(db, comment_id)
    if not comment:
        return False
    db.delete(comment)
    db.commit()
    return True
