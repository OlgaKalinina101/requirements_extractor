"""CRUD operations for document_pages table."""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.database.models import DocumentPage


def bulk_create_document_pages(
    db: Session,
    document_id: int,
    pages: List[Dict],
) -> int:
    """Insert or replace per-page text+bbox records for a document.

    Each element of ``pages`` must be a dict::

        {
            "page_number": int,          # 1-based
            "raw_text":    str,          # full page text
            "text_blocks": list[dict],   # [{text, x0, y0, x1, y1, block_type}, ...]
            "is_ocr":      bool,         # True if OCR was used for this page
        }

    Existing rows for the same (document_id, page_number) are deleted first
    so the operation is idempotent on re-processing.

    Returns:
        Number of rows inserted.
    """
    if not pages:
        return 0

    page_numbers = [p["page_number"] for p in pages]
    db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.page_number.in_(page_numbers),
    ).delete(synchronize_session=False)

    rows = [
        DocumentPage(
            document_id=document_id,
            page_number=p["page_number"],
            raw_text=p.get("raw_text", ""),
            text_blocks=p.get("text_blocks", []),
            is_ocr=p.get("is_ocr", False),
        )
        for p in pages
    ]
    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)


def get_document_page(
    db: Session,
    document_id: int,
    page_number: int,
) -> Optional[DocumentPage]:
    """Return the DocumentPage record for a specific page, or None."""
    return (
        db.query(DocumentPage)
        .filter(
            DocumentPage.document_id == document_id,
            DocumentPage.page_number == page_number,
        )
        .first()
    )


def get_document_pages(
    db: Session,
    document_id: int,
) -> List[DocumentPage]:
    """Return all DocumentPage records for a document, ordered by page_number."""
    return (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
        .all()
    )
