#!/usr/bin/env python3
"""
Tests for image sync enable/disable toggle
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import HikvisionSync


class TestImageSyncToggle:
    """Test image sync enable/disable functionality"""

    def test_process_camera_with_images_enabled(self) -> None:
        """Test that images are processed when sync_images=True"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")], sync_images=True
        )

        with patch.object(sync, "_process_media") as mock_process:
            mock_process.return_value = {
                "total": 10,
                "existing": 0,
                "new": 10,
                "failed": 0,
            }

            with patch("pathlib.Path.exists", return_value=True):
                result = sync.process_camera("/src", "/dst", "test_cam")

            assert mock_process.call_count == 2
            mock_process.assert_any_call("/src", "/dst", "test_cam", "video")
            mock_process.assert_any_call("/src", "/dst", "test_cam", "image")

            assert result["videos"]["new"] == 10
            assert result["images"]["new"] == 10

    def test_process_camera_with_images_disabled(self) -> None:
        """Test that images are skipped when sync_images=False"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")], sync_images=False
        )

        with patch.object(sync, "_process_media") as mock_process:
            mock_process.return_value = {
                "total": 10,
                "existing": 0,
                "new": 10,
                "failed": 0,
            }

            with patch.object(sync, "log") as mock_log:
                with patch("pathlib.Path.exists", return_value=True):
                    result = sync.process_camera("/src", "/dst", "test_cam")

            assert mock_process.call_count == 1
            mock_process.assert_called_once_with("/src", "/dst", "test_cam", "video")

            assert result["videos"]["new"] == 10
            assert result["images"]["total"] == 0
            assert result["images"]["new"] == 0

            mock_log.assert_any_call(
                "Skipping image sync (disabled) for camera test_cam"
            )

    def test_default_behavior_enables_images(self) -> None:
        """Test that default behavior is to enable image sync"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        assert sync.sync_images is True
