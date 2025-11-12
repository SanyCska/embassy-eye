#!/bin/bash
# Wrapper script to run embassy-eye script
# This script manages VPN connection and runs the embassy-eye script

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
    # Build Docker image first (if needed, WITHOUT VPN - faster)
    echo "$(date): Checking if Docker image needs to be built..."
    if [ -f "build_docker.sh" ]; then
        bash build_docker.sh
        BUILD_EXIT=$?
        if [ $BUILD_EXIT -ne 0 ]; then
            echo "$(date): ERROR: Docker build failed, aborting"
            exit $BUILD_EXIT
        fi
    else
        # Fallback: always build if build script doesn't exist
        echo "$(date): build_docker.sh not found, building Docker image..."
        docker-compose build
    fi
    
    # Start VPN (AFTER build, BEFORE running container)
    start_vpn
    
    # Run with Docker (device info randomizes on each run)
    echo "$(date): Running embassy-eye with Docker (device info will be randomized)..."
    docker-compose run --rm embassy-eye
else
    # Run directly with Python (requires Python environment setup)
    # For Python, VPN is needed before running
    start_vpn
    
    echo "$(date): Running embassy-eye with Python..."
    python3 fill_form.py
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): Script completed successfully"
else
    echo "$(date): Script failed with exit code $EXIT_CODE"
fi

# VPN will be shut down automatically by the trap
exit $EXIT_CODE


