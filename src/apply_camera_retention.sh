#!/bin/bash
#
# Script-name : apply_camera_retention.sh
# Author      : Dennis Bakhuis
# Date        : 2025-09-05
# License     : MIT
#
# File retention policy script for camera sync files. Automatically deletes files older than specified retention period.
# Designed to work with sync_camera_synology.sh organized folder structure.

# Configuration - should match your sync_camera_synology.sh CAMERAS array
CAMERAS=(
  "/volume3/Camera/Tuin:garden"
  # Add more camera destinations here, for example:
  # "/volume3/Camera/Oprit:driveway"
)

# Retention settings
RETENTION_DAYS=90  # Delete files older than 90 days
DRY_RUN=false     # Set to true to see what would be deleted without actually deleting

LOCK="/tmp/apply_camera_retention.lock"

# Prevent overlapping runs
exec 9>"$LOCK"
if command -v flock >/dev/null 2>&1; then
  flock -n 9 || exit 0
else
  if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    exit 0
  fi
  echo $$ > "$LOCK"
  trap 'rm -f "$LOCK"' EXIT
fi

log() { echo "[$(date +'%F %T')] $*"; }

# Cross-platform find command for age-based file deletion
cleanup_directory() {
  local dir="$1"
  local camera_tag="$2"
  
  if [[ ! -d "$dir" ]]; then
    log "Warning: Directory does not exist: $dir"
    return
  fi
  
  log "Cleaning directory: $dir [$camera_tag] (files older than $RETENTION_DAYS days)"
  
  local deleted_count=0
  local total_size=0
  
  # Find files older than RETENTION_DAYS and process them
  if find "$dir" -type f \( -name "*.mp4" -o -name "*.jpg" -o -name "*.jpeg" \) -mtime +$RETENTION_DAYS -print0 2>/dev/null | while IFS= read -r -d '' file; do
    # Get file size for reporting
    local size
    if stat -c %s "$file" >/dev/null 2>&1; then
      size=$(stat -c %s "$file")  # GNU stat (Linux)
    elif stat -f %z "$file" >/dev/null 2>&1; then
      size=$(stat -f %z "$file")  # BSD stat (macOS, FreeBSD)  
    else
      size=0
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
      log "Would delete: $file ($(( size / 1024 / 1024 ))MB)"
    else
      if rm -f "$file"; then
        log "Deleted: $file ($(( size / 1024 / 1024 ))MB)"
        deleted_count=$((deleted_count + 1))
        total_size=$((total_size + size))
      else
        log "Failed to delete: $file"
      fi
    fi
  done; then
    if [[ "$DRY_RUN" == "false" && $deleted_count -gt 0 ]]; then
      log "Cleanup completed for $camera_tag: $deleted_count files deleted, $(( total_size / 1024 / 1024 ))MB freed"
    fi
  else
    log "Error processing files in $dir"
  fi
}

# Process each camera destination
log "Starting cleanup (retention: $RETENTION_DAYS days, dry-run: $DRY_RUN)"

total_cameras=${#CAMERAS[@]}
log "Processing $total_cameras camera location(s)"

for camera_config in "${CAMERAS[@]}"; do
  IFS=':' read -r dst cam_tag <<< "$camera_config"
  
  # Clean video directory
  cleanup_directory "$dst/video" "$cam_tag-video"
  
  # Clean images directory  
  cleanup_directory "$dst/images" "$cam_tag-images"
done

log "Cleanup process completed"