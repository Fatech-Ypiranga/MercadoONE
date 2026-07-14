#!/bin/sh
set -eu

PORT="${PORT:-8000}"

echo "Running alembic upgrade head..."
python -c "from database.migrate import upgrade_head; upgrade_head()"

echo "Starting uvicorn on 0.0.0.0:${PORT}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
