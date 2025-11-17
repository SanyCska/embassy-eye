#!/bin/bash
# Wrapper script to run embassy-eye scripts (Hungary and Italy)
# This script manages VPN connection and runs both Hungary and Italy scrapers sequentially

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# VPN configuration - randomly select from available VPNs
VPN_OPTIONS=("rs-beg" "hu-bu" "me-tgd")
VPN_NAME="${VPN_OPTIONS[$RANDOM % ${#VPN_OPTIONS[@]}]}"
VPN_UP_CMD="sudo wg-quick up $VPN_NAME"
VPN_DOWN_CMD="sudo wg-quick down $VPN_NAME"

echo "$(date): Selected VPN: $VPN_NAME (randomly chosen from: ${VPN_OPTIONS[*]})"

# Function to start VPN
start_vpn() {
    echo "$(date): Starting VPN ($VPN_NAME)..."
    $VPN_UP_CMD 2>&1
    VPN_UP_EXIT=$?

    if [ $VPN_UP_EXIT -ne 0 ]; then
        # Check if VPN is already running
        if sudo wg show "$VPN_NAME" &>/dev/null; then
            echo "$(date): VPN is already running, continuing..."
        else
            echo "$(date): ERROR: Failed to start VPN (exit code $VPN_UP_EXIT)"
            echo "$(date): Aborting script execution"
            exit $VPN_UP_EXIT
        fi
    else
        echo "$(date): VPN started successfully"
    fi

    # Wait a moment for VPN to establish connection
    sleep 2
}

# Function to shut down VPN (called on exit)
shutdown_vpn() {
    # Check if VPN is running before trying to shut it down
    if sudo wg show "$VPN_NAME" &>/dev/null; then
        echo "$(date): Shutting down VPN ($VPN_NAME)..."
        $VPN_DOWN_CMD 2>&1
        VPN_DOWN_EXIT=$?
        if [ $VPN_DOWN_EXIT -eq 0 ]; then
            echo "$(date): VPN shut down successfully"
        else
            echo "$(date): Warning: VPN shutdown returned exit code $VPN_DOWN_EXIT"
        fi
    else
        echo "$(date): VPN ($VPN_NAME) is not running, skipping shutdown"
    fi
}

# Set trap to ensure VPN is always shut down, even on error or interrupt
trap shutdown_vpn EXIT INT TERM

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    # Build Docker images first (if needed, WITHOUT VPN - faster)
    echo "$(date): Checking if Docker images need to be built..."
    if [ -f "build_docker.sh" ]; then
        bash build_docker.sh
        BUILD_EXIT=$?
        if [ $BUILD_EXIT -ne 0 ]; then
            echo "$(date): ERROR: Docker build failed, aborting"
            exit $BUILD_EXIT
        fi
    else
        # Fallback: always build if build script doesn't exist
        echo "$(date): build_docker.sh not found, building Docker images..."
        docker-compose build
    fi
    
    # Build Italy Docker image if docker-compose.italy.yml exists
    if [ -f "docker-compose.italy.yml" ]; then
        # Check if Italy image exists (Docker Compose uses pattern: <project>_<service>)
        # Try multiple possible naming patterns
        ITALY_IMAGE_EXISTS=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "(embassy-eye-italy|embassy-eye.*italy)" | head -1)
        
        if [ -z "$ITALY_IMAGE_EXISTS" ]; then
            echo "$(date): Italy Docker image not found, building..."
            docker-compose -f docker-compose.italy.yml build
        else
            echo "$(date): Italy Docker image exists ($ITALY_IMAGE_EXISTS), skipping build"
        fi
    fi
    
    # Start VPN (AFTER build, BEFORE running containers)
    start_vpn
    
    # Run Hungary script with Docker (device info randomizes on each run)
    echo "$(date): ========================================"
    echo "$(date): Running Hungary embassy-eye with Docker..."
    echo "$(date): ========================================"
    docker-compose run --rm embassy-eye
    HUNGARY_EXIT=$?
    
    if [ $HUNGARY_EXIT -eq 0 ]; then
        echo "$(date): Hungary script completed successfully"
    else
        echo "$(date): Hungary script failed with exit code $HUNGARY_EXIT"
    fi
    
    # Run Italy script with Docker
    echo "$(date): ========================================"
    echo "$(date): Running Italy embassy-eye with Docker..."
    echo "$(date): ========================================"
    if [ -f "docker-compose.italy.yml" ]; then
        docker-compose -f docker-compose.italy.yml run --rm embassy-eye-italy
        ITALY_EXIT=$?
        
        if [ $ITALY_EXIT -eq 0 ]; then
            echo "$(date): Italy script completed successfully"
        else
            echo "$(date): Italy script failed with exit code $ITALY_EXIT"
        fi
    else
        echo "$(date): WARNING: docker-compose.italy.yml not found, skipping Italy script"
        ITALY_EXIT=0
    fi
    
    # Use the worst exit code from both scripts
    if [ $HUNGARY_EXIT -ne 0 ] || [ $ITALY_EXIT -ne 0 ]; then
        EXIT_CODE=1
    else
        EXIT_CODE=0
    fi
else
    # Run directly with Python (requires Python environment setup)
    # For Python, VPN is needed before running
    start_vpn
    
    # Run Hungary script with Python
    echo "$(date): ========================================"
    echo "$(date): Running Hungary embassy-eye with Python..."
    echo "$(date): ========================================"
    python3 fill_form.py hungary
    HUNGARY_EXIT=$?
    
    if [ $HUNGARY_EXIT -eq 0 ]; then
        echo "$(date): Hungary script completed successfully"
    else
        echo "$(date): Hungary script failed with exit code $HUNGARY_EXIT"
    fi
    
    # Run Italy script with Python
    echo "$(date): ========================================"
    echo "$(date): Running Italy embassy-eye with Python..."
    echo "$(date): ========================================"
    python3 -m embassy_eye.scrapers.italy.runner
    ITALY_EXIT=$?
    
    if [ $ITALY_EXIT -eq 0 ]; then
        echo "$(date): Italy script completed successfully"
    else
        echo "$(date): Italy script failed with exit code $ITALY_EXIT"
    fi
    
    # Use the worst exit code from both scripts
    if [ $HUNGARY_EXIT -ne 0 ] || [ $ITALY_EXIT -ne 0 ]; then
        EXIT_CODE=1
    else
        EXIT_CODE=0
    fi
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): All scripts completed successfully"
else
    echo "$(date): One or more scripts failed"
fi

# VPN will be shut down automatically by the trap
exit $EXIT_CODE


