#!/bin/bash
#
# Script-name : sync_camera_synology.sh
# Author      : Dennis Bakhuis
# Date        : 2025-09-05
# License     : MIT
#
# Multi-camera sync script for Hikvision NAS storage on Synology systems.
# Syncs videos (.mp4) and images (.pic -> .jpg) to organized folders with timestamped filenames.

# Configuration for multiple cameras
# Format: "source_path:destination_path:camera_tag"
CAMERAS=(
  "/volume3/Camera-Tuin:/volume3/Camera/Tuin:garden"
  "/volume3/Cemera-Oprit:/volume3/Camera/Oprit:driveway"
  # Add more cameras here, for example:
  # "/volume3/Camera-Oprit:/volume3/Camera/Oprit:driveway"
)

VIDEO_PATTERNS=("*.mp4")
IMAGE_PATTERNS=("*.pic")
SEARCH_DIRS=("datadir*")  # typical Hikvsion folder structure

AGE_SEC=120  # only process files older than 120s
LOCK="/tmp/sync_camera_synology.lock"

# Create destination directories
for camera_config in "${CAMERAS[@]}"; do
  IFS=':' read -r src_base dst cam_tag <<< "$camera_config"
  mkdir -p "$dst/video" || { echo "Failed to create directory: $dst/video"; exit 1; }
  mkdir -p "$dst/images" || { echo "Failed to create directory: $dst/images"; exit 1; }
done

# Prevent overlapping runs
exec 9>"$LOCK"
if command -v flock >/dev/null 2>&1; then
  flock -n 9 || exit 0
else
  # Fallback for systems without flock
  if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    exit 0
  fi
  echo $$ > "$LOCK"
  trap 'rm -f "$LOCK"' EXIT
fi

log() { echo "[$(date +'%F %T')] $*"; }

# Cross-platform stat functions
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

process_file() {
  local f="$1"
  local dst="$2"
  local cam_tag="$3"
  local file_type="$4"

  # Skip if too new
  local mtime=$(get_mtime "$f") || { log "Failed to get mtime for $f"; return; }
  local now=$(date +%s)
  if ! ((now - mtime > AGE_SEC)); then
    return
  fi

  # Skip zero-byte files
  local size=$(get_size "$f") || { log "Failed to get size for $f"; return; }
  if [[ "$size" -eq 0 ]]; then
    return
  fi

  # Skip if still growing
  local s1="$size"  # Use already retrieved size
  sleep 2
  local s2=$(get_size "$f") || { log "Failed to get size for $f after wait"; return; }
  if [[ "$s1" != "$s2" ]]; then
    return
  fi

  # Format timestamp
  local ts
  if ts=$(date -d @"$mtime" +"%Y-%m-%d_%H-%M-%S" 2>/dev/null); then
    : # ts is already set
  elif ts=$(date -r "$mtime" +"%Y-%m-%d_%H-%M-%S" 2>/dev/null); then
    : # ts is already set
  else
    log "Failed to format timestamp for $f"
    return
  fi

  # Set destination path and extension
  local dest_dir ext dest
  if [[ "$file_type" == "video" ]]; then
    dest_dir="$dst/video"
    ext="mp4"
  else
    dest_dir="$dst/images"
    ext="jpg"
  fi
  
  # Create base destination filename
  local base_dest="$dest_dir/${ts}-${cam_tag}.${ext}"
  
  # Check if file with same timestamp already exists, if so add unique suffix
  local dest="$base_dest"
  local counter=1
  while [[ -f "$dest" ]]; do
    # Check if existing file is identical (same size) to avoid true duplicates
    local existing_size=$(get_size "$dest") || { log "Failed to get size for existing $dest"; break; }
    local source_size=$(get_size "$f") || { log "Failed to get size for source $f"; break; }
    
    if [[ "$existing_size" -eq "$source_size" ]]; then
      log "Identical file already exists: $dest (size: $existing_size bytes), skipping $f"
      return
    fi
    
    # Generate new filename with counter
    local name_without_ext="${base_dest%.*}"
    local extension="${base_dest##*.}"
    dest="${name_without_ext}_${counter}.${extension}"
    counter=$((counter + 1))
    
    # Prevent infinite loops
    if [[ $counter -gt 1000 ]]; then
      log "Too many filename collisions for $f, skipping"
      return
    fi
  done
  
  local tmp="${dest}.part.$$"

  # Atomic copy via temporary file
  if cp -p -- "$f" "$tmp" 2>/dev/null || { 
    # Fallback copy method
    log "Using fallback copy method for $f"
    cp -- "$f" "$tmp"
  }; then
    mv -f -- "$tmp" "$dest" || {
      log "mv failed: $f"
      rm -f -- "$tmp"
      return
    }
    log "copied: $f -> $dest [$cam_tag] ($file_type)"
  else
    log "copy failed: $f"
    rm -f -- "$tmp"
  fi
}

export -f process_file get_mtime get_size log
export AGE_SEC

# Process each camera configuration
log "Starting multi-camera sync for ${#CAMERAS[@]} camera(s)"

for camera_config in "${CAMERAS[@]}"; do
  IFS=':' read -r src_base dst cam_tag <<< "$camera_config"
  
  log "Processing camera '$cam_tag': $src_base -> $dst"
  
  # Check if source directory exists
  if [[ ! -d "$src_base" ]]; then
    log "Warning: Source directory does not exist: $src_base"
    continue
  fi
  
  # Scan directory patterns for videos and images
  for search_pattern in "${SEARCH_DIRS[@]}"; do
    find "$src_base" -maxdepth 1 -type d -name "$search_pattern" -print0 | while IFS= read -r -d '' dir; do
      if [[ -d "$dir" ]]; then
        log "Scanning directory: $dir [$cam_tag]"
        
        # Process video files
        for video_pattern in "${VIDEO_PATTERNS[@]}"; do
          find "$dir" -maxdepth 1 -type f -name "$video_pattern" -print0 |
            xargs -0 -I{} bash -c 'process_file "$1" "$2" "$3" "$4"' _ {} "$dst" "$cam_tag" "video"
        done
        
        # Process image files (.pic)
        for image_pattern in "${IMAGE_PATTERNS[@]}"; do
          find "$dir" -maxdepth 1 -type f -name "$image_pattern" -print0 |
            xargs -0 -I{} bash -c 'process_file "$1" "$2" "$3" "$4"' _ {} "$dst" "$cam_tag" "image"
        done
      fi
    done
  done
done

log "Multi-camera sync completed"
