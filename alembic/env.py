"""Alembic environment configuration.

This module configures Alembic migrations for the requirements management system.
"""

from logging.config import fileConfig
import os
import sys

# Set UTF-8 encoding for Windows to avoid encoding issues
if sys.platform == 'win32':
    import codecs
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import database models and Base (do NOT import database.database to avoid engine creation)
from src.database.models import Base

# Build DATABASE_URL from env without importing database module (avoids engine creation)
_raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql://requirements_user:requirements_pass@localhost:5433/requirements_db",
)
if _raw_url.startswith("postgresql://") and "+" not in _raw_url:
    _database_url = _raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif _raw_url.startswith("postgresql+psycopg2://"):
    _database_url = _raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
else:
    _database_url = _raw_url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option("sqlalchemy.url", _database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# Skip fileConfig to avoid encoding issues on Windows
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get database URL and create engine directly to avoid encoding issues
    database_url = config.get_main_option("sqlalchemy.url")
    
    # Use create_engine directly instead of engine_from_config to avoid encoding issues
    from sqlalchemy import create_engine
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
        echo=False,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
