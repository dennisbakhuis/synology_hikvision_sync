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
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections.abc import Sequence
from typing import TextIO

from libhikvision import libHikvision  # type: ignore[import-not-found]


DEFAULT_LOCK_FILE = "/tmp/sync_hikvision_cameras.lock"
DEFAULT_CACHE_DIR = "/tmp/hikvision_cache"
DEFAULT_INPUT_DIR = "/input"
DEFAULT_OUTPUT_DIR = "/output"
DEFAULT_RETENTION_DAYS = 90
DEFAULT_SYNC_INTERVAL_MINUTES = 10
DEFAULT_RUN_MODE = "once"


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


class HikvisionScheduler:
    """Scheduler for running HikvisionSync at regular intervals.

    Parameters
    ----------
    sync_instance : HikvisionSync
        Instance of HikvisionSync to run on schedule
    interval_minutes : int
        Interval between sync runs in minutes
    """

    def __init__(self, sync_instance: "HikvisionSync", interval_minutes: int) -> None:
        self.sync = sync_instance
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.running = False
        self.setup_signal_handlers()

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown.

        Sets up handlers for SIGTERM and SIGINT signals to allow
        graceful shutdown of the scheduler.
        """

        def signal_handler(signum: int, _frame: object) -> None:
            signal_name = signal.Signals(signum).name
            log_message(f"Received {signal_name} signal, shutting down gracefully...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def run_scheduled(self) -> int:
        """Run the sync process in a loop with the specified interval.

        Returns
        -------
        int
            Exit code: 0 if stopped gracefully, 1 if error occurred
        """
        log_message(f"Starting scheduler: sync every {self.interval_minutes} minutes")
        self.running = True

        try:
            log_message("Running initial sync...")
            self.sync.run()

            while self.running:
                log_message(
                    f"Waiting {self.interval_minutes} minutes until next sync..."
                )

                elapsed = 0
                while elapsed < self.interval_seconds and self.running:
                    time.sleep(1)
                    elapsed += 1

                if self.running:  # pragma: no cover
                    log_message("Starting scheduled sync...")
                    self.sync.run()

        except KeyboardInterrupt:
            log_message("Interrupted by user")
        except Exception as e:
            log_message(f"Scheduler error: {e}")
        finally:
            log_message("Scheduler stopped")

        return 0 if not self.running else 1


class HikvisionSync:
    def __init__(
        self,
        cameras: Sequence[tuple[Path | str, Path | str, str]] | None = None,
        lock_file: str | None = None,
        cache_directory: str | None = None,
        retention_days: int | None = None,
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
        self.lock_file_descriptor: TextIO | None = None

    def log(self, message: str) -> None:
        """Log message with timestamp.

        Parameters
        ----------
        message : str
            Message to log
        """
        log_message(message)

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
            image_statistics = self._process_media(
                source_path, destination_path, camera_tag, "image"
            )

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

            file_extension = "mp4" if media_type == "video" else "jpg"
            media_directory = (
                Path(destination_path) / f"{media_type}s"
                if media_type == "image"
                else Path(destination_path) / media_type
            )
            media_directory.mkdir(parents=True, exist_ok=True)

            existing_files_set = (
                {file.name for file in media_directory.iterdir() if file.is_file()}
                if media_directory.exists()
                else set()
            )

            new_files_count = existing_files_count = failed_files_count = 0

            for segment_number, segment_data in enumerate(segments_list):
                try:
                    segment_start_time = segment_data.get("cust_startTime")
                    if not segment_start_time:
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

                    if media_type == "video":
                        extraction_result = hikvision_instance.extractSegmentMP4(
                            segment_number,
                            cachePath=self.cache_directory,
                            filename=destination_file_path,
                        )
                    else:
                        extraction_result = hikvision_instance.extractSegmentJPG(
                            segment_number,
                            cachePath=self.cache_directory,
                            filename=destination_file_path,
                        )

                    if (
                        extraction_result
                        and os.path.exists(destination_file_path)
                        and os.path.getsize(destination_file_path) > 0
                    ):
                        self.log(
                            f"Extracted {media_type}: {destination_file_path} [{camera_tag}]"
                        )
                        new_files_count += 1
                        existing_files_set.add(output_filename)
                    else:
                        failed_files_count += 1

                except Exception:
                    failed_files_count += 1

            if existing_files_count > 0:
                self.log(
                    f"Skipped {existing_files_count} existing {media_type} files for camera {camera_tag}"
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
                f"Efficiency: {(total_existing_files/total_segments_processed)*100:.1f}% skipped"
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
            self.log(f"Starting sync for {len(self.cameras)} camera(s)")
            self.create_directories()

            all_camera_statistics = {}
            for source_path, destination_path, camera_tag in self.cameras:
                all_camera_statistics[camera_tag] = self.process_camera(
                    source_path, destination_path, camera_tag
                )

            deleted_files_count = self.apply_retention_policy()
            self._generate_summary_report(all_camera_statistics, deleted_files_count)
            self.log("Sync completed")
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
    RUN_MODE : str
        Run mode (once or scheduled)
    SYNC_INTERVAL_MINUTES : int
        Sync interval in minutes for scheduled mode

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
        "--run-mode",
        "-m",
        type=str,
        choices=["once", "scheduled"],
        default=os.getenv("RUN_MODE", DEFAULT_RUN_MODE).lower(),
        help=f"Run mode: once or scheduled (default: {DEFAULT_RUN_MODE})",
    )

    parser.add_argument(
        "--sync-interval",
        "-s",
        type=int,
        default=int(
            os.getenv("SYNC_INTERVAL_MINUTES", str(DEFAULT_SYNC_INTERVAL_MINUTES))
        ),
        help=f"Sync interval in minutes for scheduled mode (1-1440) (default: {DEFAULT_SYNC_INTERVAL_MINUTES})",
    )

    return parser


if __name__ == "__main__":  # pragma: no cover
    parser = create_argument_parser()
    args = parser.parse_args()

    # Validate arguments
    if args.sync_interval < 1 or args.sync_interval > 1440:
        parser.error(
            f"sync-interval must be between 1 and 1440 minutes, got: {args.sync_interval}"
        )

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
    )

    if args.run_mode == "once":
        print("Running sync once...")
        sys.exit(sync.run())
    elif args.run_mode == "scheduled":
        print("WARNING: Python-based scheduling is deprecated.")
        print(
            "Please use shell-based scheduling (RUN_MODE=scheduled in entrypoint.sh)."
        )
        print(f"Running sync in scheduled mode (every {args.sync_interval} minutes)...")
        scheduler = HikvisionScheduler(sync, args.sync_interval)
        sys.exit(scheduler.run_scheduled())
