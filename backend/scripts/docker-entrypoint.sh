#!/bin/sh
set -eu

PORT="${PORT:-8000}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"

if [ "$RUN_MIGRATIONS" = "1" ] || [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running alembic upgrade head..."
  python -c "from database.migrate import upgrade_head; upgrade_head()"
else
  echo "Skipping migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS})"
fi

echo "Starting uvicorn on 0.0.0.0:${PORT} (workers=${UVICORN_WORKERS})..."
if [ "$UVICORN_WORKERS" = "1" ]; then
  exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
fi
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}" --workers "${UVICORN_WORKERS}"
