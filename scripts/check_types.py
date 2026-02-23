"""Check type and priority values in database"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT type, priority, COUNT(*) as count "
        "FROM requirements "
        "GROUP BY type, priority "
        "ORDER BY count DESC "
        "LIMIT 20"
    ))
    
    print("\n" + "="*70)
    print("Типы и приоритеты требований в БД:")
    print("="*70)
    print(f"{'Type':<25} {'Priority':<20} {'Count':>10}")
    print("-"*70)
    
    for row in result.fetchall():
        type_val = row[0] if row[0] else 'NULL'
        priority_val = row[1] if row[1] else 'NULL'
        count = row[2]
        print(f"{type_val:<25} {priority_val:<20} {count:>10}")
    
    print("="*70)
