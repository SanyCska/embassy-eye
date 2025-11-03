#!/bin/bash
# Wrapper script to run embassy-eye with Docker
# This is a simpler version if you're only using Docker

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run Docker container
echo "$(date): Running embassy-eye..."
docker-compose run --rm embassy-eye

EXIT_CODE=$?
echo "$(date): Script finished with exit code $EXIT_CODE"
exit $EXIT_CODE

