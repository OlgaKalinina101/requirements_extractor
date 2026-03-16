"""User CRUD operations."""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.database.models import User


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


def update_user_password(db: Session, user_id: int, hashed_password: str) -> None:
    """Update user password by user ID."""
    db.query(User).filter(User.id == user_id).update({"hashed_password": hashed_password})
    db.commit()
