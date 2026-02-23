"""
Recalculate coverage metrics for existing documents.

This script fixes the coverage metrics calculation by properly counting
pages with requirements vs skipped pages.
"""
import sys
from sqlalchemy.orm import Session
from src.database.database import SessionLocal, engine
from src.database.models import Document, Requirement, CoverageMetrics
from src.database import crud
from collections import defaultdict

def recalculate_document_metrics(db: Session, document_id: int):
    """Recalculate metrics for a single document."""
    
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        print(f"[ERROR] Document {document_id} not found")
        return False
    
    print(f"\n[DOC] Document {document_id}: {document.filename}")
    print(f"   Total pages: {document.total_pages}")
    
    # Get all requirements for this document
    requirements = db.query(Requirement).filter(
        Requirement.document_id == document_id
    ).all()
    
    print(f"   Total requirements: {len(requirements)}")
    
    # Find pages with requirements
    pages_with_requirements = set()
    requirements_by_type = defaultdict(int)
    
    for req in requirements:
        if req.page_number:
            pages_with_requirements.add(req.page_number)
        
        # Count by type
        req_type = req.type if req.type else "Прочее"
        requirements_by_type[req_type] += 1
    
    # Calculate skipped pages
    if document.total_pages:
        all_pages = set(range(1, document.total_pages + 1))
        skipped_pages = sorted(list(all_pages - pages_with_requirements))
        processed_pages = len(pages_with_requirements)
    else:
        skipped_pages = []
        processed_pages = 0
    
    print(f"   Pages with requirements: {processed_pages}")
    print(f"   Skipped pages: {len(skipped_pages)}")
    if skipped_pages:
        print(f"   First skipped: {skipped_pages[:20]}")
    
    # Update coverage metrics
    try:
        crud.create_or_update_coverage_metrics(
            db=db,
            document_id=document_id,
            total_pages=document.total_pages or 0,
            processed_pages=processed_pages,
            skipped_pages=skipped_pages,
            requirements_count=len(requirements),
            requirements_by_type=dict(requirements_by_type),
        )
        print(f"   [OK] Metrics updated successfully")
        return True
    except Exception as e:
        print(f"   [ERROR] Error updating metrics: {e}")
        return False


def main():
    """Recalculate metrics for all documents."""
    
    print("=" * 60)
    print("[METRICS] Recalculating Coverage Metrics")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get all documents
        documents = db.query(Document).all()
        
        if not documents:
            print("\n[WARN] No documents found in database")
            return
        
        print(f"\nFound {len(documents)} document(s)")
        
        success_count = 0
        error_count = 0
        
        for doc in documents:
            if recalculate_document_metrics(db, doc.id):
                success_count += 1
            else:
                error_count += 1
        
        print("\n" + "=" * 60)
        print(f"[OK] Successfully updated: {success_count}")
        print(f"[ERROR] Errors: {error_count}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
