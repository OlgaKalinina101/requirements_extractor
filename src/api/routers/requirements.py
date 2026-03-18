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
    CreateLinkRequest,
)
from src.api.serializers import requirement_to_dict, requirement_to_list_item, requirement_summary, comment_to_dict
from src.database import crud
from src.database.database import get_db
from src.auth.dependencies import get_current_user, require_manager

router = APIRouter(tags=["requirements"])
logger = logging.getLogger("api")

EXECUTION_STATUSES = {"in_progress", "done", "blocked"}
MANAGER_STATUSES = {"pending", "accepted", "rejected", "modified"}
ALL_STATUSES = EXECUTION_STATUSES | MANAGER_STATUSES


@router.get("")
async def get_all_requirements(
    project_id: Optional[int] = None,
    document_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """Get all requirements across all documents with optional filters."""
    reqs = crud.get_all_requirements(
        db,
        project_id=project_id,
        document_id=document_id,
        assignee_id=assignee_id,
        discipline=discipline,
        status=status,
        req_type=type,
        priority=priority,
        search=search,
        skip=skip,
        limit=limit,
    )
    return {"requirements": [requirement_to_list_item(r) for r in reqs], "total": len(reqs)}


@router.delete("/{requirement_id}")
async def delete_requirement(
    requirement_id: int,
    db=Depends(get_db),
    _current=Depends(require_manager),
):
    """Delete a requirement. Manager/admin only."""
    deleted = crud.delete_requirement(db, requirement_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return {"ok": True}


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
    current_user=Depends(require_manager),
):
    """Accept a requirement (mark as accepted)."""
    try:
        requirement = crud.accept_requirement(db, requirement_id)
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        crud.create_history_entry(
            db, requirement_id, "accepted",
            user_id=current_user.id, new_value="accepted",
        )
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
    current_user=Depends(require_manager),
):
    """Reject a requirement (mark as rejected)."""
    try:
        reason = request.reason if request else None
        requirement = crud.reject_requirement(db, requirement_id, reason=reason)
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
        crud.create_history_entry(
            db, requirement_id, "rejected",
            user_id=current_user.id, new_value="rejected", comment=reason,
        )
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
    current_user=Depends(require_manager),
):
    """Edit a requirement (mark as modified)."""
    try:
        req = crud.get_requirement(db, requirement_id)
        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")
        old_text = req.text
        requirement = crud.edit_requirement(
            db=db,
            requirement_id=requirement_id,
            edited_text=request.edited_text,
            reason=request.reason,
            edited_by=request.edited_by,
            req_type=request.type,
            priority=request.priority,
            discipline=request.discipline,
            verification_method=request.verification_method,
            deadline=request.deadline,
            parent_id=request.parent_id,
        )
        crud.create_history_entry(
            db, requirement_id, "edited",
            user_id=current_user.id,
            field_name="text", old_value=old_text, new_value=request.edited_text,
            comment=request.reason,
        )
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

    new_assignee = request.assignee_id
    assignee_name = None
    if new_assignee:
        u = crud.get_user_by_id(db, new_assignee)
        assignee_name = (u.full_name or u.email) if u else str(new_assignee)
    crud.create_history_entry(
        db, requirement_id, "assigned",
        user_id=current_user.id,
        field_name="assignee_id", new_value=assignee_name or "(снято)",
    )

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
        if current_user.role not in ("admin", "manager", "department_head"):
            raise HTTPException(status_code=403, detail="Manager role required")

    req = crud.update_requirement_status(db, requirement_id, request.status)
    crud.create_history_entry(
        db, requirement_id, "status_changed",
        user_id=current_user.id,
        field_name="status", new_value=request.status,
    )
    return {"requirement_id": requirement_id, "status": req.status}


@router.get("/{requirement_id}/history")
async def get_history(
    requirement_id: int,
    limit: int = 100,
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """Get audit log (timeline) for a requirement."""
    entries = crud.get_requirement_history(db, requirement_id, limit=limit)
    result = []
    for e in entries:
        user = crud.get_user_by_id(db, e.user_id) if e.user_id else None
        result.append({
            "id": e.id,
            "action": e.action,
            "field_name": e.field_name,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "comment": e.comment,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "user_name": (user.full_name or user.email) if user else None,
        })
    return result


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
    crud.create_history_entry(
        db, requirement_id, "comment_added",
        user_id=current_user.id,
        comment=request.text[:200] + ("..." if len(request.text) > 200 else ""),
    )
    return comment_to_dict(comment, current_user)


@router.post("/{requirement_id}/links", status_code=201)
async def create_requirement_link(
    requirement_id: int,
    request: CreateLinkRequest,
    db=Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create a link from this requirement to another. Manager/admin only."""
    link = crud.create_link(
        db,
        source_requirement_id=requirement_id,
        target_requirement_id=request.target_requirement_id,
        link_type=request.link_type,
    )
    if not link:
        raise HTTPException(
            status_code=400,
            detail="Invalid link: requirements not found, same requirement, or duplicate link",
        )
    return {
        "id": link.id,
        "source_requirement_id": requirement_id,
        "target_requirement_id": request.target_requirement_id,
        "link_type": link.link_type,
        "created_at": link.created_at.isoformat() if link.created_at else None,
    }


@router.delete("/{requirement_id}/links/{link_id}", status_code=204)
async def delete_requirement_link(
    requirement_id: int,
    link_id: int,
    db=Depends(get_db),
    current_user=Depends(require_manager),
):
    """Delete a requirement link. Manager/admin only. Link must involve this requirement (as source or target)."""
    link = crud.get_link(db, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.source_requirement_id != requirement_id and link.target_requirement_id != requirement_id:
        raise HTTPException(status_code=403, detail="Link does not belong to this requirement")
    crud.delete_link(db, link_id)
