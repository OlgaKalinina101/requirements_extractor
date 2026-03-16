"""Requirements API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import (
    EditRequirementRequest,
    RejectRequirementRequest,
    AssignRequest,
    SetStatusRequest,
    CommentRequest,
)
from src.api.serializers import requirement_to_dict, requirement_summary, comment_to_dict
from src.database import crud
from src.database.database import get_db
from src.auth.dependencies import get_current_user, require_manager

router = APIRouter(tags=["requirements"])
logger = logging.getLogger("api")

EXECUTION_STATUSES = {"in_progress", "done", "blocked"}
MANAGER_STATUSES = {"pending", "accepted", "rejected", "modified"}
ALL_STATUSES = EXECUTION_STATUSES | MANAGER_STATUSES


@router.get("/{requirement_id}")
async def get_requirement(
    requirement_id: int,
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """Get requirement by ID with full details."""
    try:
        requirement = crud.get_requirement(db, requirement_id)
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        return requirement_to_dict(requirement)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get requirement {requirement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{requirement_id}/accept")
async def accept_requirement_endpoint(
    requirement_id: int,
    db=Depends(get_db),
    _current=Depends(require_manager),
):
    """Accept a requirement (mark as accepted)."""
    try:
        requirement = crud.accept_requirement(db, requirement_id)
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        logger.info(f"[REVIEW] Requirement {requirement_id} accepted")
        result = requirement_summary(requirement)
        result["message"] = "Requirement accepted successfully"
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REVIEW] Failed to accept requirement {requirement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{requirement_id}/reject")
async def reject_requirement_endpoint(
    requirement_id: int,
    request: Optional[RejectRequirementRequest] = None,
    db=Depends(get_db),
    _current=Depends(require_manager),
):
    """Reject a requirement (mark as rejected)."""
    try:
        reason = request.reason if request else None
        requirement = crud.reject_requirement(db, requirement_id, reason=reason)
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        logger.info(f"[REVIEW] Requirement {requirement_id} rejected (reason: {reason or 'none'})")
        result = requirement_summary(requirement)
        result["message"] = "Requirement rejected successfully"
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REVIEW] Failed to reject requirement {requirement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{requirement_id}/edit")
async def edit_requirement_endpoint(
    requirement_id: int,
    request: EditRequirementRequest,
    db=Depends(get_db),
    _current=Depends(require_manager),
):
    """Edit a requirement (mark as modified)."""
    try:
        requirement = crud.edit_requirement(
            db=db,
            requirement_id=requirement_id,
            edited_text=request.edited_text,
            reason=request.reason,
            edited_by=request.edited_by,
            req_type=request.type,
            priority=request.priority,
        )
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        logger.info(f"[REVIEW] Requirement {requirement_id} edited by {request.edited_by or 'unknown'}")
        result = requirement_summary(requirement)
        result["text"] = requirement.text
        result["message"] = "Requirement edited successfully"
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REVIEW] Failed to edit requirement {requirement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{requirement_id}/assign")
async def assign_requirement(
    requirement_id: int,
    request: AssignRequest,
    db=Depends(get_db),
    current_user=Depends(require_manager),
):
    """Assign (or unassign) an executor to a requirement. Manager/admin only."""
    if request.assignee_id is not None:
        assignee = crud.get_user_by_id(db, request.assignee_id)
        if not assignee:
            raise HTTPException(status_code=404, detail="User not found")

    req = crud.assign_requirement(db, requirement_id, request.assignee_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    assignee_info = None
    if req.assignee_id:
        u = crud.get_user_by_id(db, req.assignee_id)
        assignee_info = {"id": u.id, "full_name": u.full_name, "email": u.email} if u else None

    return {"requirement_id": requirement_id, "assignee": assignee_info}


@router.post("/{requirement_id}/set-status")
async def set_requirement_status(
    requirement_id: int,
    request: SetStatusRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update requirement execution status."""
    if request.status not in ALL_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {sorted(ALL_STATUSES)}",
        )

    req = crud.get_requirement(db, requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    if request.status in EXECUTION_STATUSES:
        if current_user.role == "user" and req.assignee_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only update status of requirements assigned to you",
            )
    else:
        if current_user.role not in ("admin", "manager"):
            raise HTTPException(status_code=403, detail="Manager role required")

    req = crud.update_requirement_status(db, requirement_id, request.status)
    return {"requirement_id": requirement_id, "status": req.status}


@router.get("/{requirement_id}/comments")
async def get_comments(
    requirement_id: int,
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """List comments for a requirement."""
    comments = crud.get_comments(db, requirement_id)
    result = []
    for c in comments:
        user = crud.get_user_by_id(db, c.user_id) if c.user_id else None
        result.append(comment_to_dict(c, user))
    return result


@router.post("/{requirement_id}/comments", status_code=201)
async def add_comment(
    requirement_id: int,
    request: CommentRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a comment to a requirement."""
    req = crud.get_requirement(db, requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    comment = crud.create_comment(db, requirement_id, current_user.id, request.text)
    return comment_to_dict(comment, current_user)
