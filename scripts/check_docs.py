"""Check documents in database"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT id, filename, file_path, status FROM documents ORDER BY id DESC LIMIT 3"
    ))
    
    docs = result.fetchall()
    print("\nDocuments in DB:")
    print("-" * 80)
    for d in docs:
        print(f"ID={d[0]}, file={d[1]}")
        print(f"  path={d[2]}")
        print(f"  status={d[3]}")
        
        # Check if file exists
        file_path = Path(d[2])
        exists = file_path.exists()
        print(f"  exists={exists}")
        print()
