#!/bin/bash
# Helper script to rebuild the Italy Docker image from scratch

echo "Stopping and removing containers..."
docker-compose -f docker-compose.italy.yml down

echo "Removing old image..."
docker rmi embassy-eye-embassy-eye-italy 2>/dev/null || echo "Image not found, skipping..."

echo "Building new image (no cache)..."
docker-compose -f docker-compose.italy.yml build --no-cache

echo "Done! You can now run:"
echo "  docker-compose -f docker-compose.italy.yml run --rm embassy-eye-italy"





