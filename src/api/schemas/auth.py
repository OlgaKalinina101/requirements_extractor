"""Auth API schemas."""

from typing import Any, Dict

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request body."""

    email: str = Field(..., description="User email")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Login response with JWT."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: Dict[str, Any] = Field(..., description="User info")
