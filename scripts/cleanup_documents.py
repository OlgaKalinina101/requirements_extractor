"""Clean up all uploaded documents and related data from the database.

Deletes:
  - documents
  - sections (cascade)
  - requirements (cascade)
  - coverage_metrics (cascade)
  - comments, requirement_history, requirement_links (via requirements cascade)

Does NOT touch: projects, users, dictionary_items.

Usage:
    python scripts/cleanup_documents.py           # dry-run, show what would be deleted
    python scripts/cleanup_documents.py --yes       # actually delete from DB
    python scripts/cleanup_documents.py --yes --files   # also delete PDF files from data/uploads
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import func
from src.database.database import SessionLocal
from src.database.models import Document, Section, Requirement, CoverageMetrics


def main():
    parser = argparse.ArgumentParser(description="Clean up documents and related data")
    parser.add_argument("--yes", action="store_true", help="Actually perform deletion")
    parser.add_argument("--files", action="store_true", help="Also delete PDF files from disk (data/uploads)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # Count before
        docs = db.query(Document).all()
        if not docs:
            print("No documents in database. Nothing to clean.")
            return

        req_count = db.query(func.count(Requirement.id)).scalar()
        section_count = db.query(func.count(Section.id)).scalar()
        metrics_count = db.query(func.count(CoverageMetrics.id)).scalar()

        print("=" * 60)
        print("Documents and related data to be removed:")
        print("=" * 60)
        for doc in docs:
            print(f"  [{doc.id}] {doc.filename}")
            print(f"       file: {doc.file_path}")
        print()
        print(f"  Total: {len(docs)} documents")
        print(f"         {section_count} sections")
        print(f"         {req_count} requirements")
        print(f"         {metrics_count} coverage_metrics")
        print("=" * 60)

        if not args.yes:
            print()
            print("Dry-run. Use --yes to actually delete.")
            if args.files:
                print("Use --files to also remove PDF files from data/uploads")
            return

        # Collect file paths before deleting (for --files)
        file_paths = [Path(d.file_path) for d in docs]

        # Delete documents (CASCADE will remove sections, requirements, coverage_metrics, etc.)
        deleted = db.query(Document).delete()
        db.commit()
        print(f"\nDeleted {deleted} documents from database.")

        # Optionally delete physical files
        if args.files and file_paths:
            removed = 0
            for fp in file_paths:
                if fp.exists():
                    try:
                        fp.unlink()
                        print(f"  Removed file: {fp}")
                        removed += 1
                    except OSError as e:
                        print(f"  Failed to remove {fp}: {e}")
                else:
                    print(f"  File not found (skipped): {fp}")
            print(f"\nRemoved {removed} file(s) from disk.")
        elif args.files:
            print("No file paths to remove.")

        print("\nDone.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
