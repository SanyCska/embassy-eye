#!/bin/bash
# Wrapper script to run embassy-eye Hungary scraper
# This script manages VPN connection and runs the Hungary scraper (Subotica and Belgrade)

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

# Test connectivity to target website
test_target_website_connectivity() {
    local url="https://konzinfobooking.mfa.gov.hu/"
    local timeout=10
    
    echo "$(date): Testing connectivity to target website ($url)..."
    
    # Try using curl first (more reliable)
    if command -v curl &> /dev/null; then
        if curl -s --max-time "$timeout" --head "$url" &>/dev/null; then
            echo "$(date): ✓ Target website: OK (curl test passed)"
            return 0
        else
            echo "$(date): ✗ Target website: FAILED (curl test failed)"
            return 1
        fi
    # Fallback to wget if curl is not available
    elif command -v wget &> /dev/null; then
        if wget --spider --timeout="$timeout" --tries=1 "$url" &>/dev/null 2>&1; then
            echo "$(date): ✓ Target website: OK (wget test passed)"
            return 0
        else
            echo "$(date): ✗ Target website: FAILED (wget test failed)"
            return 1
        fi
    # Last resort: try Python
    elif command -v python3 &> /dev/null; then
        if python3 -c "
import urllib.request
import ssl
try:
    context = ssl.create_default_context()
    response = urllib.request.urlopen('$url', timeout=$timeout, context=context)
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
            echo "$(date): ✓ Target website: OK (Python test passed)"
            return 0
        else
            echo "$(date): ✗ Target website: FAILED (Python test failed)"
            return 1
        fi
    else
        echo "$(date): ⚠ Cannot test connectivity: curl, wget, and python3 not available"
        return 1
    fi
}

# Wrapper to start VPN and ensure IP is acceptable
establish_vpn_connection() {
    local tried_vpns=()
    local total_vpns=${#VPN_OPTIONS[@]}
    local max_connectivity_attempts=5

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
            # Test connectivity to target website
            local connectivity_attempt=1
            local connectivity_ok=false
            
            while [ $connectivity_attempt -le $max_connectivity_attempts ]; do
                if test_target_website_connectivity; then
                    connectivity_ok=true
                    break
                else
                    echo "$(date): Connectivity test failed. Attempt $connectivity_attempt/$max_connectivity_attempts"
                    if [ $connectivity_attempt -lt $max_connectivity_attempts ]; then
                        echo "$(date): Waiting 3 seconds before retry..."
                        sleep 3
                    fi
                    connectivity_attempt=$((connectivity_attempt + 1))
                fi
            done
            
            if [ "$connectivity_ok" = true ]; then
                echo "$(date): VPN connection established and target website is reachable"
                return 0
            else
                VPN_COUNTRY=$(get_vpn_country "$VPN_NAME")
                echo "$(date): WARNING: Target website not reachable via $VPN_NAME - $VPN_COUNTRY. Trying another server..."
                shutdown_vpn
            fi
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

# Function to run Hungary script with IP block retry logic
# Exit code 2 means IP was blocked - will rotate VPN and retry
run_hungary_with_ip_retry() {
    local max_ip_retries=3
    local ip_retry_attempt=1
    local hungary_exit=0
    
    while [ $ip_retry_attempt -le $max_ip_retries ]; do
        if [ $ip_retry_attempt -gt 1 ]; then
            echo "$(date): ========================================"
            echo "$(date): Retrying Hungary script after IP block (attempt $ip_retry_attempt/$max_ip_retries)..."
            echo "$(date): ========================================"
        fi
        
        # Run the script (Docker or Python based on what was called)
        if [ "$1" = "docker" ]; then
            docker-compose run --rm embassy-eye python fill_form.py hungary both
            hungary_exit=$?
        else
            python3 fill_form.py hungary both
            hungary_exit=$?
        fi
        
        # Check exit code
        if [ $hungary_exit -eq 0 ]; then
            echo "$(date): Hungary script completed successfully"
            return 0
        elif [ $hungary_exit -eq 2 ]; then
            # Exit code 2 = IP blocked
            echo "$(date): Hungary script detected IP block (exit code 2)"
            if [ $ip_retry_attempt -lt $max_ip_retries ]; then
                echo "$(date): Rotating VPN IP and retrying..."
                shutdown_vpn
                select_random_vpn
                if ! start_vpn; then
                    echo "$(date): ERROR: Failed to restart VPN after IP block. Attempt $ip_retry_attempt/$max_ip_retries."
                    ip_retry_attempt=$((ip_retry_attempt + 1))
                    continue
                fi
                
                # Ensure new IP is not blocked
                if ! ensure_vpn_ip_allowed; then
                    echo "$(date): WARNING: New VPN IP is also blocked. Attempt $ip_retry_attempt/$max_ip_retries."
                    ip_retry_attempt=$((ip_retry_attempt + 1))
                    continue
                fi
                
                # Test connectivity
                if ! test_target_website_connectivity; then
                    echo "$(date): WARNING: Target website not reachable with new VPN. Attempt $ip_retry_attempt/$max_ip_retries."
                    ip_retry_attempt=$((ip_retry_attempt + 1))
                    continue
                fi
                
                echo "$(date): VPN IP rotated successfully, retrying Hungary script..."
                ip_retry_attempt=$((ip_retry_attempt + 1))
                continue
            else
                echo "$(date): ERROR: Reached maximum IP retry attempts ($max_ip_retries). Giving up."
                return 2
            fi
        else
            # Other error (not IP block)
            echo "$(date): Hungary script failed with exit code $hungary_exit (not IP block)"
            return $hungary_exit
        fi
    done
    
    return $hungary_exit
}

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    # Load .env while filtering out comments and empty lines
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        # Export the variable (handles quotes and special characters properly)
        export "$line" 2>/dev/null || true
    done < .env
    set +a
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
    
    # Start VPN (AFTER build, BEFORE running containers)
    establish_vpn_connection
    
    # Run Hungary script with Docker (device info randomizes on each run)
    # Check both Subotica and Belgrade locations
    # Includes automatic IP block retry with VPN rotation
    echo "$(date): ========================================"
    echo "$(date): Running Hungary embassy-eye with Docker (both locations)..."
    echo "$(date): ========================================"
    run_hungary_with_ip_retry "docker"
    EXIT_CODE=$?
else
    # Run directly with Python (requires Python environment setup)
    # For Python, VPN is needed before running
    establish_vpn_connection
    
    # Run Hungary script with Python
    # Check both Subotica and Belgrade locations
    # Includes automatic IP block retry with VPN rotation
    echo "$(date): ========================================"
    echo "$(date): Running Hungary embassy-eye with Python (both locations)..."
    echo "$(date): ========================================"
    run_hungary_with_ip_retry "python"
    EXIT_CODE=$?
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): Hungary script completed successfully"
else
    echo "$(date): Hungary script failed with exit code $EXIT_CODE"
fi

# VPN will be shut down automatically by the trap
exit $EXIT_CODE


