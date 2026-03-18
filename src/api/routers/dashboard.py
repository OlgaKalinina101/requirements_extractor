"""Dashboard API - analytics for manager view, summary for executor."""

from typing import Optional

from fastapi import APIRouter, Depends

from src.database.database import get_db
from src.database import crud
from src.auth.dependencies import get_current_user, require_manager, require_admin

router = APIRouter(tags=["dashboard"])


@router.get("")
async def get_dashboard(
    project_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    discipline: Optional[str] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get dashboard statistics. Manager/admin: full analytics. Executor: my assigned requirements."""
    if current_user.role in ("admin", "manager", "department_head"):
        return crud.get_dashboard_stats(db, project_id=project_id, assignee_id=assignee_id, discipline=discipline)
    return crud.get_my_dashboard_stats(db, current_user.id)


@router.get("/manager")
async def get_manager_dashboard(
    project_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    discipline: Optional[str] = None,
    db=Depends(get_db),
    _current=Depends(require_manager),
):
    """Get full dashboard statistics (manager/admin only)."""
    return crud.get_dashboard_stats(db, project_id=project_id, assignee_id=assignee_id, discipline=discipline)


@router.get("/activity")
async def get_activity(
    limit: int = 200,
    db=Depends(get_db),
    _current=Depends(require_admin),
):
    """Get full system activity log (admin only)."""
    return {"activities": crud.get_recent_activity(db, limit=limit)}
