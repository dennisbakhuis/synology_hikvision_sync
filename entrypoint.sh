#!/bin/sh

# Entrypoint script for Hikvision sync container
# Uses Python's built-in scheduler instead of cron

set -e

# Default values
SYNC_INTERVAL_MINUTES=${SYNC_INTERVAL_MINUTES:-10}
RUN_MODE=${RUN_MODE:-"scheduled"}

# Function to validate sync interval
validate_interval() {
    if ! echo "$1" | grep -qE '^[1-9][0-9]*$'; then
        echo "Error: SYNC_INTERVAL_MINUTES must be a positive integer (minutes)"
        exit 1
    fi
    
    if [ "$1" -lt 1 ] || [ "$1" -gt 1440 ]; then
        echo "Error: SYNC_INTERVAL_MINUTES must be between 1 and 1440 minutes (24 hours)"
        exit 1
    fi
}

# Function to run scheduled mode
run_scheduled() {
    echo "Starting Hikvision sync in scheduled mode..."
    echo "Sync interval: $SYNC_INTERVAL_MINUTES minutes"
    
    # Validate interval
    validate_interval "$SYNC_INTERVAL_MINUTES"
    
    # Export environment variables and run Python scheduler
    export SYNC_INTERVAL_MINUTES
    export RUN_MODE
    exec python src/sync_hikvision_cameras.py
}

# Function to run once
run_once() {
    echo "Running Hikvision sync once..."
    export RUN_MODE="once"
    exec python src/sync_hikvision_cameras.py
}

# Main execution logic
case "$RUN_MODE" in
    "once")
        run_once
        ;;
    "scheduled")
        run_scheduled
        ;;
    # Backward compatibility with old 'cron' mode
    "cron")
        echo "Warning: 'cron' mode is deprecated, using 'scheduled' mode instead"
        RUN_MODE="scheduled"
        run_scheduled
        ;;
    *)
        echo "Error: RUN_MODE must be either 'once' or 'scheduled'"
        echo "Current value: $RUN_MODE"
        exit 1
        ;;
esac