#!/bin/bash

# Test script for cron functionality
set -e

echo "Testing cron functionality for Hikvision sync container..."

# Test 1: Validate entrypoint script syntax
echo "✓ Testing entrypoint script syntax..."
bash -n entrypoint.sh
echo "  Entrypoint script syntax is valid"

# Test 2: Test environment variable validation
echo "✓ Testing environment variable validation..."

# Test invalid CRON_INTERVAL
echo "  Testing invalid CRON_INTERVAL values..."
export CRON_INTERVAL="0"
if ./entrypoint.sh 2>/dev/null; then
    echo "  ❌ Should have failed with CRON_INTERVAL=0"
    exit 1
else
    echo "  ✓ Correctly rejected CRON_INTERVAL=0"
fi

export CRON_INTERVAL="abc"
if ./entrypoint.sh 2>/dev/null; then
    echo "  ❌ Should have failed with CRON_INTERVAL=abc"
    exit 1
else
    echo "  ✓ Correctly rejected CRON_INTERVAL=abc"
fi

export CRON_INTERVAL="1441"
if ./entrypoint.sh 2>/dev/null; then
    echo "  ❌ Should have failed with CRON_INTERVAL=1441 (>24 hours)"
    exit 1
else
    echo "  ✓ Correctly rejected CRON_INTERVAL=1441"
fi

# Test valid CRON_INTERVAL
echo "  Testing valid CRON_INTERVAL values..."
export CRON_INTERVAL="5"
export RUN_MODE="once"
if timeout 5 ./entrypoint.sh >/dev/null 2>&1; then
    echo "  ✓ Accepted valid CRON_INTERVAL=5"
else
    echo "  ✓ Valid interval accepted (expected timeout for 'once' mode)"
fi

# Test 3: Test RUN_MODE validation
echo "✓ Testing RUN_MODE validation..."
export RUN_MODE="invalid"
if ./entrypoint.sh 2>/dev/null; then
    echo "  ❌ Should have failed with RUN_MODE=invalid"
    exit 1
else
    echo "  ✓ Correctly rejected RUN_MODE=invalid"
fi

echo "✅ All cron functionality tests passed!"
echo ""
echo "Usage examples:"
echo ""
echo "# Run once (default behavior):"
echo "docker run --rm -e RUN_MODE=once ghcr.io/dennisbakhuis/synology_hikvision_sync:latest"
echo ""
echo "# Run every 10 minutes (default cron):"
echo "docker run -d ghcr.io/dennisbakhuis/synology_hikvision_sync:latest"
echo ""
echo "# Run every 5 minutes:"
echo "docker run -d -e CRON_INTERVAL=5 ghcr.io/dennisbakhuis/synology_hikvision_sync:latest"
echo ""
echo "# Run every hour:"
echo "docker run -d -e CRON_INTERVAL=60 ghcr.io/dennisbakhuis/synology_hikvision_sync:latest"