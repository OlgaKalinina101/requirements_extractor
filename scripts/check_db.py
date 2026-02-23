"""Check database contents - uses psycopg3 to avoid Windows encoding issues."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql://requirements_user:requirements_pass@localhost:5433/requirements_db"
)

# Force psycopg3 driver
if raw_url.startswith("postgresql://"):
    database_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    database_url = raw_url

print("=" * 60)
print("Checking database contents...")
print("=" * 60)
print()

try:
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url, poolclass=None, echo=False)

    with engine.connect() as conn:
        # Documents
        print("DOCUMENTS:")
        print("-" * 60)
        result = conn.execute(text(
            "SELECT id, filename, status, total_pages, uploaded_at "
            "FROM documents ORDER BY id DESC LIMIT 5"
        ))
        docs = result.fetchall()
        if docs:
            for doc in docs:
                print(f"  ID={doc[0]}  {doc[1]}  status={doc[2]}  pages={doc[3]}  uploaded={doc[4]}")
        else:
            print("  (empty)")
        print()

        # Sections
        print("SECTIONS:")
        print("-" * 60)
        result = conn.execute(text("SELECT COUNT(*) FROM sections"))
        print(f"  Total: {result.fetchone()[0]}")
        print()

        # Requirements
        print("REQUIREMENTS:")
        print("-" * 60)
        result = conn.execute(text("SELECT COUNT(*) FROM requirements"))
        req_count = result.fetchone()[0]
        print(f"  Total: {req_count}")
        if req_count > 0:
            result = conn.execute(text(
                "SELECT status, COUNT(*) FROM requirements GROUP BY status ORDER BY status"
            ))
            for row in result.fetchall():
                print(f"    {row[0]}: {row[1]}")

            result = conn.execute(text(
                "SELECT id, requirement_id, LEFT(text, 60), status "
                "FROM requirements ORDER BY id LIMIT 3"
            ))
            print()
            print("  Sample:")
            for row in result.fetchall():
                print(f"    [{row[0]}] {row[1]} ({row[3]}): {row[2]}...")
        print()

        # Coverage
        print("COVERAGE METRICS:")
        print("-" * 60)
        result = conn.execute(text(
            "SELECT document_id, total_pages, processed_pages, "
            "ROUND(coverage_percent::numeric, 1), requirements_count "
            "FROM coverage_metrics"
        ))
        metrics = result.fetchall()
        if metrics:
            for m in metrics:
                print(f"  Doc {m[0]}: {m[2]}/{m[1]} pages ({m[3]}%), {m[4]} reqs")
        else:
            print("  (empty)")

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
