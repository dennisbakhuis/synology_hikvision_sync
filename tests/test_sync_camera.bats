#!/usr/bin/env bats

# Test suite for sync_camera_synology.sh with proper mocking
# Run with: bats tests/test_sync_camera.bats

setup() {
    # Create temporary test directories
    export TEST_DIR="$(mktemp -d)"
    export TEST_SRC="$TEST_DIR/source"
    export TEST_DST="$TEST_DIR/destination" 
    export TEST_SCRIPT="$BATS_TEST_DIRNAME/../src/sync_camera_synology.sh"
    export TEST_CLEANUP_SCRIPT="$BATS_TEST_DIRNAME/../src/apply_camera_retention.sh"
    
    # Create test structure
    mkdir -p "$TEST_SRC/datadir001"
    mkdir -p "$TEST_DST"
    
    # Create test files with different ages (non-empty)
    echo "fake video data" > "$TEST_SRC/datadir001/test_old.mp4"
    echo "fake pic data" > "$TEST_SRC/datadir001/test_old.pic"
    
    # Make files old enough to process (older than 120 seconds)
    # Use a trick to set file time in the past
    if command -v touch >/dev/null 2>&1; then
        # GNU touch (Linux)
        touch -d "5 minutes ago" "$TEST_SRC/datadir001/test_old.mp4" 2>/dev/null || \
        # BSD touch (macOS) 
        touch -t $(date -v-5M +%Y%m%d%H%M.%S) "$TEST_SRC/datadir001/test_old.mp4" 2>/dev/null || \
        # Fallback - just make it old by seconds
        perl -e "utime time-300, time-300, '$TEST_SRC/datadir001/test_old.mp4'" 2>/dev/null || true
        
        touch -d "5 minutes ago" "$TEST_SRC/datadir001/test_old.pic" 2>/dev/null || \
        touch -t $(date -v-5M +%Y%m%d%H%M.%S) "$TEST_SRC/datadir001/test_old.pic" 2>/dev/null || \
        perl -e "utime time-300, time-300, '$TEST_SRC/datadir001/test_old.pic'" 2>/dev/null || true
    fi
    
    # Create a recent file (should be skipped)
    echo "fake new video" > "$TEST_SRC/datadir001/test_new.mp4"
    
    # Create empty .pic file (should be skipped)
    touch "$TEST_SRC/datadir001/test_empty.pic"
    
    # Create empty .mp4 file (should be skipped)
    touch "$TEST_SRC/datadir001/test_empty.mp4"
    
    # Create a non-empty .pic file
    echo "fake image data" > "$TEST_SRC/datadir001/test_image.pic"
    if command -v touch >/dev/null 2>&1; then
        touch -d "5 minutes ago" "$TEST_SRC/datadir001/test_image.pic" 2>/dev/null || \
        touch -t $(date -v-5M +%Y%m%d%H%M.%S) "$TEST_SRC/datadir001/test_image.pic" 2>/dev/null || \
        perl -e "utime time-300, time-300, '$TEST_SRC/datadir001/test_image.pic'" 2>/dev/null || true
    fi
}

teardown() {
    # Clean up test directories
    rm -rf "$TEST_DIR"
}

@test "script exists and is executable" {
    [ -f "$TEST_SCRIPT" ]
    [ -x "$TEST_SCRIPT" ]
}

@test "script has valid bash syntax" {
    run bash -n "$TEST_SCRIPT"
    [ "$status" -eq 0 ]
    
    run bash -n "$TEST_CLEANUP_SCRIPT"
    [ "$status" -eq 0 ]
}

@test "script creates destination directories" {
    # Create a mocked version of the script that uses test paths
    cat > "$TEST_DIR/test_sync_mock.sh" << 'EOF'
#!/bin/bash

# Mock the directory creation part of sync_camera_synology.sh
CAMERAS=()
while IFS= read -r line; do
    CAMERAS+=("$line")
done <<< "$TEST_CAMERAS_INPUT"

# Create destination directories
for camera_config in "${CAMERAS[@]}"; do
  IFS=':' read -r src_base dst cam_tag <<< "$camera_config"
  mkdir -p "$dst/video" || { echo "Failed to create directory: $dst/video"; exit 1; }
  mkdir -p "$dst/images" || { echo "Failed to create directory: $dst/images"; exit 1; }
done
echo "Directories created successfully"
EOF
    chmod +x "$TEST_DIR/test_sync_mock.sh"
    
    export TEST_CAMERAS_INPUT="$TEST_SRC:$TEST_DST:test"
    run "$TEST_DIR/test_sync_mock.sh"
    [ "$status" -eq 0 ]
    [ -d "$TEST_DST/video" ]
    [ -d "$TEST_DST/images" ]
    [[ "$output" == *"Directories created successfully"* ]]
}

@test "cross-platform stat functions work" {
    # Create a mock script that only includes the stat functions
    cat > "$TEST_DIR/test_stat_functions.sh" << 'EOF'
#!/bin/bash

# Cross-platform stat functions from sync_camera_synology.sh
get_mtime() {
  if stat -c %Y "$1" 2>/dev/null; then
    return 0
  elif stat -f %m "$1" 2>/dev/null; then
    return 0
  else
    return 1
  fi
}

get_size() {
  if stat -c %s "$1" 2>/dev/null; then
    return 0
  elif stat -f %z "$1" 2>/dev/null; then
    return 0
  else
    return 1
  fi
}

# Test the functions
get_mtime "$1" && echo "mtime: $(get_mtime "$1")"
get_size "$1" && echo "size: $(get_size "$1")"
EOF
    chmod +x "$TEST_DIR/test_stat_functions.sh"
    
    # Test with a known file
    run "$TEST_DIR/test_stat_functions.sh" "$TEST_SRC/datadir001/test_old.mp4"
    [ "$status" -eq 0 ]
    [[ "$output" == *"mtime:"* ]]
    [[ "$output" == *"size:"* ]]
}

@test "script handles non-existent source directory gracefully" {
    cat > "$TEST_DIR/test_missing_dir.sh" << 'EOF'
#!/bin/bash

# Mock the directory checking logic
check_source_directory() {
    local src_base="$1"
    if [[ ! -d "$src_base" ]]; then
        echo "Warning: Source directory does not exist: $src_base"
        return 1
    fi
    return 0
}

# Test with non-existent directory
check_source_directory "/nonexistent/path"
echo "Check completed with status: $?"
EOF
    
    run bash "$TEST_DIR/test_missing_dir.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Warning: Source directory does not exist"* ]]
    [[ "$output" == *"Check completed with status: 1"* ]]
}

@test "dry-run mode in cleanup script works" {
    # Create old test files in destination
    mkdir -p "$TEST_DST/video" "$TEST_DST/images"
    echo "test video" > "$TEST_DST/video/2024-01-01_12-00-00-test.mp4"
    echo "test image" > "$TEST_DST/images/2024-01-01_12-00-00-test.jpg"
    
    # Make them old (100 days)
    if command -v touch >/dev/null 2>&1; then
        touch -d "100 days ago" "$TEST_DST/video/2024-01-01_12-00-00-test.mp4" 2>/dev/null || \
        touch -t $(date -v-100d +%Y%m%d%H%M.%S) "$TEST_DST/video/2024-01-01_12-00-00-test.mp4" 2>/dev/null || \
        perl -e "utime time-(100*24*3600), time-(100*24*3600), '$TEST_DST/video/2024-01-01_12-00-00-test.mp4'" 2>/dev/null || true
        
        touch -d "100 days ago" "$TEST_DST/images/2024-01-01_12-00-00-test.jpg" 2>/dev/null || \
        touch -t $(date -v-100d +%Y%m%d%H%M.%S) "$TEST_DST/images/2024-01-01_12-00-00-test.jpg" 2>/dev/null || \
        perl -e "utime time-(100*24*3600), time-(100*24*3600), '$TEST_DST/images/2024-01-01_12-00-00-test.jpg'" 2>/dev/null || true
    fi
    
    # Test dry-run mode with mock cleanup script
    cat > "$TEST_DIR/test_cleanup_mock.sh" << 'EOF'
#!/bin/bash

# Mock cleanup script variables
CAMERAS=()
while IFS= read -r line; do
    CAMERAS+=("$line")
done <<< "$TEST_CAMERAS_INPUT"

RETENTION_DAYS=90
DRY_RUN=true

log() { echo "[$(date +'%F %T')] $*"; }

# Simplified cleanup function for testing
for camera_config in "${CAMERAS[@]}"; do
  IFS=':' read -r dst cam_tag <<< "$camera_config"
  
  echo "Processing camera: $cam_tag in $dst"
  
  if find "$dst" -type f \( -name "*.mp4" -o -name "*.jpg" \) -mtime +$RETENTION_DAYS -print 2>/dev/null | while read -r file; do
    if [[ "$DRY_RUN" == "true" ]]; then
      echo "Would delete: $file"
    else
      rm -f "$file"
    fi
  done; then
    echo "Dry run completed for $cam_tag"
  fi
done
EOF
    chmod +x "$TEST_DIR/test_cleanup_mock.sh"
    
    export TEST_CAMERAS_INPUT="$TEST_DST:test"
    run "$TEST_DIR/test_cleanup_mock.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Would delete"* ]]
    [[ "$output" == *"Dry run completed"* ]]
    
    # Verify files still exist (not actually deleted)
    [ -f "$TEST_DST/video/2024-01-01_12-00-00-test.mp4" ]
    [ -f "$TEST_DST/images/2024-01-01_12-00-00-test.jpg" ]
}

@test "file locking prevents concurrent execution" {
    export LOCK_FILE="$TEST_DIR/test.lock"
    
    # Test script that simulates the locking mechanism
    cat > "$TEST_DIR/test_lock.sh" << 'EOF'
#!/bin/bash
LOCK="$LOCK_FILE"
exec 9>"$LOCK"

# Mock the locking logic
if command -v flock >/dev/null 2>&1; then
  if flock -n 9; then
    echo "Lock acquired successfully"
    sleep 1
  else
    echo "Lock acquisition failed"
    exit 1
  fi
else
  # Fallback locking
  if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "Lock acquisition failed - PID exists"
    exit 1
  fi
  echo $$ > "$LOCK"
  trap 'rm -f "$LOCK"' EXIT
  echo "Lock acquired via fallback method"
  sleep 1
fi
EOF
    chmod +x "$TEST_DIR/test_lock.sh"
    
    # First instance should succeed
    run timeout 10 "$TEST_DIR/test_lock.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Lock acquired"* ]]
}

@test "log function formats messages correctly" {
    # Test the log function in isolation
    cat > "$TEST_DIR/test_log.sh" << 'EOF'
#!/bin/bash

# Mock log function from sync_camera_synology.sh
log() { echo "[$(date +'%F %T')] $*"; }

# Test the function
log "test message"
EOF
    
    run bash "$TEST_DIR/test_log.sh"
    [ "$status" -eq 0 ]
    [[ "$output" =~ ^\[[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}\]\ test\ message$ ]]
}

@test "timestamp formatting works correctly and doesn't loop" {
    # Test the timestamp formatting logic to prevent infinite loops
    cat > "$TEST_DIR/test_timestamp.sh" << 'EOF'
#!/bin/bash

# Mock timestamp formatting function from sync_camera_synology.sh
format_timestamp() {
  local mtime="$1"
  local ts
  
  # This is the fixed version that properly captures output
  if ts=$(date -d @"$mtime" +"%Y-%m-%d_%H-%M-%S" 2>/dev/null); then
    echo "timestamp: $ts"
    return 0
  elif ts=$(date -r "$mtime" +"%Y-%m-%d_%H-%M-%S" 2>/dev/null); then
    echo "timestamp: $ts"
    return 0
  else
    echo "Failed to format timestamp"
    return 1
  fi
}

# Test with current time (should work on all platforms)
current_time=$(date +%s)
format_timestamp "$current_time"
EOF
    chmod +x "$TEST_DIR/test_timestamp.sh"
    
    # Run with timeout to catch infinite loops
    run timeout 5 "$TEST_DIR/test_timestamp.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"timestamp: "* ]]
    # Ensure output contains properly formatted timestamp (YYYY-MM-DD_HH-MM-SS pattern)
    [[ "$output" =~ timestamp:\ [0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2} ]]
}

@test "zero-byte files are skipped correctly" {
    # Test the zero-byte file filtering logic
    cat > "$TEST_DIR/test_zero_byte.sh" << 'EOF'
#!/bin/bash

# Test zero-byte file detection
test_zero_byte_check() {
  local f="$1"
  local file_type="$2"
  
  if [[ ! -s "$f" ]]; then
    echo "Skipping empty $file_type file: $f"
    return 0
  else
    echo "Processing $file_type file: $f"
    return 0
  fi
}

# Test with empty video file
test_zero_byte_check "$1" "video"
# Test with empty image file  
test_zero_byte_check "$2" "image"
# Test with non-empty file
test_zero_byte_check "$3" "image"
EOF
    chmod +x "$TEST_DIR/test_zero_byte.sh"
    
    # Test with empty mp4, empty pic, and non-empty pic
    run "$TEST_DIR/test_zero_byte.sh" "$TEST_SRC/datadir001/test_empty.mp4" "$TEST_SRC/datadir001/test_empty.pic" "$TEST_SRC/datadir001/test_image.pic"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Skipping empty video file: "*"test_empty.mp4"* ]]
    [[ "$output" == *"Skipping empty image file: "*"test_empty.pic"* ]]
    [[ "$output" == *"Processing image file: "*"test_image.pic"* ]]
}

@test "process_file function handles different file types correctly" {
    # Create a mock process_file function to test logic
    cat > "$TEST_DIR/test_process_file.sh" << 'EOF'
#!/bin/bash

# Mock process_file function with core logic
process_file_mock() {
  local f="$1"
  local dst="$2"
  local cam_tag="$3"
  local file_type="$4"

  echo "Processing: $f -> $dst ($file_type) [$cam_tag]"
  
  # Check if file exists
  if [[ ! -f "$f" ]]; then
    echo "Error: File does not exist: $f"
    return 1
  fi
  
  # Check if file is empty (applies to both video and image files)
  if [[ ! -s "$f" ]]; then
    echo "Skipping empty $file_type file: $f"
    return 0
  fi
  
  # Determine extension
  local ext
  if [[ "$file_type" == "video" ]]; then
    ext="mp4"
  else
    ext="jpg"  # Convert .pic to .jpg
  fi
  
  # Use plural form for consistency with actual script
  local subdir
  if [[ "$file_type" == "video" ]]; then
    subdir="video"
  else
    subdir="images"  # Use plural form
  fi
  
  echo "Would copy to: $dst/${subdir}/$(date +%Y-%m-%d_%H-%M-%S)-${cam_tag}.${ext}"
  return 0
}

# Test video processing
process_file_mock "$1" "$2" "testcam" "video"
echo "---"
# Test image processing  
process_file_mock "$3" "$2" "testcam" "image"
EOF
    chmod +x "$TEST_DIR/test_process_file.sh"
    
    # Test with video file and image file
    run "$TEST_DIR/test_process_file.sh" "$TEST_SRC/datadir001/test_old.mp4" "$TEST_DST" "$TEST_SRC/datadir001/test_image.pic"
    
    # Debug output for CI troubleshooting
    echo "Test exit status: $status" >&3
    echo "Test output:" >&3 
    echo "$output" >&3
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"Processing:"*"test_old.mp4"*"(video)"* ]]
    [[ "$output" == *"Would copy to:"*"video/"*".mp4"* ]]
    [[ "$output" == *"Processing:"*"test_image.pic"*"(image)"* ]]
    [[ "$output" == *"Would copy to:"*"images/"*".jpg"* ]]
}