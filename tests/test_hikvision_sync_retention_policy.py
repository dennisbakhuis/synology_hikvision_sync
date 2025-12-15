#!/usr/bin/env python3
"""
Tests for HikvisionSync.apply_retention_policy method
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncRetentionPolicy:
    """Test HikvisionSync retention policy functionality"""

    def test_retention_disabled(self) -> None:
        """Test retention policy when disabled (retention_days <= 0)"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")], retention_days=0
        )

        with patch.object(sync, "log") as mock_log:
            result = sync.apply_retention_policy()

            assert result == 0
            mock_log.assert_called_once_with(
                "Retention policy disabled (retention_days <= 0)"
            )

    def test_retention_no_cameras_exist(self) -> None:
        """Test retention when camera directories don't exist"""
        cameras = [("/src", "/nonexistent", "cam")]
        sync = HikvisionSync(cameras=cameras, retention_days=30)

        with patch.object(sync, "log") as mock_log:
            with patch("pathlib.Path.exists", return_value=False):
                result = sync.apply_retention_policy()

                assert result == 0
                # Should log start message and completion message
                assert mock_log.call_count == 2

    def test_retention_no_old_files(self) -> None:
        """Test retention when no files are old enough to delete"""
        cameras = [("/src", "/dst", "cam")]
        sync = HikvisionSync(cameras=cameras, retention_days=30)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure
            video_dir = Path(temp_dir) / "video"
            video_dir.mkdir(parents=True)

            # Create a new file (not old enough to delete)
            test_file = video_dir / "test.mp4"
            test_file.touch()

            with patch.object(sync, "log") as mock_log:
                with patch.object(sync, "cameras", [(None, temp_dir, "cam")]):
                    result = sync.apply_retention_policy()

                    assert result == 0
                    # Should log start and completion messages
                    assert mock_log.call_count == 2
                    assert (
                        "no files needed deletion" in mock_log.call_args_list[-1][0][0]
                    )

    def test_retention_deletes_old_files(self) -> None:
        """Test retention policy deleting old files"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")], retention_days=30
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure
            video_dir = Path(temp_dir) / "video"
            images_dir = Path(temp_dir) / "images"
            video_dir.mkdir(parents=True)
            images_dir.mkdir(parents=True)

            # Create test files
            old_video = video_dir / "old_video.mp4"
            old_image = images_dir / "old_image.jpg"
            old_video.write_text("test content video")
            old_image.write_text("test content image")

            # Set file times to be old
            old_time = datetime.now() - timedelta(days=35)
            old_timestamp = old_time.timestamp()
            os.utime(old_video, (old_timestamp, old_timestamp))
            os.utime(old_image, (old_timestamp, old_timestamp))

            with patch.object(sync, "log") as mock_log:
                with patch.object(sync, "cameras", [(None, temp_dir, "cam")]):
                    result = sync.apply_retention_policy()

                    assert result == 2  # Should delete 2 files

                    # Check log messages
                    log_calls = [call[0][0] for call in mock_log.call_args_list]
                    assert any("files deleted" in call for call in log_calls)

    def test_retention_mixed_file_ages(self) -> None:
        """Test retention with mix of old and new files"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")], retention_days=30
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            video_dir = Path(temp_dir) / "video"
            video_dir.mkdir(parents=True)

            # Create old file
            old_file = video_dir / "old.mp4"
            old_file.write_text("old content")
            old_time = datetime.now() - timedelta(days=35)
            os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))

            # Create new file
            new_file = video_dir / "new.mp4"
            new_file.write_text("new content")

            with patch.object(sync, "log"):
                with patch.object(sync, "cameras", [(None, temp_dir, "cam")]):
                    result = sync.apply_retention_policy()

                    assert result == 1  # Should delete only 1 file
                    assert not old_file.exists()
                    assert new_file.exists()

    def test_retention_file_deletion_error(self) -> None:
        """Test retention when file deletion fails"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")], retention_days=30
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            video_dir = Path(temp_dir) / "video"
            video_dir.mkdir(parents=True)

            # Create old file
            old_file = video_dir / "old.mp4"
            old_file.write_text("test")
            old_time = datetime.now() - timedelta(days=35)
            os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))

            with patch.object(sync, "log") as mock_log:
                with patch.object(sync, "cameras", [(None, temp_dir, "cam")]):
                    with patch(
                        "pathlib.Path.unlink", side_effect=Exception("Delete failed")
                    ):
                        result = sync.apply_retention_policy()

                        # Should handle error gracefully
                        assert result == 0
                        log_calls = [call[0][0] for call in mock_log.call_args_list]
                        assert any("Error deleting file" in call for call in log_calls)

    def test_retention_ignores_non_files(self) -> None:
        """Test retention policy ignores directories and other non-files"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")], retention_days=30
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            video_dir = Path(temp_dir) / "video"
            video_dir.mkdir(parents=True)

            # Create a subdirectory (not a file)
            subdir = video_dir / "subdir"
            subdir.mkdir()

            # Set directory time to be old (though this shouldn't matter)
            old_time = datetime.now() - timedelta(days=35)
            old_timestamp = old_time.timestamp()
            os.utime(subdir, (old_timestamp, old_timestamp))

            with patch.object(sync, "log") as mock_log:
                with patch.object(sync, "cameras", [(None, temp_dir, "cam")]):
                    result = sync.apply_retention_policy()

                    # Should not delete anything (subdirs are ignored)
                    assert result == 0
                    log_calls = [call[0][0] for call in mock_log.call_args_list]
                    assert any("no files needed deletion" in call for call in log_calls)


class TestRetentionPolicyExceptionHandling:
    """Test retention policy exception handling"""

    def test_retention_camera_processing_exception(self) -> None:
        """Test retention policy handles camera processing exceptions gracefully"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")], retention_days=30
        )

        # Create a camera that will cause an exception during processing
        sync.cameras = [("src", "dst", "test_cam")]

        with patch.object(sync, "log") as mock_log:
            # Mock the Path.iterdir to raise an exception during processing
            with patch("sync_hikvision_cameras.Path") as mock_path:
                # Set up the mock to raise an exception at specific line
                mock_instance = Mock()
                mock_instance.exists.return_value = True
                mock_instance.__truediv__ = Mock(
                    side_effect=Exception("Processing error")
                )
                mock_path.return_value = mock_instance

                result = sync.apply_retention_policy()

                # Should handle error gracefully and continue
                assert result == 0
                log_calls = [call[0][0] for call in mock_log.call_args_list]
                assert any(
                    "Error processing retention for camera test_cam: Processing error"
                    in call
                    for call in log_calls
                )
