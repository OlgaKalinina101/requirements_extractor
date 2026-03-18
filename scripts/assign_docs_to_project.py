"""Assign documents without project to project 'Тест'.

Usage:
    python scripts/assign_docs_to_project.py           # dry-run
    python scripts/assign_docs_to_project.py --yes     # apply
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.database.database import SessionLocal
from src.database.models import Document, Project


def main():
    db = SessionLocal()
    try:
        # Find project "Тест"
        project = db.query(Project).filter(Project.name == "Тест").first()
        if not project:
            print("Project 'Тест' not found. Create it first in the UI or run:")
            print("  INSERT INTO projects (name, status) VALUES ('Тест', 'active');")
            return

        # Documents without project
        docs = db.query(Document).filter(Document.project_id == None).all()
        if not docs:
            print("No documents without project. Nothing to do.")
            return

        print(f"Project 'Тест' id={project.id}")
        print(f"Documents to assign: {len(docs)}")
        for d in docs:
            print(f"  [{d.id}] {d.filename}")

        if "--yes" not in sys.argv:
            print("\nDry-run. Use --yes to apply.")
            return

        for d in docs:
            d.project_id = project.id
        db.commit()
        print(f"\nAssigned {len(docs)} document(s) to project 'Тест'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
