#!/bin/sh

# Entrypoint script for Hikvision sync container
# Supports both one-time execution and cron-based periodic execution

set -e

# Default values
CRON_INTERVAL=${CRON_INTERVAL:-10}
RUN_MODE=${RUN_MODE:-"cron"}

# Function to validate cron interval
validate_interval() {
    if ! echo "$1" | grep -qE '^[1-9][0-9]*$'; then
        echo "Error: CRON_INTERVAL must be a positive integer (minutes)"
        exit 1
    fi
    
    if [ "$1" -lt 1 ] || [ "$1" -gt 1440 ]; then
        echo "Error: CRON_INTERVAL must be between 1 and 1440 minutes (24 hours)"
        exit 1
    fi
}

# Function to setup cron job
setup_cron() {
    echo "Setting up cron job to run every $CRON_INTERVAL minutes..."
    
    # Validate interval
    validate_interval "$CRON_INTERVAL"
    
    # Create cron entry
    CRON_SCHEDULE="*/$CRON_INTERVAL * * * *"
    
    # Create the cron command with all environment variables
    CRON_COMMAND="cd /app && env"
    CRON_COMMAND="$CRON_COMMAND CAMERA_TRANSLATION=\"$CAMERA_TRANSLATION\""
    CRON_COMMAND="$CRON_COMMAND CACHE_DIR=\"$CACHE_DIR\""
    CRON_COMMAND="$CRON_COMMAND LOCK_FILE=\"$LOCK_FILE\""
    CRON_COMMAND="$CRON_COMMAND RETENTION_DAYS=\"$RETENTION_DAYS\""
    CRON_COMMAND="$CRON_COMMAND PYTHONPATH=\"$PYTHONPATH\""
    CRON_COMMAND="$CRON_COMMAND PATH=\"$PATH\""
    CRON_COMMAND="$CRON_COMMAND python src/process_hikvision_folder.py"
    
    # Add logging
    CRON_COMMAND="$CRON_COMMAND >> /proc/1/fd/1 2>> /proc/1/fd/2"
    
    # Create crontab entry
    echo "$CRON_SCHEDULE $CRON_COMMAND" > /tmp/crontab
    
    # Install crontab
    crontab /tmp/crontab
    
    # Clean up
    rm /tmp/crontab
    
    echo "Cron job installed: $CRON_SCHEDULE"
    echo "Script will run every $CRON_INTERVAL minutes"
    
    # Run once immediately on startup
    echo "Running initial sync..."
    python src/process_hikvision_folder.py
    
    # Start cron daemon
    echo "Starting cron daemon..."
    exec crond -f -l 2
}

# Function to run once
run_once() {
    echo "Running Hikvision sync once..."
    exec python src/process_hikvision_folder.py
}

# Main execution logic
case "$RUN_MODE" in
    "once")
        run_once
        ;;
    "cron")
        setup_cron
        ;;
    *)
        echo "Error: RUN_MODE must be either 'once' or 'cron'"
        echo "Current value: $RUN_MODE"
        exit 1
        ;;
esac