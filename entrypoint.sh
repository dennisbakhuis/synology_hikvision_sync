#!/bin/sh
#
# Entrypoint script for Hikvision sync container
# Handles scheduling in shell for better resilience

set -e

# Default values
SYNC_INTERVAL_MINUTES=${SYNC_INTERVAL_MINUTES:-10}
RUN_MODE=${RUN_MODE:-"scheduled"}

# Global flag for shutdown
SHUTDOWN=0

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Signal handler for graceful shutdown
handle_signal() {
    SIGNAL_NAME=$1
    log "Received ${SIGNAL_NAME}, shutting down gracefully..."
    SHUTDOWN=1

    # Kill any running Python processes (children of this shell)
    pkill -P $$ python 2>/dev/null || true
}

# Register signal handlers
trap 'handle_signal SIGTERM' TERM
trap 'handle_signal SIGINT' INT

# Function to validate sync interval
validate_interval() {
    if ! echo "$1" | grep -qE '^[1-9][0-9]*$'; then
        log "Error: SYNC_INTERVAL_MINUTES must be a positive integer (minutes)"
        exit 1
    fi

    if [ "$1" -lt 1 ] || [ "$1" -gt 1440 ]; then
        log "Error: SYNC_INTERVAL_MINUTES must be between 1 and 1440 minutes (24 hours)"
        exit 1
    fi
}

# Function to run Python sync once
run_python_sync() {
    python src/sync_hikvision_cameras.py \
        --input-dir "${INPUT_DIR:-/input}" \
        --output-dir "${OUTPUT_DIR:-/output}" \
        --cache-dir "${CACHE_DIR:-/tmp/hikvision_cache}" \
        --lock-file "${LOCK_FILE:-/tmp/sync_hikvision_cameras.lock}" \
        --retention-days "${RETENTION_DAYS:-90}" \
        --camera-translation "${CAMERA_TRANSLATION:-}"

    return $?
}

# Function to run scheduled mode
run_scheduled() {
    log "Starting Hikvision sync in scheduled mode..."
    log "Sync interval: $SYNC_INTERVAL_MINUTES minutes"

    # Validate interval
    validate_interval "$SYNC_INTERVAL_MINUTES"

    # Main loop
    while [ $SHUTDOWN -eq 0 ]; do
        log "Running sync..."

        # Run Python sync
        if run_python_sync; then
            log "Sync completed successfully"
        else
            EXIT_CODE=$?
            log "Sync failed with exit code $EXIT_CODE - will retry at next interval"
        fi

        # Wait for next interval (unless shutting down)
        if [ $SHUTDOWN -eq 0 ]; then
            log "Waiting ${SYNC_INTERVAL_MINUTES} minutes until next sync..."

            # Sleep in background so we can interrupt it
            sleep $((SYNC_INTERVAL_MINUTES * 60)) &
            SLEEP_PID=$!

            # Wait for sleep to finish (or be interrupted)
            wait $SLEEP_PID 2>/dev/null || true
        fi
    done

    log "Scheduler stopped"
}

# Function to run once
run_once() {
    log "Running Hikvision sync once..."

    # Use exec to replace shell with Python (maintains PID 1)
    exec python src/sync_hikvision_cameras.py \
        --input-dir "${INPUT_DIR:-/input}" \
        --output-dir "${OUTPUT_DIR:-/output}" \
        --cache-dir "${CACHE_DIR:-/tmp/hikvision_cache}" \
        --lock-file "${LOCK_FILE:-/tmp/sync_hikvision_cameras.lock}" \
        --retention-days "${RETENTION_DAYS:-90}" \
        --camera-translation "${CAMERA_TRANSLATION:-}"
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
        log "Warning: 'cron' mode is deprecated, using 'scheduled' mode instead"
        RUN_MODE="scheduled"
        run_scheduled
        ;;
    *)
        log "Error: RUN_MODE must be either 'once' or 'scheduled'"
        log "Current value: $RUN_MODE"
        exit 1
        ;;
esac
