"""Documents API endpoints."""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.serializers import (
    document_to_dict,
    document_to_list_item,
    metrics_to_dict,
    requirement_to_list_item,
)
from src.database.database import get_db
from src.database import crud
from src.models import RequirementType
from src.auth.dependencies import get_current_user

router = APIRouter(tags=["documents"])
logger = logging.getLogger("api")


@router.get("")
async def get_all_documents(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = Query(None, description="Filter by project"),
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """Get all documents with pagination. Optionally filter by project."""
    try:
        if project_id:
            documents = crud.get_documents_by_project(db, project_id)
        else:
            documents = crud.get_all_documents(db, skip=skip, limit=limit)
        result = [document_to_list_item(doc) for doc in documents]
        return {"documents": result, "total": len(result)}
    except Exception as e:
        logger.error(f"Failed to get documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(document_id: int, db=Depends(get_db)):
    """Get document by ID with full metadata."""
    try:
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document_to_dict(document)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/requirements")
async def get_requirements(
    document_id: int,
    status: Optional[str] = None,
    type: Optional[str] = None,
    assignee_id: Optional[str] = None,
    discipline: Optional[str] = None,
    skip: int = 0,
    limit: int = 5000,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get requirements for a document with optional filters."""
    try:
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        req_type = None
        if type:
            try:
                req_type = RequirementType(type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid requirement type: {type}")

        assignee_filter: Optional[int] = None
        if assignee_id == "me":
            assignee_filter = current_user.id
        elif assignee_id:
            try:
                assignee_filter = int(assignee_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid assignee_id")

        requirements = crud.get_requirements_by_document(
            db=db,
            document_id=document_id,
            status=status,
            type=req_type,
            assignee_id=assignee_filter,
            discipline=discipline,
            skip=skip,
            limit=limit,
        )
        return {
            "requirements": [requirement_to_list_item(req) for req in requirements],
            "total": len(requirements),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get requirements for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/metrics")
async def get_metrics(document_id: int, db=Depends(get_db)):
    """Get coverage metrics for a document."""
    try:
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        metrics = crud.get_coverage_metrics(db, document_id)
        if not metrics:
            raise HTTPException(status_code=404, detail="Metrics not found for this document")
        return metrics_to_dict(metrics)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/pdf")
async def get_document_pdf(document_id: int, db=Depends(get_db)):
    """Get PDF file for document viewer."""
    try:
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDF for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/export/word")
async def export_word(
    document_id: int,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """Generate Word document from database data on-the-fly."""
    from src.word_exporter import generate_word_from_db

    document = crud.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        sections = crud.get_sections_by_document(db, document_id)
        all_requirements = crud.get_requirements_by_document(db, document_id)
        metrics = crud.get_coverage_metrics(db, document_id)
        tmp_path = generate_word_from_db(document, sections, all_requirements, metrics)
        if tmp_path is None:
            raise HTTPException(status_code=500, detail="python-docx not available")
        background_tasks.add_task(os.unlink, tmp_path)
        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{document.filename}_requirements.docx",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EXPORT] Word generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/export/json")
async def export_json(
    document_id: int,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """Generate JSON registry from database data on-the-fly."""
    from src.export import export_json_to_temp_file

    document = crud.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    sections = crud.get_sections_by_document(db, document_id)
    all_requirements = crud.get_requirements_by_document(db, document_id)

    try:
        tmp_path = export_json_to_temp_file(document, sections, all_requirements)
        background_tasks.add_task(os.unlink, tmp_path)
        return FileResponse(
            tmp_path,
            media_type="application/json",
            filename=f"{document.filename}_registry.json",
        )
    except Exception as e:
        logger.error(f"[EXPORT] JSON generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/export/xlsx")
async def export_xlsx(
    document_id: int,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """Generate Excel (XLSX) registry from database data on-the-fly."""
    from src.export.xlsx_exporter import export_xlsx_to_temp_file

    document = crud.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    sections = crud.get_sections_by_document(db, document_id)
    all_requirements = crud.get_requirements_by_document(db, document_id)
    metrics = crud.get_coverage_metrics(db, document_id)

    try:
        tmp_path = export_xlsx_to_temp_file(document, sections, all_requirements, metrics)
        if tmp_path is None:
            raise HTTPException(status_code=500, detail="openpyxl not available")
        background_tasks.add_task(os.unlink, tmp_path)
        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{document.filename}_registry.xlsx",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EXPORT] Excel generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/export/txt")
async def export_txt(
    document_id: int,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """Generate TXT usage report from database data on-the-fly."""
    from src.export import export_txt_to_temp_file

    document = crud.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    sections = crud.get_sections_by_document(db, document_id)
    all_requirements = crud.get_requirements_by_document(db, document_id)
    metrics = crud.get_coverage_metrics(db, document_id)

    try:
        tmp_path = export_txt_to_temp_file(document, sections, all_requirements, metrics)
        background_tasks.add_task(os.unlink, tmp_path)
        return FileResponse(
            tmp_path,
            media_type="text/plain",
            filename=f"{document.filename}_report.txt",
        )
    except Exception as e:
        logger.error(f"[EXPORT] TXT generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
