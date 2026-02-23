"""Initialize database - create tables and run migrations.

This script should be run once to set up the database schema.
Can be used for both development and production.
"""

import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows to avoid encoding issues
if sys.platform == 'win32':
    import codecs
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text


def main():
    """Initialize database."""
    print("🚀 Initializing database...")
    
    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⚠️  DATABASE_URL not set, using default")
        database_url = "postgresql://requirements_user:requirements_pass@localhost:5433/requirements_db"
    
    print(f"📊 Database URL: {database_url.split('@')[1] if '@' in database_url else 'local'}")
    
    try:
        # First, try to connect to database using psycopg2 directly
        print("🔌 Testing database connection...")
        try:
            import psycopg2
            # Parse connection string manually to avoid encoding issues
            parts = database_url.replace("postgresql://", "").split("@")
            if len(parts) == 2:
                user_pass = parts[0].split(":")
                host_port_db = parts[1].split("/")
                host_port = host_port_db[0].split(":")
                
                user = user_pass[0]
                password = user_pass[1] if len(user_pass) > 1 else ""
                host = host_port[0]
                port = int(host_port[1]) if len(host_port) > 1 else 5432
                database = host_port_db[1] if len(host_port_db) > 1 else "postgres"
                
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    connect_timeout=5
                )
                conn.close()
                print("✓ Database connection successful")
            else:
                raise ValueError("Invalid database URL format")
        except ImportError:
            print("⚠️  psycopg2 not available, skipping connection test")
        except Exception as conn_error:
            print(f"❌ Cannot connect to database: {conn_error}")
            print("\n💡 Make sure PostgreSQL is running:")
            print("   docker-compose up -d postgres")
            print("   Wait 5-10 seconds, then try again.")
            sys.exit(1)
        
        # Run Alembic migrations
        print("📦 Running Alembic migrations...")
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        # Stamp database with current revision (if needed)
        # command.stamp(alembic_cfg, "head")
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        
        print("✅ Database initialized successfully!")
        print("\n📋 Next steps:")
        print("   1. Start the API server: python api_server.py")
        print("   2. Or use Docker Compose: docker-compose up")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print("\n💡 Make sure PostgreSQL is running and accessible.")
        print("   For Docker: docker-compose up postgres")
        sys.exit(1)


if __name__ == "__main__":
    main()
