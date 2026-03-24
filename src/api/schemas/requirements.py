"""Requirements API schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class CreateRequirementRequest(BaseModel):
    """Request model for manually creating a requirement."""

    text: str = Field(..., description="Requirement text", min_length=1)
    requirement_id: Optional[str] = Field(None, description="Custom ID (e.g. REQ-1-001). Auto-generated if omitted.")
    type: Optional[str] = Field(None, description="Requirement type")
    priority: Optional[str] = Field(None, description="Requirement priority")
    discipline: Optional[str] = Field(None, description="Discipline")
    page_number: Optional[int] = Field(None, description="Page number in document")


class EditRequirementRequest(BaseModel):
    """Request model for editing a requirement."""

    edited_text: str = Field(..., description="New requirement text", min_length=1)
    reason: Optional[str] = Field(None, description="Reason for editing")
    edited_by: Optional[str] = Field(None, description="User who edited the requirement")
    type: Optional[str] = Field(None, description="Requirement type override")
    priority: Optional[str] = Field(None, description="Requirement priority override")
    discipline: Optional[str] = Field(None, description="Discipline")
    verification_method: Optional[str] = Field(None, description="Verification method (Analysis, Test, etc.)")
    deadline: Optional[date] = Field(None, description="Due date for execution")
    parent_id: Optional[int] = Field(None, description="Parent requirement ID for hierarchy")
    lifecycle_status: Optional[str] = Field(None, description="Lifecycle status (extracted, verification, accepted, assigned, in_progress, completed, closed)")


class RejectRequirementRequest(BaseModel):
    """Request model for rejecting a requirement."""

    reason: Optional[str] = Field(None, description="Reason for rejection")


class AssignRequest(BaseModel):
    """Request model for assigning a requirement."""

    assignee_id: Optional[int] = Field(None, description="Assignee user ID (null to unassign)")
    deadline: Optional[date] = Field(None, description="Due date for the assignment")


class SetStatusRequest(BaseModel):
    """Request model for setting requirement status."""

    status: str = Field(..., description="New status")


class SetLifecycleStatusRequest(BaseModel):
    """Request model for setting requirement lifecycle status."""

    lifecycle_status: str = Field(..., description="New lifecycle status (extracted, verification, accepted, assigned, in_progress, completed, closed)")


class CreateLinkRequest(BaseModel):
    """Request model for creating a requirement link."""

    target_requirement_id: int = Field(..., description="ID of the target requirement")
    link_type: str = Field(..., description="Link type (depends_on, conflicts_with, derived_from, parent_child)")
