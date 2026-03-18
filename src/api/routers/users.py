"""Users management endpoints (admin)."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import CreateUserRequest, UpdateUserRequest
from src.api.serializers import user_to_dict
from src.database.database import get_db
from src.database import crud
from src.auth.dependencies import get_current_user, require_admin
from src.auth.password import hash_password

router = APIRouter(tags=["users"])


@router.get("")
async def list_users(
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """List all users. Any authenticated user can view (for assignee pickers)."""
    users = crud.list_users(db)
    return [user_to_dict(u) for u in users]


@router.post("", status_code=201)
async def create_user(
    request: CreateUserRequest,
    db=Depends(get_db),
    _current=Depends(require_admin),
):
    """Create a new user. Admin only."""
    if crud.get_user_by_email(db, request.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if request.role not in ("admin", "manager", "department_head", "user"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user = crud.create_user(
        db,
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
    )
    return user_to_dict(user)


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    db=Depends(get_db),
    _current=Depends(require_admin),
):
    """Update user. Admin only."""
    user = crud.update_user(
        db,
        user_id,
        full_name=request.full_name,
        role=request.role,
        is_active=request.is_active,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.password:
        crud.update_user_password(db, user_id, hash_password(request.password))
        db.refresh(user)

    return user_to_dict(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    """Deactivate (soft-delete) a user. Admin only."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user = crud.update_user(db, user_id, is_active=False)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
