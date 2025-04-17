#!/usr/bin/env bash
set -euo pipefail

# Change to project root (scripts/ is under root/scripts)
cd "$(dirname "$0")/.."

# Ensure src is on PYTHONPATH for module imports
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"

# Enable SQL echo if desired
export SQL_ECHO=true

# Ensure migrations are applied
alembic upgrade head
echo "Migrations applied."

# Verify DB readiness using the app's SessionLocal
echo "Verifying DB readiness via check_db_ready.py..."
python3 scripts/check_db_ready.py
if [ $? -ne 0 ]; then
  echo "ERROR: Database readiness check failed. Aborting server start."
  exit 1
fi
echo "Database readiness check successful."

# Start the Uvicorn server without reload
uvicorn src.virtualstack.main:app --host 0.0.0.0 --port 8000 