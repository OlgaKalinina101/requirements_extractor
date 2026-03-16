"""Requirements API schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class EditRequirementRequest(BaseModel):
    """Request model for editing a requirement."""

    edited_text: str = Field(..., description="New requirement text", min_length=1)
    reason: Optional[str] = Field(None, description="Reason for editing")
    edited_by: Optional[str] = Field(None, description="User who edited the requirement")
    type: Optional[str] = Field(None, description="Requirement type override")
    priority: Optional[str] = Field(None, description="Requirement priority override")


class RejectRequirementRequest(BaseModel):
    """Request model for rejecting a requirement."""

    reason: Optional[str] = Field(None, description="Reason for rejection")


class AssignRequest(BaseModel):
    """Request model for assigning a requirement."""

    assignee_id: Optional[int] = Field(None, description="Assignee user ID")


class SetStatusRequest(BaseModel):
    """Request model for setting requirement status."""

    status: str = Field(..., description="New status")
