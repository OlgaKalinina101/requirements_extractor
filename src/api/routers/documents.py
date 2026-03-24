"""Documents API endpoints."""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

from src.api.schemas import CreateRequirementRequest
from src.api.serializers import (
    document_to_dict,
    document_to_list_item,
    metrics_to_dict,
    requirement_to_list_item,
)
from src.database.database import get_db
from src.database import crud
from src.models import RequirementType
from src.auth.dependencies import get_current_user, require_manager

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
async def get_document(document_id: int, db=Depends(get_db), _current=Depends(get_current_user)):
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


@router.post("/{document_id}/requirements", status_code=201)
async def create_requirement(
    document_id: int,
    request: CreateRequirementRequest,
    db=Depends(get_db),
    _current=Depends(require_manager),
):
    """Manually create a new requirement for a document. Manager/admin only."""
    document = crud.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    req_id = request.requirement_id
    if not req_id:
        req_id = crud._next_manual_requirement_id(db, document_id)
    # Check uniqueness within document
    from src.database.models import Requirement
    existing = db.query(Requirement).filter(
        Requirement.document_id == document_id,
        Requirement.requirement_id == req_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Requirement ID '{req_id}' already exists in this document")

    # Inherit section_id from existing requirements on the same page so the new
    # requirement is sorted together with its page-mates rather than falling to
    # the very end of the list (section_id IS NULL → nulls_last in ORDER BY).
    section_id: int | None = None
    if request.page_number:
        from src.database.models import Requirement as _Req
        peer = (
            db.query(_Req)
            .filter(
                _Req.document_id == document_id,
                _Req.page_number == request.page_number,
                _Req.section_id.isnot(None),
            )
            .order_by(_Req.section_id.asc())
            .first()
        )
        if peer:
            section_id = peer.section_id

    req = crud.create_requirement(
        db=db,
        document_id=document_id,
        requirement_id=req_id,
        text=request.text,
        ai_suggested=request.text,
        type=request.type,
        priority=request.priority,
        page_number=request.page_number,
        section_id=section_id,
    )
    if request.discipline:
        req.discipline = request.discipline
        db.commit()
        db.refresh(req)
    return requirement_to_list_item(req)


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
async def get_metrics(document_id: int, db=Depends(get_db), _current=Depends(get_current_user)):
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


@router.get("/{document_id}/pages/{page_number}")
async def get_document_page(
    document_id: int,
    page_number: int,
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """Get text blocks and OCR data for a specific page (used for highlight overlay)."""
    try:
        page = crud.get_document_page(db, document_id, page_number)
        if not page:
            return {"text_blocks": [], "raw_text": "", "is_ocr": False}
        return {
            "text_blocks": page.text_blocks or [],
            "raw_text": page.raw_text or "",
            "is_ocr": page.is_ocr,
        }
    except Exception as e:
        logger.error(f"Failed to get page {page_number} for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.api_route("/{document_id}/pdf", methods=["GET", "HEAD"])
async def get_document_pdf(document_id: int, request: Request, db=Depends(get_db), _current=Depends(get_current_user)):
    """Get PDF file for document viewer. HEAD supported for content-type check."""
    try:
        document = crud.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        if request.method == "HEAD":
            return Response(headers={"Content-Type": "application/pdf", "Content-Disposition": "inline"})
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
    _current=Depends(get_current_user),
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
    _current=Depends(get_current_user),
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
    _current=Depends(get_current_user),
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
    _current=Depends(get_current_user),
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
