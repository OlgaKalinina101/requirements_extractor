#!/bin/sh
set -e

# If command passed (e.g. docker compose run api alembic upgrade head), run it
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# Default: run migrations, then start server
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete. Starting API server..."
exec python api_server.py
