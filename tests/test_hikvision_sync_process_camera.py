#!/usr/bin/env python3
"""
Tests for HikvisionSync.process_camera method
"""

import os
import sys
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncProcessCamera:
    """Test HikvisionSync camera processing"""

    def test_process_camera_nonexistent_source(self) -> None:
        """Test processing camera with non-existent source directory"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        with patch.object(sync, "log") as mock_log:
            result = sync.process_camera("/nonexistent", "/dst", "test_cam")

            expected_result = {
                "videos": {"total": 0, "existing": 0, "new": 0, "failed": 0},
                "images": {"total": 0, "existing": 0, "new": 0, "failed": 0},
            }
            assert result == expected_result
            mock_log.assert_any_call(
                "Warning: Source directory does not exist: /nonexistent"
            )

    def test_process_camera_success(self) -> None:
        """Test successful camera processing"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        mock_video_stats = {"total": 10, "existing": 3, "new": 5, "failed": 2}
        mock_image_stats = {"total": 8, "existing": 2, "new": 4, "failed": 2}

        with patch.object(sync, "log") as mock_log:
            with patch.object(
                sync, "_process_media", side_effect=[mock_video_stats, mock_image_stats]
            ):
                with patch("pathlib.Path.exists", return_value=True):
                    result = sync.process_camera("/src", "/dst", "test_cam")

                    expected_result = {
                        "videos": mock_video_stats,
                        "images": mock_image_stats,
                    }
                    assert result == expected_result

                    # Should log processing start and completion
                    log_calls = [call[0][0] for call in mock_log.call_args_list]
                    assert any(
                        "Processing camera 'test_cam'" in call for call in log_calls
                    )
                    assert any(
                        "Completed processing camera test_cam" in call
                        for call in log_calls
                    )

    def test_process_camera_exception(self) -> None:
        """Test camera processing with exception"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        with patch.object(sync, "log") as mock_log:
            with patch.object(
                sync, "_process_media", side_effect=Exception("Processing error")
            ):
                with patch("pathlib.Path.exists", return_value=True):
                    result = sync.process_camera("/src", "/dst", "test_cam")

                    expected_result = {
                        "videos": {"total": 0, "existing": 0, "new": 0, "failed": 0},
                        "images": {"total": 0, "existing": 0, "new": 0, "failed": 0},
                    }
                    assert result == expected_result

                    # Should log error
                    log_calls = [call[0][0] for call in mock_log.call_args_list]
                    assert any(
                        "Error processing camera test_cam" in call for call in log_calls
                    )
