#!/bin/bash

# Run Alembic migrations
# Usage: ./scripts/run_migrations.sh [revision_command]
# Examples:
#   ./scripts/run_migrations.sh                    # Runs all migrations (upgrade head)
#   ./scripts/run_migrations.sh revision -m "..."  # Creates a new migration
#   ./scripts/run_migrations.sh downgrade -1       # Reverts the last migration

# Make the script safer
set -euo pipefail

# Set working directory to project root
cd "$(dirname "$0")/.."

# Default to "upgrade head" if no arguments provided
if [ $# -eq 0 ]; then
    echo "Running migrations: upgrade head"
    alembic upgrade head
else
    echo "Running migrations: $*"
    alembic "$@"
fi 