"""Dictionaries API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.serializers import dict_item_to_dict
from src.database.database import get_db
from src.database import crud
from src.auth.dependencies import get_current_user, require_admin

router = APIRouter(tags=["dictionaries"])


@router.get("/{dict_type}")
async def get_dictionary(
    dict_type: str,
    db=Depends(get_db),
    _current=Depends(get_current_user),
):
    """Return all items for a given dictionary type."""
    if dict_type not in crud.VALID_DICT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown dictionary type: {dict_type}")
    items = crud.get_dictionary_items(db, dict_type)
    return [dict_item_to_dict(i) for i in items]


@router.post("/{dict_type}", status_code=201)
async def create_dictionary_item(
    dict_type: str,
    body: dict,
    db=Depends(get_db),
    _current=Depends(require_admin),
):
    """Create a new dictionary item. Admin only."""
    if dict_type not in crud.VALID_DICT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown dictionary type: {dict_type}")
    if not body.get("name"):
        raise HTTPException(status_code=422, detail="Field 'name' is required")
    item = crud.create_dictionary_item(db, dict_type, body)
    return dict_item_to_dict(item)


@router.put("/{dict_type}/{item_id}")
async def update_dictionary_item(
    dict_type: str,
    item_id: int,
    body: dict,
    db=Depends(get_db),
    _current=Depends(require_admin),
):
    """Update a dictionary item. Admin only."""
    if dict_type not in crud.VALID_DICT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown dictionary type: {dict_type}")
    item = crud.update_dictionary_item(db, item_id, body)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return dict_item_to_dict(item)


@router.delete("/{dict_type}/{item_id}", status_code=204)
async def delete_dictionary_item(
    dict_type: str,
    item_id: int,
    db=Depends(get_db),
    _current=Depends(require_admin),
):
    """Delete a dictionary item. Admin only."""
    if dict_type not in crud.VALID_DICT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown dictionary type: {dict_type}")
    deleted = crud.delete_dictionary_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
