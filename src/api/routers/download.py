"""File download endpoint."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from src.auth.dependencies import get_current_user

router = APIRouter(tags=["download"])
logger = logging.getLogger("api")


@router.get("")
async def download_file(path: str, _current=Depends(get_current_user)) -> FileResponse:
    """Download generated file by path with security checks."""
    try:
        file_path = Path(path).absolute()
        base_path = Path.cwd() / "data"

        if not str(file_path).startswith(str(base_path)):
            raise HTTPException(status_code=403, detail="Access denied")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        media_type = "application/octet-stream"
        if file_path.suffix == ".json":
            media_type = "application/json"
        elif file_path.suffix == ".txt":
            media_type = "text/plain"
        elif file_path.suffix == ".docx":
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type=media_type,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
