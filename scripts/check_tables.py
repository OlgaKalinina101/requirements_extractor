"""Check if database tables exist."""

import subprocess
import sys

CONTAINER = "requirements-extractor-db"
DB_USER = "requirements_user"
DB_NAME = "requirements_db"

SQL_CHECK_TABLES = """
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
"""

print("Checking if tables exist in database...")
print()

try:
    result = subprocess.run(
        ["docker", "exec", "-i", CONTAINER,
         "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A"],
        input=SQL_CHECK_TABLES,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)
    
    tables = [t.strip() for t in result.stdout.strip().splitlines() if t.strip()]
    
    if tables:
        print("Tables found:")
        for table in tables:
            print(f"  [+] {table}")
        print()
        print(f"Total: {len(tables)} tables")
        
        # Check if expected tables exist
        expected = ["documents", "sections", "requirements", "coverage_metrics"]
        missing = [t for t in expected if t not in tables]
        if missing:
            print()
            print("WARNING: Missing expected tables:")
            for t in missing:
                print(f"  [-] {t}")
            print()
            print("Run: python init_db_docker.py")
    else:
        print("ERROR: No tables found!")
        print()
        print("Tables need to be created. Run:")
        print("  python init_db_docker.py")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
