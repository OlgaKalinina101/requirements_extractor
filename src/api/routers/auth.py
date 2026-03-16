"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import LoginRequest, LoginResponse
from src.database.database import get_db
from src.database import crud
from src.auth.dependencies import get_current_user
from src.auth.password import verify_password
from src.auth.jwt import create_access_token

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db=Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = crud.get_user_by_email(db, request.email)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(data={"sub": str(user.id)})
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    )


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """Get current authenticated user."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }
