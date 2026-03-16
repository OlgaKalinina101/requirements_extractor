"""Comments API endpoints (delete)."""

from fastapi import APIRouter, Depends, HTTPException

from src.database.database import get_db
from src.database import crud
from src.auth.dependencies import get_current_user

router = APIRouter(tags=["comments"])


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete own comment (or admin deletes any)."""
    comment = crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    deleted = crud.delete_comment(db, comment_id, current_user.id)
    if not deleted and current_user.role == "admin":
        crud.delete_comment_by_id(db, comment_id)
