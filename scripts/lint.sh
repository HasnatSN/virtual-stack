#!/bin/bash

# Run linting tools
# Usage: ./scripts/lint.sh [fix]
# If "fix" is provided as an argument, tools will auto-fix issues where possible

# Make the script safer
set -euo pipefail

# Set working directory to project root
cd "$(dirname "$0")/.."

# Default to not fixing
FIX=false

# Parse arguments
if [ $# -gt 0 ] && [ "$1" == "fix" ]; then
    FIX=true
fi

echo "Running linting tools..."

# Determine flags based on fix mode
if [ "$FIX" = true ]; then
    echo "Auto-fix mode enabled"
    BLACK_ARGS=""
    ISORT_ARGS="--profile black"
    FLAKE8_ARGS=""
else
    echo "Check-only mode (use './scripts/lint.sh fix' to auto-fix)"
    BLACK_ARGS="--check"
    ISORT_ARGS="--check-only --profile black"
    FLAKE8_ARGS=""
fi

# Run black
echo "Running black..."
black $BLACK_ARGS src tests

# Run isort
echo "Running isort..."
isort $ISORT_ARGS src tests

# Run flake8 (never fixes, just reports)
echo "Running flake8..."
flake8 src tests

# Run mypy
echo "Running mypy..."
mypy src 