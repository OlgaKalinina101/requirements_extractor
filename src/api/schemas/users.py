"""Users API schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    """Create user request."""

    email: str = Field(..., description="User email")
    password: str = Field(..., description="Password")
    full_name: Optional[str] = Field(None, description="Full name")
    role: str = Field(default="user", description="User role")


class UpdateUserRequest(BaseModel):
    """Update user request."""

    full_name: Optional[str] = Field(None, description="Full name")
    role: Optional[str] = Field(None, description="Role")
    is_active: Optional[bool] = Field(None, description="Active status")
    password: Optional[str] = Field(None, description="New password")
