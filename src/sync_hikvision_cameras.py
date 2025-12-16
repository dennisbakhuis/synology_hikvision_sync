#!/usr/bin/python3
#
# Script-name : sync_hikvision_cameras.py
# Author      : Dennis Bakhuis
# Date        : 2025-09-05
# License     : MIT
#
# Multi-camera sync script for Hikvision NAS storage using libhikvision.
# Extracts video segments and images from Hikvision format to organized folders with timestamped filenames.
import os
import sys
import fcntl
import argparse
import signal
from pathlib import Path
from datetime import datetime, timedelta
from collections.abc import Sequence, Generator
from contextlib import contextmanager
from typing import TextIO, Any

from libhikvision import libHikvision


DEFAULT_LOCK_FILE = "/tmp/sync_hikvision_cameras.lock"
DEFAULT_CACHE_DIR = "/tmp/hikvision_cache"
DEFAULT_INPUT_DIR = "/input"
DEFAULT_OUTPUT_DIR = "/output"
DEFAULT_RETENTION_DAYS = 90
DEFAULT_EXTRACTION_TIMEOUT_SECONDS = 60
DEFAULT_VIDEO_SYNC_DAYS = 7
DEFAULT_IMAGE_SYNC_DAYS = 7
DEFAULT_SYNC_IMAGES = True
DEFAULT_USE_FAST_EXTRACTION = True


def parse_camera_translation(translation_env: str) -> dict[str, str]:
    """Parse camera translation table from environment variable.

    Parameters
    ----------
    translation_env : str
        Environment variable string with camera translations.
        Format: "Camera-Tuin:garden,Camera-Oprit:driveway,Another-Name:another_tag"

    Returns
    -------
    dict[str, str]
        Dictionary mapping original camera names to translated names
    """
    translation_map: dict[str, str] = {}
    if not translation_env:
        return translation_map

    try:
        pairs = translation_env.split(",")
        for pair in pairs:
            pair = pair.strip()
            if ":" in pair:
                original, translated = pair.split(":", 1)
                translation_map[original.strip()] = translated.strip()
    except Exception as e:
        print(f"Warning: Failed to parse camera translation '{translation_env}': {e}")

    return translation_map


def parse_bool_env(env_var: str, default: bool = True) -> bool:
    """Parse boolean from environment variable.

    Parameters
    ----------
    env_var : str
        Environment variable value to parse
    default : bool, default=True
        Default value if env_var is empty or invalid

    Returns
    -------
    bool
        Parsed boolean value
    """
    value = env_var.lower().strip()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    return default


@contextmanager
def extraction_timeout(seconds: int) -> Generator[None, None, None]:
    """Context manager for extraction timeout using SIGALRM.

    Note: POSIX-only (Linux, macOS). Not compatible with Windows.
    Works in Docker containers (Linux-based).

    Parameters
    ----------
    seconds : int
        Timeout duration in seconds

    Raises
    ------
    TimeoutError
        If operation exceeds timeout duration
    """

    def timeout_handler(signum: Any, frame: Any) -> None:
        raise TimeoutError(f"Extraction timed out after {seconds} seconds")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def discover_cameras(
    input_dir: str = DEFAULT_INPUT_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    translation_map: dict[str, str] | None = None,
) -> Sequence[tuple[Path | str, Path | str, str]]:
    """Automatically discover cameras from input directory.

    Parameters
    ----------
    input_dir : str, default=DEFAULT_INPUT_DIR
        Base input directory to scan for camera folders
    output_dir : str, default=DEFAULT_OUTPUT_DIR
        Base output directory
    translation_map : dict[str, str] | None, default=None
        Optional mapping of camera names to translated names/tags

    Returns
    -------
    list[tuple[Path | str, Path | str, str]]
        List of (source_path, destination_path, camera_tag) tuples
    """
    cameras: list[tuple[Path | str, Path | str, str]] = []
    translation_map = translation_map or {}

    try:
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"Warning: Input directory {input_dir} does not exist")
            return cameras

        for camera_dir in input_path.iterdir():
            if camera_dir.is_dir():
                camera_name = camera_dir.name

                translated_name = translation_map.get(camera_name, camera_name)

                src_path = camera_dir
                dst_path = Path(output_dir) / translated_name

                cameras.append((src_path, dst_path, translated_name))

        print(f"Discovered {len(cameras)} camera(s): {[cam[2] for cam in cameras]}")

    except Exception as e:
        print(f"Error discovering cameras from {input_dir}: {e}")

    return cameras


def log_message(message: str) -> None:
    """Log message with timestamp prefix.

    Parameters
    ----------
    message : str
        Message to log with timestamp
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


class HikvisionSync:
    def __init__(
        self,
        cameras: Sequence[tuple[Path | str, Path | str, str]] | None = None,
        lock_file: str | None = None,
        cache_directory: str | None = None,
        retention_days: int | None = None,
        video_sync_days: int | None = None,
        image_sync_days: int | None = None,
        sync_images: bool = True,
        extraction_timeout_seconds: int | None = None,
        use_fast_extraction: bool = True,
    ) -> None:
        if cameras is None:
            raise ValueError(
                "No cameras provided. Use discover_cameras() to find cameras or provide explicit camera configuration."
            )
        self.cameras: Sequence[tuple[Path | str, Path | str, str]] = list(cameras)
        self.lock_file = lock_file or DEFAULT_LOCK_FILE
        self.cache_directory = cache_directory or DEFAULT_CACHE_DIR
        self.retention_days = (
            retention_days if retention_days is not None else DEFAULT_RETENTION_DAYS
        )
        self.video_sync_days = (
            video_sync_days if video_sync_days is not None else DEFAULT_VIDEO_SYNC_DAYS
        )
        self.image_sync_days = (
            image_sync_days if image_sync_days is not None else DEFAULT_IMAGE_SYNC_DAYS
        )
        self.sync_images = sync_images
        self.extraction_timeout_seconds = (
            extraction_timeout_seconds
            if extraction_timeout_seconds is not None
            else DEFAULT_EXTRACTION_TIMEOUT_SECONDS
        )
        self.use_fast_extraction = use_fast_extraction
        self.lock_file_descriptor: TextIO | None = None

    def log(self, message: str) -> None:
        """Log message with timestamp.

        Parameters
        ----------
        message : str
            Message to log
        """
        log_message(message)

    def _is_same_filesystem(self, path1: Path, path2: Path) -> bool:
        """Check if two paths are on the same filesystem.

        Parameters
        ----------
        path1 : Path
            First path to check
        path2 : Path
            Second path to check

        Returns
        -------
        bool
            True if both paths are on same filesystem, False otherwise
        """
        try:
            return os.stat(path1).st_dev == os.stat(path2).st_dev
        except OSError:
            return False

    def _extract_video_fast(self, segment: dict, output_path: Path) -> bool:
        """Fast extraction for same-disk operations - copies byte range directly.

        Parameters
        ----------
        segment : dict
            Segment metadata from libHikvision with 'cust_filePath', 'startOffset', 'endOffset'
        output_path : Path
            Destination file path for extracted video

        Returns
        -------
        bool
            True if extraction succeeded, False if failed (for fallback to libHikvision)
        """
        try:
            source_file = segment["cust_filePath"]
            start_offset = segment["startOffset"]
            end_offset = segment["endOffset"]

            with open(source_file, "rb") as src, open(output_path, "wb") as dst:
                src.seek(start_offset)
                remaining = end_offset - start_offset
                chunk_size = 4096

                while remaining > 0:
                    chunk = src.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    dst.write(chunk)
                    remaining -= len(chunk)

            return True
        except Exception:
            return False

    def acquire_lock(self) -> bool:
        """Acquire file lock to prevent overlapping runs.

        Returns
        -------
        bool
            True if lock acquired successfully, False otherwise
        """
        try:
            self.lock_file_descriptor = open(self.lock_file, "w")
            fcntl.flock(self.lock_file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file_descriptor.write(str(os.getpid()))
            self.lock_file_descriptor.flush()
            return True
        except (OSError, IOError):
            if self.lock_file_descriptor:
                self.lock_file_descriptor.close()
            return False

    def release_lock(self) -> None:
        """Release file lock and clean up lock file."""
        if self.lock_file_descriptor:
            fcntl.flock(self.lock_file_descriptor, fcntl.LOCK_UN)
            self.lock_file_descriptor.close()
            try:
                os.unlink(self.lock_file)
            except OSError:
                pass

    def create_directories(self) -> None:
        """Create destination directories for all cameras.

        Creates 'video' and 'images' subdirectories for each camera's
        destination path.
        """
        for _, destination_path, _ in self.cameras:
            (Path(destination_path) / "video").mkdir(parents=True, exist_ok=True)
            (Path(destination_path) / "images").mkdir(parents=True, exist_ok=True)

    def apply_retention_policy(self) -> int:
        """Apply retention policy to delete old files.

        Deletes files older than the configured retention period from
        all camera destination directories.

        Returns
        -------
        int
            Number of files deleted
        """
        if self.retention_days <= 0:
            self.log("Retention policy disabled (retention_days <= 0)")
            return 0

        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        cutoff_timestamp = cutoff_time.timestamp()
        total_deleted = 0
        total_size_freed = 0

        self.log(
            f"Applying retention policy: deleting files older than {self.retention_days} days"
        )

        for _, destination_path, camera_tag in self.cameras:
            try:
                destination_path_object = Path(destination_path)
                if not destination_path_object.exists():
                    continue

                for subdirectory_name in ["video", "images"]:
                    subdirectory_path = destination_path_object / subdirectory_name
                    if not subdirectory_path.exists():
                        continue

                    for file_path in subdirectory_path.iterdir():
                        if not file_path.is_file():
                            continue

                        try:
                            file_modification_time = file_path.stat().st_mtime

                            if file_modification_time < cutoff_timestamp:
                                file_size = file_path.stat().st_size
                                file_path.unlink()
                                total_deleted += 1
                                total_size_freed += file_size
                                self.log(
                                    f"Deleted old file: {file_path} ({file_size} bytes) [{camera_tag}]"
                                )

                        except Exception as e:
                            self.log(f"Error deleting file {file_path}: {e}")
                            continue

            except Exception as e:
                self.log(f"Error processing retention for camera {camera_tag}: {e}")
                continue

        if total_deleted > 0:
            size_megabytes = total_size_freed / (1024 * 1024)
            self.log(
                f"Retention cleanup completed: {total_deleted} files deleted, {size_megabytes:.1f} MB freed"
            )
        else:
            self.log("Retention cleanup completed: no files needed deletion")

        return total_deleted

    def process_camera(
        self, source_path: Path | str, destination_path: Path | str, camera_tag: str
    ) -> dict[str, dict[str, int]]:
        """Process a single camera's Hikvision data.

        Parameters
        ----------
        source_path : Path | str
            Path to camera's Hikvision data directory
        destination_path : Path | str
            Path to output directory for processed files
        camera_tag : str
            Tag/name identifier for the camera

        Returns
        -------
        dict[str, dict[str, int]]
            Statistics dictionary with 'videos' and 'images' keys,
            each containing 'total', 'existing', 'new', and 'failed' counts
        """
        self.log(
            f"Processing camera '{camera_tag}': {source_path} -> {destination_path}"
        )

        if not Path(source_path).exists():
            self.log(f"Warning: Source directory does not exist: {source_path}")
            return {
                "videos": {"total": 0, "existing": 0, "new": 0, "failed": 0},
                "images": {"total": 0, "existing": 0, "new": 0, "failed": 0},
            }

        try:
            video_statistics = self._process_media(
                source_path, destination_path, camera_tag, "video"
            )

            if self.sync_images:
                image_statistics = self._process_media(
                    source_path, destination_path, camera_tag, "image"
                )
            else:
                self.log(f"Skipping image sync (disabled) for camera {camera_tag}")
                image_statistics = {"total": 0, "existing": 0, "new": 0, "failed": 0}

            self.log(
                f"Completed processing camera {camera_tag}: {video_statistics['new']} videos, {image_statistics['new']} images"
            )

            return {"videos": video_statistics, "images": image_statistics}

        except Exception as e:
            self.log(f"Error processing camera {camera_tag}: {e}")
            return {
                "videos": {"total": 0, "existing": 0, "new": 0, "failed": 0},
                "images": {"total": 0, "existing": 0, "new": 0, "failed": 0},
            }

    def _process_media(
        self,
        source_path: Path | str,
        destination_path: Path | str,
        camera_tag: str,
        media_type: str,
    ) -> dict[str, int]:
        """Process video or image segments for a camera.

        Parameters
        ----------
        source_path : Path | str
            Path to camera's Hikvision data directory
        destination_path : Path | str
            Path to output directory for processed files
        camera_tag : str
            Tag/name identifier for the camera
        media_type : str
            Type of media to process ('video' or 'image')

        Returns
        -------
        dict[str, int]
            Statistics dictionary containing 'total', 'existing', 'new',
            and 'failed' counts for processed segments
        """
        try:
            hikvision_instance = libHikvision(f"{str(source_path)}/", media_type)
            segments_list = hikvision_instance.getSegments()
            self.log(
                f"Found {len(segments_list)} {media_type} segments for camera {camera_tag}"
            )

            sync_days = (
                self.video_sync_days if media_type == "video" else self.image_sync_days
            )
            cutoff_time = None
            if sync_days > 0:
                cutoff_time = datetime.now() - timedelta(days=sync_days)

            file_extension = "mp4" if media_type == "video" else "jpg"
            media_directory = (
                Path(destination_path) / f"{media_type}s"
                if media_type == "image"
                else Path(destination_path) / media_type
            )
            media_directory.mkdir(parents=True, exist_ok=True)

            if media_directory.exists():
                try:
                    existing_files_set = {
                        name
                        for name in os.listdir(media_directory)
                        if os.path.isfile(os.path.join(media_directory, name))
                    }
                except (OSError, PermissionError) as e:
                    self.log(
                        f"Warning: Could not list directory {media_directory}: {e}"
                    )
                    existing_files_set = set()
            else:
                existing_files_set = set()

            new_files_count = existing_files_count = failed_files_count = (
                skipped_old_count
            ) = skipped_no_timestamp_count = timed_out_count = fast_path_count = 0

            for segment_number, segment_data in enumerate(segments_list):
                try:
                    segment_start_time = segment_data.get("cust_startTime")
                    if not segment_start_time:
                        skipped_no_timestamp_count += 1
                        continue

                    if cutoff_time and segment_start_time < cutoff_time:
                        skipped_old_count += 1
                        continue

                    timestamp_formatted = segment_start_time.strftime(
                        "%Y-%m-%d_%H-%M-%S"
                    )
                    output_filename = (
                        f"{timestamp_formatted}-{camera_tag}.{file_extension}"
                    )

                    if output_filename in existing_files_set:
                        existing_files_count += 1
                        continue

                    destination_file_path = str(media_directory / output_filename)

                    use_fast_path = (
                        self.use_fast_extraction
                        and media_type == "video"
                        and self._is_same_filesystem(
                            Path(source_path), Path(destination_path)
                        )
                    )

                    try:
                        timeout_seconds = (
                            self.extraction_timeout_seconds
                            if self.extraction_timeout_seconds > 0
                            else 999999
                        )

                        with extraction_timeout(timeout_seconds):
                            extraction_result = False

                            if use_fast_path:
                                extraction_result = self._extract_video_fast(
                                    segment_data, Path(destination_file_path)
                                )
                                if extraction_result:
                                    fast_path_count += 1

                            if not extraction_result:
                                if media_type == "video":
                                    extraction_result = (
                                        hikvision_instance.extractSegmentMP4(
                                            segment_number,
                                            cachePath=self.cache_directory,
                                            filename=destination_file_path,
                                        )
                                    )
                                else:
                                    extraction_result = (
                                        hikvision_instance.extractSegmentJPG(
                                            segment_number,
                                            cachePath=self.cache_directory,
                                            filename=destination_file_path,
                                        )
                                    )

                        if (
                            extraction_result
                            and os.path.exists(destination_file_path)
                            and os.path.getsize(destination_file_path) > 0
                        ):
                            new_files_count += 1
                            existing_files_set.add(output_filename)
                        else:
                            failed_files_count += 1

                    except TimeoutError as e:
                        timed_out_count += 1
                        self.log(
                            f"Timeout extracting {media_type} segment {segment_number} for camera {camera_tag}: {e}"
                        )
                        continue

                except Exception:
                    failed_files_count += 1

            if new_files_count > 0:
                self.log(
                    f"Downloaded {new_files_count} new {media_type} files for camera {camera_tag}"
                )
            if existing_files_count > 0:
                self.log(
                    f"Skipped {existing_files_count} existing {media_type} files for camera {camera_tag}"
                )
            if skipped_old_count > 0:
                self.log(
                    f"Skipped {skipped_old_count} old {media_type} segments (beyond {sync_days}-day sync window) for camera {camera_tag}"
                )
            if skipped_no_timestamp_count > 0:
                self.log(
                    f"Skipped {skipped_no_timestamp_count} {media_type} segments (missing timestamp) for camera {camera_tag}"
                )
            if failed_files_count > 0:
                self.log(
                    f"Failed to process {failed_files_count} {media_type} segments for camera {camera_tag}"
                )
            if timed_out_count > 0:
                self.log(
                    f"Timed out on {timed_out_count} {media_type} segments for camera {camera_tag}"
                )
            if fast_path_count > 0:
                self.log(
                    f"Used fast extraction for {fast_path_count} {media_type} segments for camera {camera_tag}"
                )

            return {
                "total": len(segments_list),
                "existing": existing_files_count,
                "new": new_files_count,
                "failed": failed_files_count,
            }

        except Exception as e:
            self.log(f"Error processing {media_type}s for camera {camera_tag}: {e}")
            return {"total": 0, "existing": 0, "new": 0, "failed": 0}

    def _generate_summary_report(
        self,
        all_camera_statistics: dict[str, dict[str, dict[str, int]]],
        deleted_files_count: int,
    ) -> None:
        """Generate and log summary report of sync operation.

        Parameters
        ----------
        all_camera_statistics : dict[str, dict[str, dict[str, int]]]
            Dictionary mapping camera tags to their processing statistics
        deleted_files_count : int
            Number of files deleted by retention policy
        """
        self.log("=" * 50)
        self.log("SYNC SUMMARY REPORT")
        self.log("=" * 50)

        summary_totals = {
            "videos": {"total": 0, "existing": 0, "new": 0, "failed": 0},
            "images": {"total": 0, "existing": 0, "new": 0, "failed": 0},
        }

        for camera_tag, camera_statistics in all_camera_statistics.items():
            self.log(
                f"{camera_tag}: Videos {camera_statistics['videos']['new']}/{camera_statistics['videos']['total']}, Images {camera_statistics['images']['new']}/{camera_statistics['images']['total']}"
            )
            for media_type in ["videos", "images"]:
                for statistic_key in summary_totals[media_type]:
                    summary_totals[media_type][statistic_key] += camera_statistics[
                        media_type
                    ][statistic_key]

        total_segments_processed = (
            summary_totals["videos"]["total"] + summary_totals["images"]["total"]
        )
        total_new_files = (
            summary_totals["videos"]["new"] + summary_totals["images"]["new"]
        )
        total_existing_files = (
            summary_totals["videos"]["existing"] + summary_totals["images"]["existing"]
        )

        self.log(
            f"Total: {total_new_files} new, {total_existing_files} existing, {total_segments_processed} segments"
        )
        if deleted_files_count:
            self.log(f"Retention: {deleted_files_count} old files deleted")
        if total_segments_processed:
            self.log(
                f"Efficiency: {(total_existing_files / total_segments_processed) * 100:.1f}% skipped"
            )
        self.log("=" * 50)

    def run(self) -> int:
        """Main execution function for sync operation.

        Returns
        -------
        int
            Exit code: 0 if successful, 1 if error occurred
        """
        if not self.acquire_lock():
            self.log("Another instance is already running, exiting")
            return 1

        try:
            start_time = datetime.now()
            self.log(
                f"=== SYNC STARTED at {start_time.strftime('%Y-%m-%d %H:%M:%S')} ==="
            )
            self.log(f"Starting sync for {len(self.cameras)} camera(s)")
            self.create_directories()

            all_camera_statistics = {}
            for source_path, destination_path, camera_tag in self.cameras:
                all_camera_statistics[camera_tag] = self.process_camera(
                    source_path, destination_path, camera_tag
                )

            deleted_files_count = self.apply_retention_policy()
            self._generate_summary_report(all_camera_statistics, deleted_files_count)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.log(
                f"=== SYNC COMPLETED at {end_time.strftime('%Y-%m-%d %H:%M:%S')} (duration: {duration:.1f}s) ==="
            )
            return 0

        except KeyboardInterrupt:
            self.log("Interrupted by user")
            return 1
        except Exception as e:
            self.log(f"Unexpected error: {e}")
            return 1
        finally:
            self.release_lock()


def create_argument_parser() -> argparse.ArgumentParser:  # pragma: no cover
    """Create and configure argument parser.

    The parser supports both command line arguments and environment variables.
    Environment variables take precedence over default values but are overridden
    by explicit command line arguments.

    Environment Variables
    ---------------------
    INPUT_DIR : str
        Input directory to scan for camera folders
    OUTPUT_DIR : str
        Output directory for processed files
    CACHE_DIR : str
        Cache directory for temporary files
    LOCK_FILE : str
        Lock file to prevent overlapping runs
    CAMERA_TRANSLATION : str
        Camera translation mapping
    RETENTION_DAYS : int
        Number of days to retain files
    VIDEO_SYNC_DAYS : int
        Number of days of video segments to sync
    IMAGE_SYNC_DAYS : int
        Number of days of image segments to sync
    SYNC_IMAGES : bool
        Enable or disable image synchronization
    EXTRACTION_TIMEOUT_SECONDS : int
        Timeout in seconds for extracting each segment
    USE_FAST_EXTRACTION : bool
        Enable fast extraction for same-disk operations

    Returns
    -------
    argparse.ArgumentParser
        Configured argument parser instance
    """
    parser = argparse.ArgumentParser(
        description="Multi-camera sync script for Hikvision NAS storage using libhikvision."
    )

    parser.add_argument(
        "--input-dir",
        "-i",
        type=str,
        default=os.getenv("INPUT_DIR", DEFAULT_INPUT_DIR),
        help=f"Input directory to scan for camera folders (default: {DEFAULT_INPUT_DIR})",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
        help=f"Output directory for processed files (default: {DEFAULT_OUTPUT_DIR})",
    )

    parser.add_argument(
        "--cache-dir",
        "-c",
        type=str,
        default=os.getenv("CACHE_DIR", DEFAULT_CACHE_DIR),
        help=f"Cache directory for temporary files (default: {DEFAULT_CACHE_DIR})",
    )

    parser.add_argument(
        "--lock-file",
        "-l",
        type=str,
        default=os.getenv("LOCK_FILE", DEFAULT_LOCK_FILE),
        help=f"Lock file to prevent overlapping runs (default: {DEFAULT_LOCK_FILE})",
    )

    parser.add_argument(
        "--camera-translation",
        "-t",
        type=str,
        default=os.getenv("CAMERA_TRANSLATION", ""),
        help='Camera translation mapping (format: "Camera-Name:tag,Another:tag2")',
    )

    parser.add_argument(
        "--retention-days",
        "-r",
        type=int,
        default=int(os.getenv("RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS))),
        help=f"Number of days to retain files (0 disables retention) (default: {DEFAULT_RETENTION_DAYS})",
    )

    parser.add_argument(
        "--video-sync-days",
        type=int,
        default=int(os.getenv("VIDEO_SYNC_DAYS", str(DEFAULT_VIDEO_SYNC_DAYS))),
        help=f"Number of days of video segments to sync (0 syncs all) (default: {DEFAULT_VIDEO_SYNC_DAYS})",
    )

    parser.add_argument(
        "--image-sync-days",
        type=int,
        default=int(os.getenv("IMAGE_SYNC_DAYS", str(DEFAULT_IMAGE_SYNC_DAYS))),
        help=f"Number of days of image segments to sync (0 syncs all) (default: {DEFAULT_IMAGE_SYNC_DAYS})",
    )

    parser.add_argument(
        "--sync-images",
        type=lambda x: parse_bool_env(x, DEFAULT_SYNC_IMAGES),
        default=parse_bool_env(os.getenv("SYNC_IMAGES", ""), DEFAULT_SYNC_IMAGES),
        help=f"Enable or disable image synchronization (default: {DEFAULT_SYNC_IMAGES})",
    )

    parser.add_argument(
        "--extraction-timeout",
        type=int,
        default=int(
            os.getenv(
                "EXTRACTION_TIMEOUT_SECONDS", str(DEFAULT_EXTRACTION_TIMEOUT_SECONDS)
            )
        ),
        help=f"Timeout in seconds for extracting each segment (0 disables timeout) (default: {DEFAULT_EXTRACTION_TIMEOUT_SECONDS})",
    )

    parser.add_argument(
        "--use-fast-extraction",
        type=lambda x: parse_bool_env(x, DEFAULT_USE_FAST_EXTRACTION),
        default=parse_bool_env(
            os.getenv("USE_FAST_EXTRACTION", ""), DEFAULT_USE_FAST_EXTRACTION
        ),
        help=f"Enable fast extraction for same-disk operations (default: {DEFAULT_USE_FAST_EXTRACTION})",
    )

    return parser


if __name__ == "__main__":  # pragma: no cover
    parser = create_argument_parser()
    args = parser.parse_args()

    translation_map = parse_camera_translation(args.camera_translation)

    if Path(args.input_dir).exists():
        print(f"Using containerized mode: discovering cameras from {args.input_dir}")
        cameras = discover_cameras(args.input_dir, args.output_dir, translation_map)

        if not cameras:
            print(f"No cameras found in {args.input_dir}, exiting")
            sys.exit(1)
    else:
        print(
            f"Input directory {args.input_dir} not found and no cameras could be discovered"
        )
        print(
            "Please ensure the input directory exists or provide explicit camera configuration"
        )
        sys.exit(1)

    sync = HikvisionSync(
        cameras=cameras,
        lock_file=args.lock_file,
        cache_directory=args.cache_dir,
        retention_days=args.retention_days,
        video_sync_days=args.video_sync_days,
        image_sync_days=args.image_sync_days,
        sync_images=args.sync_images,
        extraction_timeout_seconds=args.extraction_timeout,
        use_fast_extraction=args.use_fast_extraction,
    )

    sys.exit(sync.run())
