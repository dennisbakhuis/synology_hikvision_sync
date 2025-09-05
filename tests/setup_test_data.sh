#!/bin/bash
#
# setup_test_data.sh - Create realistic test data for camera sync scripts
# Author: Dennis Bakhuis
# Date: 2025-09-05
#
# This script creates a realistic test environment with mock Hikvision camera data
# for testing sync_camera_synology.sh and cleanup_camera_files.sh

TEST_BASE_DIR="${1:-$(pwd)/test_data}"
CLEANUP_AFTER="${2:-false}"

setup_test_environment() {
    local base_dir="$1"
    
    echo "Setting up test environment in: $base_dir"
    
    # Clean up any existing test data
    rm -rf "$base_dir"
    
    # Create source structure (mock Hikvision cameras)
    mkdir -p "$base_dir/camera1/datadir001"
    mkdir -p "$base_dir/camera2/datadir001" 
    mkdir -p "$base_dir/camera2/datadir002"
    
    # Create destination structure
    mkdir -p "$base_dir/clean/camera1"
    mkdir -p "$base_dir/clean/camera2"
    
    echo "✓ Created directory structure"
    
    # Create test video files (.mp4)
    create_test_file "$base_dir/camera1/datadir001/rec001.mp4" "fake video data 1" "3 hours ago"
    create_test_file "$base_dir/camera1/datadir001/rec002.mp4" "fake video data 2" "2 hours ago"
    create_test_file "$base_dir/camera1/datadir001/rec003.mp4" "fake video data 3" "30 seconds ago"  # Too new
    
    create_test_file "$base_dir/camera2/datadir001/vid001.mp4" "camera2 video 1" "4 hours ago"
    create_test_file "$base_dir/camera2/datadir002/vid002.mp4" "camera2 video 2" "1 hour ago"
    
    echo "✓ Created test video files"
    
    # Create test image files (.pic)
    create_test_file "$base_dir/camera1/datadir001/snap001.pic" "fake image data 1" "3 hours ago"
    create_test_file "$base_dir/camera1/datadir001/snap002.pic" "fake image data 2" "2 hours ago"
    create_test_file "$base_dir/camera1/datadir001/snap003.pic" "" "1 hour ago"  # Empty file - should be skipped
    create_test_file "$base_dir/camera1/datadir001/snap004.pic" "fake image data 4" "10 seconds ago"  # Too new
    
    create_test_file "$base_dir/camera2/datadir001/img001.pic" "camera2 image 1" "5 hours ago" 
    create_test_file "$base_dir/camera2/datadir002/img002.pic" "camera2 image 2" "90 minutes ago"
    
    echo "✓ Created test image files"
    
    # Create some old files for cleanup testing  
    mkdir -p "$base_dir/clean/camera1/video" "$base_dir/clean/camera1/images"
    mkdir -p "$base_dir/clean/camera2/video" "$base_dir/clean/camera2/images"
    
    create_test_file "$base_dir/clean/camera1/video/2024-01-01_12-00-00-cam1.mp4" "old video 1" "100 days ago"
    create_test_file "$base_dir/clean/camera1/images/2024-01-01_12-00-05-cam1.jpg" "old image 1" "100 days ago"
    create_test_file "$base_dir/clean/camera2/video/2024-02-01_15-30-00-cam2.mp4" "old video 2" "60 days ago"
    create_test_file "$base_dir/clean/camera2/images/2024-02-01_15-30-10-cam2.jpg" "old image 2" "60 days ago"
    
    # Recent files (should not be cleaned up)
    create_test_file "$base_dir/clean/camera1/video/$(date +%Y-%m-%d_%H-%M-%S)-cam1.mp4" "recent video" "1 day ago"
    create_test_file "$base_dir/clean/camera1/images/$(date +%Y-%m-%d_%H-%M-%S)-cam1.jpg" "recent image" "1 day ago"
    
    echo "✓ Created cleanup test files"
    
    # Create test configuration
    cat > "$base_dir/test_config.sh" << EOF
# Test configuration for camera sync scripts

# Source cameras (for sync script)
CAMERAS=(
    "$base_dir/camera1:$base_dir/clean/camera1:cam1"
    "$base_dir/camera2:$base_dir/clean/camera2:cam2"
)

# Cleanup configuration  
CLEANUP_CAMERAS=(
    "$base_dir/clean/camera1:cam1"
    "$base_dir/clean/camera2:cam2"
)

# Test settings
AGE_SEC=60  # Process files older than 60 seconds (for testing)
RETENTION_DAYS=90
DRY_RUN=true  # Start with dry-run for safety
EOF
    
    echo "✓ Created test configuration"
    echo
    echo "Test environment ready!"
    echo
    echo "Directory structure:"
    find "$base_dir" -type f | sort
    echo
    echo "To test the sync script:"
    echo "  1. Edit sync_camera_synology.sh and source $base_dir/test_config.sh"
    echo "  2. Run: ./sync_camera_synology.sh"
    echo
    echo "To test cleanup script:"
    echo "  1. Edit cleanup_camera_files.sh and source $base_dir/test_config.sh"
    echo "  2. Run: ./cleanup_camera_files.sh"
    echo
    
    if [[ "$CLEANUP_AFTER" == "true" ]]; then
        echo "Press Enter to clean up test data, or Ctrl+C to keep it..."
        read -r
        rm -rf "$base_dir"
        echo "✓ Test data cleaned up"
    fi
}

create_test_file() {
    local file="$1"
    local content="$2"
    local age="$3"
    
    # Create the file with content
    if [[ -n "$content" ]]; then
        echo "$content" > "$file"
    else
        touch "$file"  # Empty file
    fi
    
    # Set file age
    if command -v touch >/dev/null 2>&1; then
        # Try GNU date first (Linux)
        if date -d "$age" >/dev/null 2>&1; then
            touch -d "$age" "$file" 2>/dev/null
        # Try BSD date (macOS)
        elif [[ "$age" =~ ([0-9]+)\ (day|hour|minute|second)s?\ ago ]]; then
            local num="${BASH_REMATCH[1]}"
            local unit="${BASH_REMATCH[2]}"
            case "$unit" in
                day) touch -t "$(date -v-${num}d +%Y%m%d%H%M.%S)" "$file" 2>/dev/null ;;
                hour) touch -t "$(date -v-${num}H +%Y%m%d%H%M.%S)" "$file" 2>/dev/null ;;
                minute) touch -t "$(date -v-${num}M +%Y%m%d%H%M.%S)" "$file" 2>/dev/null ;;
                second) touch -t "$(date -v-${num}S +%Y%m%d%H%M.%S)" "$file" 2>/dev/null ;;
            esac
        fi
    fi
}

# Run setup if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    setup_test_environment "$TEST_BASE_DIR" "$CLEANUP_AFTER"
fi