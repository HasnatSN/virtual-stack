#!/bin/bash

# Run the Celery worker
# Usage: ./scripts/run_worker.sh [worker_args]
# Examples:
#   ./scripts/run_worker.sh                    # Runs with default settings
#   ./scripts/run_worker.sh -c 2 -Q high,low   # Sets concurrency and queues

# Make the script safer
set -euo pipefail

# Set working directory to project root
cd "$(dirname "$0")/.."

# Pass all arguments to the celery command
echo "Starting Celery worker..."
celery -A src.virtualstack.workers.celery_app worker --loglevel=info "$@" 