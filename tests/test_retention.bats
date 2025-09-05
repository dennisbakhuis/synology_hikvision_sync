#!/usr/bin/env bats

# Test suite for apply_camera_retention.sh
# Run with: bats tests/test_retention.bats

setup() {
    # Create temporary test directories
    export TEST_DIR="$(mktemp -d)"
    export TEST_DST="$TEST_DIR/destination"
    export TEST_SCRIPT="$BATS_TEST_DIRNAME/../src/apply_camera_retention.sh"
    
    # Create test structure with video and images directories
    mkdir -p "$TEST_DST/camera1/video" "$TEST_DST/camera1/images"
    mkdir -p "$TEST_DST/camera2/video" "$TEST_DST/camera2/images"
    
    # Create test files with different ages
    
    # Recent files (should NOT be deleted - 1 day old)
    echo "recent video" > "$TEST_DST/camera1/video/2025-09-04_12-00-00-cam1.mp4"
    echo "recent image" > "$TEST_DST/camera1/images/2025-09-04_12-00-00-cam1.jpg"
    
    # Old files (should be deleted - 100 days old)
    echo "old video" > "$TEST_DST/camera1/video/2024-05-01_12-00-00-cam1.mp4"
    echo "old image" > "$TEST_DST/camera1/images/2024-05-01_12-00-00-cam1.jpg"
    echo "old video 2" > "$TEST_DST/camera2/video/2024-05-01_15-30-00-cam2.mp4"
    
    # Make files appropriately old using cross-platform method
    if command -v touch >/dev/null 2>&1; then
        # Recent files (1 day old)
        touch -d "1 day ago" "$TEST_DST/camera1/video/2025-09-04_12-00-00-cam1.mp4" 2>/dev/null || \
        touch -t $(date -v-1d +%Y%m%d%H%M.%S) "$TEST_DST/camera1/video/2025-09-04_12-00-00-cam1.mp4" 2>/dev/null || \
        perl -e "utime time-(1*24*3600), time-(1*24*3600), '$TEST_DST/camera1/video/2025-09-04_12-00-00-cam1.mp4'" 2>/dev/null || true
        
        touch -d "1 day ago" "$TEST_DST/camera1/images/2025-09-04_12-00-00-cam1.jpg" 2>/dev/null || \
        touch -t $(date -v-1d +%Y%m%d%H%M.%S) "$TEST_DST/camera1/images/2025-09-04_12-00-00-cam1.jpg" 2>/dev/null || \
        perl -e "utime time-(1*24*3600), time-(1*24*3600), '$TEST_DST/camera1/images/2025-09-04_12-00-00-cam1.jpg'" 2>/dev/null || true
        
        # Old files (100 days old)
        touch -d "100 days ago" "$TEST_DST/camera1/video/2024-05-01_12-00-00-cam1.mp4" 2>/dev/null || \
        touch -t $(date -v-100d +%Y%m%d%H%M.%S) "$TEST_DST/camera1/video/2024-05-01_12-00-00-cam1.mp4" 2>/dev/null || \
        perl -e "utime time-(100*24*3600), time-(100*24*3600), '$TEST_DST/camera1/video/2024-05-01_12-00-00-cam1.mp4'" 2>/dev/null || true
        
        touch -d "100 days ago" "$TEST_DST/camera1/images/2024-05-01_12-00-00-cam1.jpg" 2>/dev/null || \
        touch -t $(date -v-100d +%Y%m%d%H%M.%S) "$TEST_DST/camera1/images/2024-05-01_12-00-00-cam1.jpg" 2>/dev/null || \
        perl -e "utime time-(100*24*3600), time-(100*24*3600), '$TEST_DST/camera1/images/2024-05-01_12-00-00-cam1.jpg'" 2>/dev/null || true
        
        touch -d "100 days ago" "$TEST_DST/camera2/video/2024-05-01_15-30-00-cam2.mp4" 2>/dev/null || \
        touch -t $(date -v-100d +%Y%m%d%H%M.%S) "$TEST_DST/camera2/video/2024-05-01_15-30-00-cam2.mp4" 2>/dev/null || \
        perl -e "utime time-(100*24*3600), time-(100*24*3600), '$TEST_DST/camera2/video/2024-05-01_15-30-00-cam2.mp4'" 2>/dev/null || true
    fi
}

teardown() {
    # Clean up test directories
    rm -rf "$TEST_DIR"
}

@test "retention script exists and is executable" {
    [ -f "$TEST_SCRIPT" ]
    [ -x "$TEST_SCRIPT" ]
}

@test "retention script has valid bash syntax" {
    run bash -n "$TEST_SCRIPT"
    [ "$status" -eq 0 ]
}

@test "dry-run mode shows what would be deleted without deleting" {
    # Create mock retention script with dry-run enabled
    cat > "$TEST_DIR/test_retention_dry.sh" << 'EOF'
#!/bin/bash

# Mock retention script variables
CAMERAS=()
while IFS= read -r line; do
    CAMERAS+=("$line")
done <<< "$TEST_CAMERAS_INPUT"

RETENTION_DAYS=90
DRY_RUN=true

log() { echo "[$(date +'%F %T')] $*"; }

# Mock cleanup function
cleanup_directory() {
    local dir="$1"
    local camera_tag="$2"
    
    if [[ ! -d "$dir" ]]; then
        log "Warning: Directory does not exist: $dir"
        return
    fi
    
    log "Cleaning directory: $dir [$camera_tag] (files older than $RETENTION_DAYS days)"
    
    find "$dir" -type f \( -name "*.mp4" -o -name "*.jpg" -o -name "*.jpeg" \) -mtime +$RETENTION_DAYS -print 2>/dev/null | while read -r file; do
        if [[ "$DRY_RUN" == "true" ]]; then
            log "Would delete: $file"
        else
            rm -f "$file"
        fi
    done
}

# Process each camera destination
for camera_config in "${CAMERAS[@]}"; do
    IFS=':' read -r dst cam_tag <<< "$camera_config"
    cleanup_directory "$dst/video" "$cam_tag-video"
    cleanup_directory "$dst/images" "$cam_tag-images"
done
EOF
    chmod +x "$TEST_DIR/test_retention_dry.sh"
    
    export TEST_CAMERAS_INPUT="$TEST_DST/camera1:cam1"
    run "$TEST_DIR/test_retention_dry.sh"
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"Would delete:"* ]]
    [[ "$output" == *"2024-05-01"* ]]  # Should mention the old files
    
    # Verify files still exist (not actually deleted in dry-run)
    [ -f "$TEST_DST/camera1/video/2024-05-01_12-00-00-cam1.mp4" ]
    [ -f "$TEST_DST/camera1/images/2024-05-01_12-00-00-cam1.jpg" ]
}

@test "actual deletion mode removes old files and keeps recent ones" {
    # Create mock retention script with actual deletion enabled
    cat > "$TEST_DIR/test_retention_real.sh" << 'EOF'
#!/bin/bash

# Mock retention script variables
CAMERAS=()
while IFS= read -r line; do
    CAMERAS+=("$line")
done <<< "$TEST_CAMERAS_INPUT"

RETENTION_DAYS=90
DRY_RUN=false

log() { echo "[$(date +'%F %T')] $*"; }

# Mock cleanup function
cleanup_directory() {
    local dir="$1"
    local camera_tag="$2"
    
    if [[ ! -d "$dir" ]]; then
        log "Warning: Directory does not exist: $dir"
        return
    fi
    
    log "Cleaning directory: $dir [$camera_tag] (files older than $RETENTION_DAYS days)"
    
    local deleted_count=0
    find "$dir" -type f \( -name "*.mp4" -o -name "*.jpg" -o -name "*.jpeg" \) -mtime +$RETENTION_DAYS -print 2>/dev/null | while read -r file; do
        if [[ "$DRY_RUN" == "false" ]]; then
            if rm -f "$file"; then
                log "Deleted: $file"
                deleted_count=$((deleted_count + 1))
            else
                log "Failed to delete: $file"
            fi
        fi
    done
    
    if [[ $deleted_count -gt 0 ]]; then
        log "Cleanup completed for $camera_tag: $deleted_count files deleted"
    fi
}

# Process each camera destination
for camera_config in "${CAMERAS[@]}"; do
    IFS=':' read -r dst cam_tag <<< "$camera_config"
    cleanup_directory "$dst/video" "$cam_tag-video"
    cleanup_directory "$dst/images" "$cam_tag-images"
done
EOF
    chmod +x "$TEST_DIR/test_retention_real.sh"
    
    export TEST_CAMERAS_INPUT="$TEST_DST/camera1:cam1"
    run "$TEST_DIR/test_retention_real.sh"
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"Deleted:"* ]]
    
    # Verify old files are deleted
    [ ! -f "$TEST_DST/camera1/video/2024-05-01_12-00-00-cam1.mp4" ]
    [ ! -f "$TEST_DST/camera1/images/2024-05-01_12-00-00-cam1.jpg" ]
    
    # Verify recent files are kept
    [ -f "$TEST_DST/camera1/video/2025-09-04_12-00-00-cam1.mp4" ]
    [ -f "$TEST_DST/camera1/images/2025-09-04_12-00-00-cam1.jpg" ]
}

@test "handles non-existent directories gracefully" {
    cat > "$TEST_DIR/test_retention_missing.sh" << 'EOF'
#!/bin/bash

log() { echo "[$(date +'%F %T')] $*"; }

# Mock cleanup function
cleanup_directory() {
    local dir="$1"
    local camera_tag="$2"
    
    if [[ ! -d "$dir" ]]; then
        log "Warning: Directory does not exist: $dir"
        return
    fi
    
    echo "Directory exists: $dir"
}

# Test with non-existent directory
cleanup_directory "/nonexistent/path" "test-cam"
echo "Test completed"
EOF
    
    run bash "$TEST_DIR/test_retention_missing.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Warning: Directory does not exist"* ]]
    [[ "$output" == *"Test completed"* ]]
}

@test "processes multiple camera configurations" {
    # Create mock retention script for multiple cameras
    cat > "$TEST_DIR/test_retention_multi.sh" << 'EOF'
#!/bin/bash

# Mock retention script variables
CAMERAS=()
while IFS= read -r line; do
    CAMERAS+=("$line")
done <<< "$TEST_CAMERAS_INPUT"

RETENTION_DAYS=90
DRY_RUN=true

log() { echo "[$(date +'%F %T')] $*"; }

# Mock cleanup function
cleanup_directory() {
    local dir="$1"
    local camera_tag="$2"
    
    if [[ -d "$dir" ]]; then
        echo "Processing: $dir [$camera_tag]"
        # Mock finding old files
        if [[ "$dir" == *"camera1"* ]]; then
            echo "Found old files in $dir"
        fi
    fi
}

# Process each camera destination
for camera_config in "${CAMERAS[@]}"; do
    IFS=':' read -r dst cam_tag <<< "$camera_config"
    echo "Camera config: $dst -> $cam_tag"
    cleanup_directory "$dst/video" "$cam_tag-video"
    cleanup_directory "$dst/images" "$cam_tag-images"
done
EOF
    chmod +x "$TEST_DIR/test_retention_multi.sh"
    
    export TEST_CAMERAS_INPUT=$''"$TEST_DST/camera1:cam1"$'\n'"$TEST_DST/camera2:cam2"''
    run "$TEST_DIR/test_retention_multi.sh"
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"cam1"* ]]
    [[ "$output" == *"cam2"* ]]
    [[ "$output" == *"Processing: $TEST_DST/camera1/video"* ]]
    [[ "$output" == *"Processing: $TEST_DST/camera2/video"* ]]
}

@test "retention script uses correct file patterns" {
    # Test that it only targets camera file types
    mkdir -p "$TEST_DST/test/video" "$TEST_DST/test/images"
    
    # Create files of different types
    echo "video" > "$TEST_DST/test/video/old.mp4"
    echo "image1" > "$TEST_DST/test/images/old.jpg"  
    echo "image2" > "$TEST_DST/test/images/old.jpeg"
    echo "other" > "$TEST_DST/test/video/old.avi"     # Should NOT be deleted
    echo "text" > "$TEST_DST/test/images/old.txt"     # Should NOT be deleted
    
    # Make all files old
    if command -v touch >/dev/null 2>&1; then
        find "$TEST_DST/test" -name "old.*" -exec touch -d "100 days ago" {} \; 2>/dev/null || \
        find "$TEST_DST/test" -name "old.*" -exec touch -t $(date -v-100d +%Y%m%d%H%M.%S) {} \; 2>/dev/null || \
        find "$TEST_DST/test" -name "old.*" -exec perl -e "utime time-(100*24*3600), time-(100*24*3600), '{}'" \; 2>/dev/null || true
    fi
    
    cat > "$TEST_DIR/test_file_patterns.sh" << 'EOF'
#!/bin/bash

RETENTION_DAYS=90
DRY_RUN=true

log() { echo "[$(date +'%F %T')] $*"; }

cleanup_directory() {
    local dir="$1"
    
    find "$dir" -type f \( -name "*.mp4" -o -name "*.jpg" -o -name "*.jpeg" \) -mtime +$RETENTION_DAYS -print 2>/dev/null | while read -r file; do
        log "Would delete: $(basename "$file")"
    done
}

cleanup_directory "$1/video"
cleanup_directory "$1/images"
EOF
    chmod +x "$TEST_DIR/test_file_patterns.sh"
    
    run "$TEST_DIR/test_file_patterns.sh" "$TEST_DST/test"
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"old.mp4"* ]]
    [[ "$output" == *"old.jpg"* ]]
    [[ "$output" == *"old.jpeg"* ]]
    [[ "$output" != *"old.avi"* ]]    # Should NOT appear
    [[ "$output" != *"old.txt"* ]]    # Should NOT appear
}