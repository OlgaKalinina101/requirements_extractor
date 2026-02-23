"""Check database contents via Docker exec - bypasses psycopg2 encoding issues."""

import subprocess
import sys

CONTAINER = "requirements-extractor-db"
DB_USER = "requirements_user"
DB_NAME = "requirements_db"

SQL_QUERY = """
SELECT 
    'DOCUMENTS' as table_name,
    COUNT(*)::text as count
FROM documents
UNION ALL
SELECT 
    'SECTIONS' as table_name,
    COUNT(*)::text as count
FROM sections
UNION ALL
SELECT 
    'REQUIREMENTS' as table_name,
    COUNT(*)::text as count
FROM requirements
UNION ALL
SELECT 
    'COVERAGE_METRICS' as table_name,
    COUNT(*)::text as count
FROM coverage_metrics;

-- Documents details
SELECT '--- DOCUMENTS ---' as info;
SELECT id, filename, status, total_pages, uploaded_at 
FROM documents 
ORDER BY id DESC 
LIMIT 5;

-- Sections sample
SELECT '--- SECTIONS (sample) ---' as info;
SELECT id, document_id, section_number, title, page_start 
FROM sections 
ORDER BY document_id, page_start 
LIMIT 10;

-- Requirements stats
SELECT '--- REQUIREMENTS STATS ---' as info;
SELECT 
    status,
    COUNT(*) as count
FROM requirements
GROUP BY status
ORDER BY status;

-- Sample requirements
SELECT '--- REQUIREMENTS (sample) ---' as info;
SELECT id, requirement_id, LEFT(text, 50) as text_preview, status, page_number 
FROM requirements 
ORDER BY document_id, id 
LIMIT 5;

-- Coverage metrics
SELECT '--- COVERAGE METRICS ---' as info;
SELECT document_id, total_pages, processed_pages, 
       ROUND(coverage_percent::numeric, 1) as coverage_pct, 
       requirements_count 
FROM coverage_metrics;
"""

print("=" * 60)
print("Checking database contents via Docker...")
print("=" * 60)
print()

# Check container is running
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
except Exception as e:
    print(f"ERROR checking container: {e}")
    sys.exit(1)

# Execute SQL query
print("Executing SQL queries...")
print()

result = subprocess.run(
    ["docker", "exec", "-i", CONTAINER,
     "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-F", "|"],
    input=SQL_QUERY,
    capture_output=True,
    text=True,
    encoding='utf-8'
)

if result.returncode != 0:
    print(f"ERROR executing SQL:\n{result.stderr}")
    sys.exit(1)

# Parse and display results
output = result.stdout.strip()
if not output:
    print("No data returned from database.")
    print("This might mean:")
    print("  1. Tables don't exist (run: python init_db_docker.py)")
    print("  2. No data was saved yet")
    sys.exit(0)

lines = output.splitlines()
current_section = None

for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Check for section headers
    if line.startswith("---"):
        print()
        print(line)
        print("-" * 60)
        current_section = line
        continue
    
    # Skip empty lines
    if not line or line == "|":
        continue
    
    # Parse table counts
    if "|" in line and current_section is None:
        parts = line.split("|")
        if len(parts) >= 2:
            table_name = parts[0].strip()
            count = parts[1].strip()
            print(f"{table_name:20s}: {count}")
    else:
        # Regular data rows
        if "|" in line:
            parts = line.split("|")
            if len(parts) > 1:
                # Format as table row
                print("  " + " | ".join(p.strip()[:50] for p in parts))
        else:
            print(f"  {line}")

print()
print("=" * 60)
print("Database check complete!")
print("=" * 60)
print()
print("To see more details, run:")
print("  docker exec -it requirements-extractor-db psql -U requirements_user -d requirements_db")
