#!/bin/sh
# One-shot migration job (e.g. Railway release command / CI migrate step).
set -eu
echo "Running alembic upgrade head (migrate-only)..."
python -c "from database.migrate import upgrade_head; upgrade_head()"
echo "Migrations complete."
