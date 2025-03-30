#!/bin/bash

# Run the development server
# Usage: ./scripts/run_dev.sh

# Make the script safer
set -euo pipefail

# Set working directory to project root
cd "$(dirname "$0")/.."

# Set PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$(pwd)/src"

# Run the server
echo "Starting development server..."
python3 -m uvicorn src.virtualstack.main:app --reload --host 0.0.0.0 --port 8000 