#!/bin/bash
set -e

# Wait for database to be ready (simple approach)
echo "Waiting for database to be ready..."
sleep 5

# Run migrations using the virtual environment
echo "Running database migrations..."
python -m alembic upgrade head

# Seed database (idempotent, development only)
echo "Running database seed..."
python -m seeds.seed_runner

# Start the application with hot reload
echo "Starting application..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /fastapi --root-path ""