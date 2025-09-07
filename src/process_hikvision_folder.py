#!/usr/bin/python3
#
# Script-name : process_hikvision_folder.py
# Author      : Dennis Bakhuis
# Date        : 2025-09-05
# License     : MIT
#
# Multi-camera sync script for Hikvision NAS storage using libhikvision.
# Extracts video segments and images from Hikvision format to organized folders with timestamped filenames.

import os
import sys
import fcntl
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Callable, Dict
from abc import ABC, abstractmethod

try:
    from libhikvision import libHikvision
except ImportError:  # pragma: no cover
    libHikvision = None  # pragma: no cover

# Default configuration for multiple cameras
# Format: (source_path, destination_path, camera_tag)
DEFAULT_CAMERAS = [
    ('./local/Camera-Tuin', './local/output/Tuin', 'garden'),
    # Add more cameras here, for example:
    # ('./local/Camera-Oprit', './local/output/Oprit', 'driveway'),
]

DEFAULT_LOCK_FILE = '/tmp/process_hikvision_folder.lock'
DEFAULT_CACHE_DIR = '/tmp/hikvision_cache'
DEFAULT_INPUT_DIR = '/input'
DEFAULT_OUTPUT_DIR = '/output'
DEFAULT_RETENTION_DAYS = 90


def parse_camera_translation(translation_env: str) -> Dict[str, str]:
    """Parse camera translation table from environment variable.
    
    Format: "Camera-Tuin:garden,Camera-Oprit:driveway,Another-Name:another_tag"
    Returns: Dictionary mapping original names to translated names
    """
    translation_map = {}
    if not translation_env:
        return translation_map
    
    try:
        pairs = translation_env.split(',')
        for pair in pairs:
            pair = pair.strip()
            if ':' in pair:
                original, translated = pair.split(':', 1)
                translation_map[original.strip()] = translated.strip()
    except Exception as e:
        print(f"Warning: Failed to parse camera translation '{translation_env}': {e}")
    
    return translation_map


def discover_cameras(input_dir: str = DEFAULT_INPUT_DIR, 
                    output_dir: str = DEFAULT_OUTPUT_DIR,
                    translation_map: Optional[Dict[str, str]] = None) -> List[Tuple[str, str, str]]:
    """Automatically discover cameras from input directory.
    
    Args:
        input_dir: Base input directory to scan for camera folders
        output_dir: Base output directory 
        translation_map: Optional mapping of camera names to translated names/tags
    
    Returns:
        List of (source_path, destination_path, camera_tag) tuples
    """
    cameras = []
    translation_map = translation_map or {}
    
    try:
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"Warning: Input directory {input_dir} does not exist")
            return cameras
        
        # Find all subdirectories in input directory
        for camera_dir in input_path.iterdir():
            if camera_dir.is_dir():
                camera_name = camera_dir.name
                
                # Use translation if available, otherwise use original name
                translated_name = translation_map.get(camera_name, camera_name)
                
                src_path = str(camera_dir)
                dst_path = str(Path(output_dir) / translated_name)
                
                cameras.append((src_path, dst_path, translated_name))
                
        print(f"Discovered {len(cameras)} camera(s): {[cam[2] for cam in cameras]}")
        
    except Exception as e:
        print(f"Error discovering cameras from {input_dir}: {e}")
    
    return cameras


class Logger(ABC):
    """Abstract logger interface for dependency injection"""
    
    @abstractmethod
    def log(self, message: str) -> None:  # pragma: no cover
        pass


class ConsoleLogger(Logger):
    """Console logger implementation"""
    
    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")


class HikvisionInterface(ABC):
    """Abstract interface for Hikvision library operations"""
    
    @abstractmethod
    def get_nas_info(self) -> dict:  # pragma: no cover
        pass
    
    @abstractmethod
    def get_segments(self) -> List[dict]:  # pragma: no cover
        pass
    
    @abstractmethod
    def extract_segment_mp4(self, segment_num: int, cache_path: str, filename: str) -> Optional[str]:  # pragma: no cover
        pass
    
    @abstractmethod
    def extract_segment_jpg(self, segment_num: int, cache_path: str, filename: str) -> Optional[str]:  # pragma: no cover
        pass


class LibHikvisionAdapter(HikvisionInterface):
    """Adapter for the real libHikvision library"""
    
    def __init__(self, src_path: str, video_type: str = 'video'):  # pragma: no cover
        self._hik = libHikvision(src_path, video_type)
    
    def get_nas_info(self) -> dict:  # pragma: no cover
        return self._hik.getNASInfo()
    
    def get_segments(self) -> List[dict]:  # pragma: no cover
        return self._hik.getSegments()
    
    def extract_segment_mp4(self, segment_num: int, cache_path: str, filename: str) -> Optional[str]:  # pragma: no cover
        try:
            result = self._hik.extractSegmentMP4(segment_num, cachePath=cache_path, filename=filename)
            return result if result else None
        except Exception:
            return None
    
    def extract_segment_jpg(self, segment_num: int, cache_path: str, filename: str) -> Optional[str]:  # pragma: no cover
        try:
            result = self._hik.extractSegmentJPG(segment_num, cachePath=cache_path, filename=filename)
            return result if result else None
        except Exception:
            return None

class HikvisionSync:
    def __init__(
        self, 
        cameras: Optional[List[Tuple[str, str, str]]] = None,
        lock_file: Optional[str] = None,
        cache_dir: Optional[str] = None,
        logger: Optional[Logger] = None,
        hikvision_factory: Optional[Callable[[str], HikvisionInterface]] = None,
        retention_days: Optional[int] = None
    ):
        self.cameras = cameras or DEFAULT_CAMERAS
        self.lock_file = lock_file or DEFAULT_LOCK_FILE
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.logger = logger or ConsoleLogger()
        self.hikvision_factory = hikvision_factory or self._default_hikvision_factory
        self.retention_days = retention_days if retention_days is not None else DEFAULT_RETENTION_DAYS
        self.lock_fd = None
    
    def _default_hikvision_factory(self, src_path: str) -> HikvisionInterface:  # pragma: no cover
        """Default factory for creating Hikvision instances"""
        return LibHikvisionAdapter(src_path)
        
    def log(self, message: str):
        """Log with timestamp"""
        self.logger.log(message)
        
    def acquire_lock(self) -> bool:
        """Prevent overlapping runs"""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            return True
        except (OSError, IOError):
            if self.lock_fd:
                self.lock_fd.close()
            return False
            
    def release_lock(self):
        """Release lock"""
        if self.lock_fd:
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            self.lock_fd.close()
            try:
                os.unlink(self.lock_file)
            except OSError:
                pass
                
    def create_directories(self, cameras: List[Tuple[str, str, str]]) -> bool:
        """Create destination directories"""
        try:
            for _, dst, _ in cameras:
                video_dir = Path(dst) / 'video'
                images_dir = Path(dst) / 'images'
                video_dir.mkdir(parents=True, exist_ok=True)
                images_dir.mkdir(parents=True, exist_ok=True)
                self.log(f"Created directories: {video_dir} and {images_dir}")
            return True
        except Exception as e:
            self.log(f"Failed to create directories: {e}")
            return False
            
    def get_unique_filename(self, base_path: str, timestamp: str, cam_tag: str, ext: str) -> str:
        """Generate unique filename to avoid collisions"""
        base_filename = f"{timestamp}-{cam_tag}.{ext}"
        filepath = Path(base_path) / base_filename
        
        counter = 1
        while filepath.exists():
            # Check if existing file might be identical (basic size check would require extracting first)
            name_without_ext = f"{timestamp}-{cam_tag}"
            filepath = Path(base_path) / f"{name_without_ext}_{counter}.{ext}"
            counter += 1
            
            if counter > 1000:
                self.log(f"Too many filename collisions for {base_filename}, using counter {counter-1}")
                break
                
        return str(filepath)
        
    def atomic_write(self, content_func, dest_path: str) -> bool:
        """Atomic file write using temporary file"""
        temp_path = f"{dest_path}.part.{os.getpid()}"
        try:
            # Extract content to temporary file
            success = content_func(temp_path)
            if success:
                # Atomic move
                os.rename(temp_path, dest_path)
                return True
            else:
                # Clean up failed temp file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                return False
        except Exception as e:
            self.log(f"Atomic write failed for {dest_path}: {e}")
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            return False
            
    def apply_retention_policy(self, cameras: List[Tuple[str, str, str]]) -> int:
        """Apply retention policy to delete old files"""
        if self.retention_days <= 0:
            self.log("Retention policy disabled (retention_days <= 0)")
            return 0
            
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        cutoff_timestamp = cutoff_time.timestamp()
        total_deleted = 0
        total_size_freed = 0
        
        self.log(f"Applying retention policy: deleting files older than {self.retention_days} days (before {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        for _, dst_path, cam_tag in cameras:
            try:
                dst_path_obj = Path(dst_path)
                if not dst_path_obj.exists():
                    continue
                
                # Check both video and images directories
                for subdir in ['video', 'images']:
                    subdir_path = dst_path_obj / subdir
                    if not subdir_path.exists():
                        continue
                    
                    for file_path in subdir_path.iterdir():
                        if not file_path.is_file():
                            continue
                            
                        try:
                            # Get file modification time
                            file_mtime = file_path.stat().st_mtime
                            
                            if file_mtime < cutoff_timestamp:
                                file_size = file_path.stat().st_size
                                file_path.unlink()
                                total_deleted += 1
                                total_size_freed += file_size
                                self.log(f"Deleted old file: {file_path} ({file_size} bytes) [{cam_tag}]")
                                
                        except Exception as e:
                            self.log(f"Error deleting file {file_path}: {e}")
                            continue
                            
            except Exception as e:
                self.log(f"Error processing retention for camera {cam_tag}: {e}")
                continue
        
        if total_deleted > 0:
            size_mb = total_size_freed / (1024 * 1024)
            self.log(f"Retention cleanup completed: {total_deleted} files deleted, {size_mb:.1f} MB freed")
        else:
            self.log("Retention cleanup completed: no files needed deletion")
            
        return total_deleted
            
    def process_camera(self, src_path: str, dst_path: str, cam_tag: str):
        """Process a single camera's Hikvision data"""
        self.log(f"Processing camera '{cam_tag}': {src_path} -> {dst_path}")
        
        # Check if source directory exists
        if not Path(src_path).exists():
            self.log(f"Warning: Source directory does not exist: {src_path}")
            return
            
        try:
            # Initialize Hikvision interface for video processing
            hik = self.hikvision_factory(src_path)
            
            # Get NAS info for verification
            nas_info = hik.get_nas_info()
            self.log(f"Camera NAS info: {nas_info}")
            
            # Get all segments
            segments = hik.get_segments()
            self.log(f"Found {len(segments)} segments for camera {cam_tag}")
            
            processed_count = 0
            
            for num, segment in enumerate(segments):
                try:
                    # Parse segment time
                    start_time = segment.get('cust_startTime')
                    if not start_time:
                        continue
                        
                    # Convert to timestamp for age check
                    if isinstance(start_time, str):
                        try:
                            segment_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                segment_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            except ValueError:
                                self.log(f"Could not parse segment time: {start_time}")
                                continue
                    else:
                        segment_dt = start_time
                        
                    segment_timestamp = segment_dt.timestamp()
                    
                    # Process all segments (age check removed)
                        
                    # Format timestamp for filename
                    ts_formatted = segment_dt.strftime('%Y-%m-%d_%H-%M-%S')
                    
                    # Try to extract MP4 video using temporary cache directory
                    video_dest = self.get_unique_filename(
                        base_path=str(Path(dst_path) / 'video'), 
                        timestamp=ts_formatted, 
                        cam_tag=cam_tag, 
                        ext='mp4',
                    )
                    
                    try:
                        os.makedirs(self.cache_dir, exist_ok=True)
                        
                        # Use a simple filename for extraction
                        temp_video_name = f"video_{num}.mp4"
                        
                        # Try extracting - let libhikvision handle the path resolution
                        extracted_path = hik.extract_segment_mp4(num, self.cache_dir, temp_video_name)
                        if extracted_path:
                            # Use the actual path returned by the library
                            if os.path.exists(extracted_path) and os.path.getsize(extracted_path) > 0:
                                # Move to final destination
                                os.rename(extracted_path, video_dest)
                                self.log(f"Extracted video: segment {num} -> {video_dest} [{cam_tag}]")
                                processed_count += 1
                            else:
                                self.log(f"Video extraction succeeded but file not found or empty: {extracted_path}")
                        else:
                            self.log(f"Video extraction failed for segment {num}")
                    except Exception as e:
                        self.log(f"Extract video error for segment {num}: {e}")
                        
                    # Try to extract JPG image using temporary cache directory  
                    image_dest = self.get_unique_filename(
                        base_path=str(Path(dst_path) / 'images'), 
                        timestamp=ts_formatted, 
                        cam_tag=cam_tag, 
                        ext='jpg',
                    )
                    
                    try:
                        os.makedirs(self.cache_dir, exist_ok=True)
                        
                        # Use a simple filename for extraction
                        temp_image_name = f"image_{num}.jpg"
                        
                        # Try extracting - let libhikvision handle the path resolution
                        extracted_path = hik.extract_segment_jpg(num, self.cache_dir, temp_image_name)
                        if extracted_path:
                            # Use the actual path returned by the library
                            if os.path.exists(extracted_path) and os.path.getsize(extracted_path) > 0:
                                # Move to final destination
                                os.rename(extracted_path, image_dest)
                                self.log(f"Extracted image: segment {num} -> {image_dest} [{cam_tag}]")
                            else:
                                self.log(f"Image extraction succeeded but file not found or empty: {extracted_path}")
                        else:
                            self.log(f"Image extraction failed for segment {num}")
                    except Exception as e:
                        self.log(f"Extract image error for segment {num}: {e}")
                        
                except Exception as e:
                    self.log(f"Error processing segment {num} for camera {cam_tag}: {e}")
                    continue
                    
            self.log(f"Completed processing camera {cam_tag}: {processed_count} segments processed")
            
        except Exception as e:
            self.log(f"Error processing camera {cam_tag}: {e}")
            
    def run(self):
        """Main execution function"""
        if not self.acquire_lock():
            self.log("Another instance is already running, exiting")
            return 1
            
        try:
            self.log(f"Starting multi-camera Hikvision sync for {len(self.cameras)} camera(s)")
            
            # Create destination directories
            if not self.create_directories(self.cameras):
                return 1
                
            # Process each camera
            for src_path, dst_path, cam_tag in self.cameras:
                self.process_camera(src_path, dst_path, cam_tag)
                
            # Apply retention policy after processing
            self.apply_retention_policy(self.cameras)
                
            self.log("Multi-camera Hikvision sync completed")
            return 0
            
        except KeyboardInterrupt:
            self.log("Interrupted by user")
            return 1
        except Exception as e:
            self.log(f"Unexpected error: {e}")
            return 1
        finally:
            self.release_lock()

if __name__ == '__main__':  # pragma: no cover
    # Check if running in containerized environment
    input_dir = os.getenv('INPUT_DIR', DEFAULT_INPUT_DIR)
    output_dir = os.getenv('OUTPUT_DIR', DEFAULT_OUTPUT_DIR)
    cache_dir = os.getenv('CACHE_DIR', DEFAULT_CACHE_DIR)
    lock_file = os.getenv('LOCK_FILE', DEFAULT_LOCK_FILE)
    camera_translation_env = os.getenv('CAMERA_TRANSLATION', '')
    retention_days = int(os.getenv('RETENTION_DAYS', str(DEFAULT_RETENTION_DAYS)))
    
    # Parse camera translation table
    translation_map = parse_camera_translation(camera_translation_env)
    
    # Auto-discover cameras or use defaults
    if Path(input_dir).exists():
        print(f"Using containerized mode: discovering cameras from {input_dir}")
        cameras = discover_cameras(input_dir, output_dir, translation_map)
        
        if not cameras:
            print(f"No cameras found in {input_dir}, exiting")
            sys.exit(1)
    else:
        print(f"Input directory {input_dir} not found, using default camera configuration")
        cameras = DEFAULT_CAMERAS
    
    # Initialize and run sync
    sync = HikvisionSync(
        cameras=cameras,
        lock_file=lock_file,
        cache_dir=cache_dir,
        retention_days=retention_days
    )
    sys.exit(sync.run())
