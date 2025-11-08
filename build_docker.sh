#!/bin/bash
# Build Docker image only if necessary (when Dockerfile or requirements.txt changed)
# This script checks if rebuild is needed and builds without VPN

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Files that trigger a rebuild
DOCKERFILE="Dockerfile"
REQUIREMENTS="requirements.txt"
BUILD_CACHE_FILE=".docker_build_cache"

# Function to get file hash (works on both Linux and macOS)
get_file_hash() {
    if [ -f "$1" ]; then
        # Try different hash commands (Linux vs macOS)
        if command -v md5sum >/dev/null 2>&1; then
            md5sum "$1" 2>/dev/null | awk '{print $1}'
        elif command -v md5 >/dev/null 2>&1; then
            md5 -q "$1" 2>/dev/null
        elif command -v shasum >/dev/null 2>&1; then
            shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
        else
            # Fallback: use file modification time
            stat -f "%m" "$1" 2>/dev/null || stat -c "%Y" "$1" 2>/dev/null || echo "0"
        fi
    else
        echo ""
    fi
}

# Check if image exists
IMAGE_EXISTS=$(docker images -q embassy-eye_embassy-eye 2>/dev/null)

# Get current hashes
CURRENT_DOCKERFILE_HASH=$(get_file_hash "$DOCKERFILE")
CURRENT_REQUIREMENTS_HASH=$(get_file_hash "$REQUIREMENTS")

# Read previous hashes from cache file
if [ -f "$BUILD_CACHE_FILE" ]; then
    source "$BUILD_CACHE_FILE"
else
    PREV_DOCKERFILE_HASH=""
    PREV_REQUIREMENTS_HASH=""
fi

# Check if rebuild is needed
REBUILD_NEEDED=false

if [ -z "$IMAGE_EXISTS" ]; then
    echo "$(date): Docker image not found, rebuild required"
    REBUILD_NEEDED=true
elif [ "$CURRENT_DOCKERFILE_HASH" != "$PREV_DOCKERFILE_HASH" ]; then
    echo "$(date): Dockerfile changed, rebuild required"
    REBUILD_NEEDED=true
elif [ "$CURRENT_REQUIREMENTS_HASH" != "$PREV_REQUIREMENTS_HASH" ]; then
    echo "$(date): requirements.txt changed, rebuild required"
    REBUILD_NEEDED=true
else
    echo "$(date): No changes detected, using existing image"
fi

# Build if needed
if [ "$REBUILD_NEEDED" = true ]; then
    echo "$(date): Building Docker image (this may take a few minutes)..."
    docker-compose build
    
    BUILD_EXIT=$?
    if [ $BUILD_EXIT -eq 0 ]; then
        echo "$(date): Docker image built successfully"
        # Save current hashes to cache
        echo "PREV_DOCKERFILE_HASH=\"$CURRENT_DOCKERFILE_HASH\"" > "$BUILD_CACHE_FILE"
        echo "PREV_REQUIREMENTS_HASH=\"$CURRENT_REQUIREMENTS_HASH\"" >> "$BUILD_CACHE_FILE"
    else
        echo "$(date): ERROR: Docker build failed (exit code $BUILD_EXIT)"
        exit $BUILD_EXIT
    fi
else
    echo "$(date): Skipping build, using existing image"
fi

exit 0

