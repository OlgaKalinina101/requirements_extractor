"""Initialize database via docker exec - bypasses psycopg2 encoding issues on Windows."""

import subprocess
import sys
from pathlib import Path

SQL_FILE = Path(__file__).parent / "create_tables.sql"
CONTAINER = "requirements-extractor-db"
DB_USER = "requirements_user"
DB_NAME = "requirements_db"

print("Initializing database via Docker...")
print(f"Container: {CONTAINER}")

# 1. Check container is running
try:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", CONTAINER],
        capture_output=True, text=True
    )
    if result.stdout.strip() != "true":
        print(f"ERROR: Container '{CONTAINER}' is not running!")
        print("   Run: docker-compose up -d postgres")
        sys.exit(1)
    print(f"OK: Container '{CONTAINER}' is running")
except FileNotFoundError:
    print("ERROR: Docker not found. Make sure Docker Desktop is installed.")
    sys.exit(1)

# 2. Read SQL file
if not SQL_FILE.exists():
    print(f"ERROR: SQL file not found: {SQL_FILE}")
    sys.exit(1)

sql_content = SQL_FILE.read_text(encoding='utf-8')
print(f"OK: SQL file loaded ({len(sql_content)} bytes)")

# 3. Execute SQL inside container
print("Creating tables...")
result = subprocess.run(
    ["docker", "exec", "-i", CONTAINER,
     "psql", "-U", DB_USER, "-d", DB_NAME],
    input=sql_content,
    capture_output=True,
    text=True,
    encoding='utf-8'
)

if result.returncode != 0:
    print(f"ERROR executing SQL:\n{result.stderr}")
    sys.exit(1)

print("Database initialized successfully!")
print("\nResult:")
for line in result.stdout.splitlines():
    if line.strip():
        print(f"   {line}")

print("\nNext steps:")
print("   1. Start the API server: python api_server.py")
print("   2. Check API docs:       http://localhost:8000/docs")
print("   3. Check documents list: http://localhost:8000/api/documents")
