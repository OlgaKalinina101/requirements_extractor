"""Projects API endpoints."""

from fastapi import APIRouter, Depends, Form, HTTPException

from src.api.serializers import project_to_dict, project_with_docs
from src.database.database import get_db
from src.database import crud

router = APIRouter(tags=["projects"])


@router.get("")
async def get_projects(db=Depends(get_db)):
    """Get all projects."""
    projects = crud.get_all_projects(db)
    project_ids = [p.id for p in projects]
    counts = crud.get_project_counts(db, project_ids) if project_ids else {}
    result = []
    for p in projects:
        c = counts.get(p.id, {"doc_count": 0, "req_count": 0})
        result.append(project_to_dict(p, doc_count=c["doc_count"], req_count=c["req_count"]))
    return {"projects": result}


@router.post("")
async def create_project(
    name: str = Form(...),
    code: str = Form(None),
    description: str = Form(None),
    db=Depends(get_db),
):
    """Create a new project."""
    if code:
        existing = crud.get_project_by_code(db, code)
        if existing:
            raise HTTPException(status_code=400, detail=f"Project with code '{code}' already exists")

    project = crud.create_project(db, name=name, code=code, description=description)
    return project_to_dict(project, include_counts=False)


@router.get("/{project_id}")
async def get_project(project_id: int, db=Depends(get_db)):
    """Get project details with documents."""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    documents = crud.get_documents_by_project(db, project_id)
    doc_ids = [d.id for d in documents]
    req_counts = crud.get_document_req_counts(db, doc_ids) if doc_ids else {}
    return project_with_docs(project, documents, req_counts)


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    name: str = Form(None),
    code: str = Form(None),
    description: str = Form(None),
    status: str = Form(None),
    db=Depends(get_db),
):
    """Update a project."""
    project = crud.update_project(db, project_id, name=name, code=code, description=description, status=status)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_to_dict(project, include_counts=False)


@router.delete("/{project_id}")
async def delete_project(project_id: int, db=Depends(get_db)):
    """Delete a project and all its documents."""
    success = crud.delete_project(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}
