#!/bin/sh
echo "Running database migrations..."
alembic upgrade head
echo "Starting API server..."
exec python api_server.py
