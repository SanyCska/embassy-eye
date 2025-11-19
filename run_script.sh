#!/bin/bash
# Wrapper script to run embassy-eye scripts (Hungary and Italy)
# This script manages VPN connection and runs both Hungary and Italy scrapers sequentially

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# VPN configuration
# Available VPNs (ensure matching configs exist in /etc/wireguard)
VPN_OPTIONS=(
    "al-tia"  # Albania (Tirana)
    "ba-sjj"  # Bosnia and Herzegovina (Sarajevo)
    "bg-sof"  # Bulgaria (Sofia)
    "cy-nic"  # Cyprus (Nicosia)
    "ge-tbs"  # Georgia (Tbilisi)
    "gr-ath"  # Greece (Athens)
    "hr-zag"  # Croatia (Zagreb)
    "hu-bud"  # Hungary (Budapest)
    "md-chi"  # Moldova (Chișinău)
    "me-tgd"  # Montenegro (Podgorica)
    "mk-skp"  # North Macedonia (Skopje)
    "pl-gdn"  # Poland (Gdańsk)
    "pl-waw"  # Poland (Warsaw)
    "ro-buc"  # Romania (Bucharest)
    "rs-beg"  # Serbia (Belgrade)
    "si-lju"  # Slovenia (Ljubljana)
    "sk-bts"  # Slovakia (Bratislava)
    "tr-ist"  # Turkey (Istanbul)
)
VPN_NAME=""
VPN_UP_CMD=""
VPN_DOWN_CMD=""
BLOCKED_IPS_FILE="$SCRIPT_DIR/logs/blocked_ips.log"
VPN_USAGE_LOG="$SCRIPT_DIR/logs/vpn_usage.log"
MAX_VPN_IP_ATTEMPTS=5

# Map VPN codes to country names for logging
get_vpn_country() {
    local vpn_code="$1"
    case "$vpn_code" in
        al-tia) echo "Albania (Tirana)" ;;
        me-tgd) echo "Montenegro (Podgorica)" ;;
        ba-sjj) echo "Bosnia and Herzegovina (Sarajevo)" ;;
        bg-sof) echo "Bulgaria (Sofia)" ;;
        cy-nic) echo "Cyprus (Nicosia)" ;;
        hr-zag) echo "Croatia (Zagreb)" ;;
        hu-bud) echo "Hungary (Budapest)" ;;
        md-chi) echo "Moldova (Chișinău)" ;;
        mk-skp) echo "North Macedonia (Skopje)" ;;
        ro-buc) echo "Romania (Bucharest)" ;;
        tr-ist) echo "Turkey (Istanbul)" ;;
        ge-tbs) echo "Georgia (Tbilisi)" ;;
        pl-gdn) echo "Poland (Gdańsk)" ;;
        pl-waw) echo "Poland (Warsaw)" ;;
        gr-ath) echo "Greece (Athens)" ;;
        rs-beg) echo "Serbia (Belgrade)" ;;
        si-lju) echo "Slovenia (Ljubljana)" ;;
        sk-bts) echo "Slovakia (Bratislava)" ;;
        *) echo "Unknown" ;;
    esac
}

select_random_vpn() {
    VPN_NAME="${VPN_OPTIONS[$RANDOM % ${#VPN_OPTIONS[@]}]}"
    VPN_UP_CMD="sudo wg-quick up $VPN_NAME"
    VPN_DOWN_CMD="sudo wg-quick down $VPN_NAME"
    VPN_COUNTRY=$(get_vpn_country "$VPN_NAME")
    echo "$(date): Selected VPN: $VPN_NAME - $VPN_COUNTRY (randomly chosen from ${#VPN_OPTIONS[@]} available VPNs)"
}

select_random_vpn

# Function to start VPN
start_vpn() {
    VPN_COUNTRY=$(get_vpn_country "$VPN_NAME")
    echo "$(date): Starting VPN: $VPN_NAME - $VPN_COUNTRY"
    $VPN_UP_CMD 2>&1
    VPN_UP_EXIT=$?

    if [ $VPN_UP_EXIT -ne 0 ]; then
        # Check if VPN is already running
        if sudo wg show "$VPN_NAME" &>/dev/null; then
            echo "$(date): VPN ($VPN_NAME - $VPN_COUNTRY) is already running, continuing..."
            return 0
        else
            echo "$(date): ERROR: Failed to start VPN $VPN_NAME - $VPN_COUNTRY (exit code $VPN_UP_EXIT)"
            return $VPN_UP_EXIT
        fi
    else
        echo "$(date): VPN started successfully: $VPN_NAME - $VPN_COUNTRY"
    fi

    # Wait a moment for VPN to establish connection
    sleep 5
    return 0
}

get_public_ip() {
    local ip
    ip=$(curl -s https://api.ipify.org)
    if [ -z "$ip" ]; then
        ip=$(curl -s https://ifconfig.me 2>/dev/null)
    fi
    echo "$ip"
}

ip_is_blocked() {
    local ip="$1"
    if [ -z "$ip" ] || [ ! -f "$BLOCKED_IPS_FILE" ]; then
        return 1
    fi
    grep -Fq "$ip" "$BLOCKED_IPS_FILE"
}

log_vpn_usage() {
    local country="$1"
    local ip="$2"
    local log_dir="$SCRIPT_DIR/logs"
    
    # Ensure logs directory exists
    mkdir -p "$log_dir"
    
    # Format: timestamp - country - IP
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$timestamp - $country - $ip" >> "$VPN_USAGE_LOG"
}

ensure_vpn_ip_allowed() {
    local attempt=1
    while [ $attempt -le $MAX_VPN_IP_ATTEMPTS ]; do
        CURRENT_IP=$(get_public_ip)
        if [ -z "$CURRENT_IP" ]; then
            echo "$(date): WARNING: Unable to determine current IP address after VPN connection."
            return 1
        fi

        echo "$(date): Current VPN IP is $CURRENT_IP"
        
        # Log VPN usage (country and IP) regardless of blocked status
        VPN_COUNTRY=$(get_vpn_country "$VPN_NAME")
        log_vpn_usage "$VPN_COUNTRY" "$CURRENT_IP"
        
        if ip_is_blocked "$CURRENT_IP"; then
            echo "$(date): Detected blocked IP ($CURRENT_IP). Attempt $attempt/$MAX_VPN_IP_ATTEMPTS."
            if [ $attempt -eq $MAX_VPN_IP_ATTEMPTS ]; then
                echo "$(date): ERROR: Reached maximum VPN retries with blocked IPs."
                return 1
            fi
            echo "$(date): Restarting VPN to obtain a different IP..."
            shutdown_vpn
            select_random_vpn
            if ! start_vpn; then
                echo "$(date): WARNING: Failed to restart VPN while rotating IP. Attempt $attempt/$MAX_VPN_IP_ATTEMPTS."
                attempt=$((attempt + 1))
                continue
            fi
            attempt=$((attempt + 1))
            continue
        fi

        echo "$(date): VPN IP OK (not in blocked list)."
        return 0
    done

    return 1
}

# Wrapper to start VPN and ensure IP is acceptable
establish_vpn_connection() {
    local tried_vpns=()
    local total_vpns=${#VPN_OPTIONS[@]}

    while [ ${#tried_vpns[@]} -lt $total_vpns ]; do
        select_random_vpn

        if [[ " ${tried_vpns[*]} " == *" $VPN_NAME "* ]]; then
            continue
        fi

        tried_vpns+=("$VPN_NAME")

        if ! start_vpn; then
            VPN_COUNTRY=$(get_vpn_country "$VPN_NAME")
            echo "$(date): WARNING: Unable to start VPN ($VPN_NAME - $VPN_COUNTRY). Trying another server..."
            continue
        fi

        if ensure_vpn_ip_allowed; then
            return 0
        else
            VPN_COUNTRY=$(get_vpn_country "$VPN_NAME")
            echo "$(date): WARNING: VPN IP validation failed for $VPN_NAME - $VPN_COUNTRY. Trying another server..."
            shutdown_vpn
        fi
    done

    echo "$(date): ERROR: Unable to establish VPN connection with any configured server."
    exit 1
}

# Function to shut down VPN (called on exit)
shutdown_vpn() {
    # Check if VPN is running before trying to shut it down
    if sudo wg show "$VPN_NAME" &>/dev/null; then
        VPN_COUNTRY=$(get_vpn_country "$VPN_NAME")
        echo "$(date): Shutting down VPN: $VPN_NAME - $VPN_COUNTRY"
        $VPN_DOWN_CMD 2>&1
        VPN_DOWN_EXIT=$?
        if [ $VPN_DOWN_EXIT -eq 0 ]; then
            echo "$(date): VPN shut down successfully: $VPN_NAME - $VPN_COUNTRY"
        else
            echo "$(date): Warning: VPN shutdown returned exit code $VPN_DOWN_EXIT for $VPN_NAME - $VPN_COUNTRY"
        fi
    else
        VPN_COUNTRY=$(get_vpn_country "$VPN_NAME")
        echo "$(date): VPN ($VPN_NAME - $VPN_COUNTRY) is not running, skipping shutdown"
    fi
}

# Set trap to ensure VPN is always shut down, even on error or interrupt
trap shutdown_vpn EXIT INT TERM

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Determine Italy execution mode (docker vs host python)
ITALY_USE_DOCKER_DEFAULT="true"
if [ -n "$ITALY_USE_DOCKER" ]; then
    ITALY_USE_DOCKER_DEFAULT="$ITALY_USE_DOCKER"
fi
ITALY_USE_DOCKER=$(echo "$ITALY_USE_DOCKER_DEFAULT" | tr '[:upper:]' '[:lower:]')

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
    
    # Build Italy Docker image if requested
    if [ "$ITALY_USE_DOCKER" != "false" ] && [ -f "docker-compose.italy.yml" ]; then
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
    establish_vpn_connection
    
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
    
    # Run Italy script (Docker or Python)
    echo "$(date): ========================================"
    if [ "$ITALY_USE_DOCKER" != "false" ]; then
        echo "$(date): Running Italy embassy-eye with Docker..."
        echo "$(date): ========================================"
        # Note: ITALY_HEADLESS environment variable from .env is used by docker-compose
        # For better reCAPTCHA compatibility, ensure ITALY_HEADLESS=false in .env (or leave unset)
        if [ -f "docker-compose.italy.yml" ]; then
            docker-compose -f docker-compose.italy.yml run --rm embassy-eye-italy
            ITALY_EXIT=$?
        else
            echo "$(date): WARNING: docker-compose.italy.yml not found, skipping Italy Docker run"
            ITALY_EXIT=0
        fi
    else
        echo "$(date): Running Italy embassy-eye with Python (Docker disabled)..."
        echo "$(date): ========================================"
        python3 -m embassy_eye.scrapers.italy.runner
        ITALY_EXIT=$?
    fi

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
else
    # Run directly with Python (requires Python environment setup)
    # For Python, VPN is needed before running
    establish_vpn_connection
    
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


