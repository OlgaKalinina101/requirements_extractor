"""Dashboard API - analytics for manager view, summary for executor."""

from fastapi import APIRouter, Depends

from src.database.database import get_db
from src.database import crud
from src.auth.dependencies import get_current_user, require_manager

router = APIRouter(tags=["dashboard"])


@router.get("")
async def get_dashboard(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get dashboard statistics. Manager/admin: full analytics. Executor: my assigned requirements."""
    if current_user.role in ("admin", "manager"):
        return crud.get_dashboard_stats(db)
    return crud.get_my_dashboard_stats(db, current_user.id)


@router.get("/manager")
async def get_manager_dashboard(
    db=Depends(get_db),
    _current=Depends(require_manager),
):
    """Get full dashboard statistics (manager/admin only)."""
    return crud.get_dashboard_stats(db)
