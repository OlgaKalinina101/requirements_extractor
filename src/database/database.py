"""Database connection and session management.

This module provides database connection setup, session management,
and initialization functions for SQLAlchemy.

Uses psycopg3 (postgresql+psycopg) instead of psycopg2 to avoid
encoding issues on Windows with Russian locale.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from src.database.models import Base

# Get database URL from environment or use default
# Use postgresql+psycopg:// for psycopg3 driver (no encoding issues on Windows)
_raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql://requirements_user:requirements_pass@localhost:5433/requirements_db"
)

# Ensure we use psycopg3 driver (postgresql+psycopg://) not psycopg2
if _raw_url.startswith("postgresql://"):
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif _raw_url.startswith("postgresql+psycopg2://"):
    DATABASE_URL = _raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = _raw_url

# Create engine
# Use NullPool for development to avoid connection issues
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session.
    
    Yields:
        Database session. Automatically closes after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database by creating all tables.
    
    This function creates all tables defined in models.py.
    Should be called once at application startup.
    """
    Base.metadata.create_all(bind=engine)
