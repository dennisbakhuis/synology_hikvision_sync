#!/usr/bin/env python3
"""
Tests for HikvisionSync.run method
"""

import os
import sys
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncRun:
    """Test HikvisionSync main run method"""

    def test_run_lock_acquisition_failure(self) -> None:
        """Test run method when lock acquisition fails"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        with patch.object(sync, "acquire_lock", return_value=False):
            with patch.object(sync, "log") as mock_log:
                result = sync.run()

                assert result == 1
                mock_log.assert_called_with(
                    "Another instance is already running, exiting"
                )

    def test_run_successful_execution(self) -> None:
        """Test successful run execution"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        mock_camera_stats = {
            "test_cam": {
                "videos": {"total": 5, "existing": 2, "new": 3, "failed": 0},
                "images": {"total": 4, "existing": 1, "new": 3, "failed": 0},
            }
        }

        with patch.object(sync, "acquire_lock", return_value=True):
            with patch.object(sync, "create_directories"):
                with patch.object(
                    sync, "process_camera", return_value=mock_camera_stats["test_cam"]
                ):
                    with patch.object(sync, "apply_retention_policy", return_value=2):
                        with patch.object(sync, "_generate_summary_report"):
                            with patch.object(sync, "release_lock"):
                                with patch.object(sync, "log"):
                                    result = sync.run()

                                    assert result == 0

    def test_run_keyboard_interrupt(self) -> None:
        """Test run method with keyboard interrupt"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        with patch.object(sync, "acquire_lock", return_value=True):
            with patch.object(
                sync, "create_directories", side_effect=KeyboardInterrupt()
            ):
                with patch.object(sync, "release_lock"):
                    with patch.object(sync, "log") as mock_log:
                        result = sync.run()

                        assert result == 1
                        mock_log.assert_any_call("Interrupted by user")

    def test_run_unexpected_exception(self) -> None:
        """Test run method with unexpected exception"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        with patch.object(sync, "acquire_lock", return_value=True):
            with patch.object(
                sync, "create_directories", side_effect=Exception("Test error")
            ):
                with patch.object(sync, "release_lock"):
                    with patch.object(sync, "log") as mock_log:
                        result = sync.run()

                        assert result == 1
                        mock_log.assert_any_call("Unexpected error: Test error")

    def test_run_always_releases_lock(self) -> None:
        """Test that run method always releases lock in finally block"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        with patch.object(sync, "acquire_lock", return_value=True):
            with patch.object(
                sync, "create_directories", side_effect=Exception("Test error")
            ):
                with patch.object(sync, "release_lock") as mock_release:
                    with patch.object(sync, "log"):
                        sync.run()

                        mock_release.assert_called_once()
