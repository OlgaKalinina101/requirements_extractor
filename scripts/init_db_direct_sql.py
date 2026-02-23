"""Initialize database using direct SQL execution.

This is a fallback method that uses psycopg2 with explicit encoding handling.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("🚀 Initializing database (direct SQL method)...")

database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://requirements_user:requirements_pass@localhost:5433/requirements_db"
)

# Parse connection string
parts = database_url.replace("postgresql://", "").split("@")
if len(parts) != 2:
    print("❌ Invalid database URL format")
    sys.exit(1)

user_pass = parts[0].split(":")
host_port_db = parts[1].split("/")
host_port = host_port_db[0].split(":")

user = user_pass[0]
password = user_pass[1] if len(user_pass) > 1 else ""
host = host_port[0]
port = int(host_port[1]) if len(host_port) > 1 else 5432
database = host_port_db[1] if len(host_port_db) > 1 else "postgres"

print(f"📊 Connecting to: {host}:{port}/{database} as {user}")

# SQL script to create tables
CREATE_TABLES_SQL = """
-- Create ENUM types
DO $$ BEGIN
    CREATE TYPE requirementtype AS ENUM ('Техническое', 'Организационное', 'Документационное', 'Функциональное', 'Нефункциональное', 'Прочее');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE requirementpriority AS ENUM ('Обязательно', 'Желательно', 'Опционально');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_pages INTEGER,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_documents_id ON documents(id);

-- Create sections table
CREATE TABLE IF NOT EXISTS sections (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_number VARCHAR(50),
    title TEXT,
    page_start INTEGER,
    page_end INTEGER
);

CREATE INDEX IF NOT EXISTS ix_sections_id ON sections(id);

-- Create requirements table
CREATE TABLE IF NOT EXISTS requirements (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(id) ON DELETE SET NULL,
    requirement_id VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    type requirementtype,
    priority requirementpriority,
    page_number INTEGER,
    bbox JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    ai_suggested TEXT NOT NULL,
    human_edited TEXT,
    edit_reason TEXT,
    edited_by VARCHAR(255),
    edited_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_requirements_id ON requirements(id);
CREATE INDEX IF NOT EXISTS ix_requirements_requirement_id ON requirements(requirement_id);
CREATE INDEX IF NOT EXISTS ix_requirements_status ON requirements(status);

-- Create coverage_metrics table
CREATE TABLE IF NOT EXISTS coverage_metrics (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    total_pages INTEGER NOT NULL,
    processed_pages INTEGER NOT NULL,
    skipped_pages INTEGER[],
    coverage_percent FLOAT NOT NULL,
    requirements_count INTEGER NOT NULL,
    requirements_by_type JSONB,
    calculated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_coverage_metrics_id ON coverage_metrics(id);
"""

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    print("🔌 Connecting to PostgreSQL...")
    
    # Try to connect with explicit encoding
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connect_timeout=5
    )
    
    # Set encoding explicitly
    conn.set_client_encoding('UTF8')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    print("✓ Connected successfully")
    
    print("📦 Creating tables...")
    cur = conn.cursor()
    cur.execute(CREATE_TABLES_SQL)
    cur.close()
    
    print("✅ Database initialized successfully!")
    print("\n📋 Tables created:")
    print("   - documents")
    print("   - sections")
    print("   - requirements")
    print("   - coverage_metrics")
    
    conn.close()
    
    print("\n📋 Next steps:")
    print("   1. Start the API server: python api_server.py")
    
except ImportError:
    print("❌ psycopg2 not installed")
    print("   Install it: pip install psycopg2-binary")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    print("\n💡 Make sure PostgreSQL is running:")
    print("   docker-compose up -d postgres")
    print("   Wait 5-10 seconds, then try again.")
    sys.exit(1)
