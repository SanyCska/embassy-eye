#!/bin/bash
# Wrapper script to run embassy-eye script
# This script can be used with cron or directly

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    # Run with Docker
    echo "$(date): Running embassy-eye with Docker..."
    docker-compose run --rm embassy-eye
else
    # Run directly with Python (requires Python environment setup)
    echo "$(date): Running embassy-eye with Python..."
    python3 fill_form.py
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): Script completed successfully"
else
    echo "$(date): Script failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE

