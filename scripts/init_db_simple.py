"""Simple database initialization using SQLAlchemy only.

This script creates tables directly without using Alembic to avoid
encoding issues with psycopg2 on Windows.
"""

import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("🚀 Initializing database (simple method)...")

database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://requirements_user:requirements_pass@localhost:5433/requirements_db"
)

print(f"📊 Database URL: {database_url.split('@')[1] if '@' in database_url else 'local'}")

try:
    # Use SQLAlchemy directly
    from sqlalchemy import create_engine, text
    from src.database.models import Base
    
    print("🔌 Creating database engine...")
    
    # Create engine with explicit encoding settings
    engine = create_engine(
        database_url,
        poolclass=None,
        echo=False,
        connect_args={
            'client_encoding': 'utf8',
            'options': '-c client_encoding=utf8'
        }
    )
    
    print("🔌 Testing connection...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"✓ Connected to PostgreSQL: {version[:60]}...")
    
    print("📦 Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database initialized successfully!")
    print("\n📋 Tables created:")
    print("   - documents")
    print("   - sections")
    print("   - requirements")
    print("   - coverage_metrics")
    print("\n📋 Next steps:")
    print("   1. Start the API server: python api_server.py")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    print("\n💡 Make sure PostgreSQL is running:")
    print("   docker-compose up -d postgres")
    print("   Wait 5-10 seconds, then try again.")
    sys.exit(1)
