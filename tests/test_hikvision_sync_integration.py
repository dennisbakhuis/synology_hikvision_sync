#!/usr/bin/env python3
"""
Integration tests for HikvisionSync
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncIntegration:
    """Integration tests for HikvisionSync"""

    def test_full_workflow_integration(self) -> None:
        """Test complete workflow integration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cameras = [("src1", f"{temp_dir}/cam1", "cam1")]
            sync = HikvisionSync(cameras=cameras, retention_days=30)

            # Mock libHikvision
            with patch("sync_hikvision_cameras.libHikvision") as mock_lib:
                mock_instance = Mock()
                mock_instance.getSegments.return_value = []
                mock_lib.return_value = mock_instance

                # Mock file system operations
                with patch("pathlib.Path.exists", return_value=True):
                    with patch.object(sync, "acquire_lock", return_value=True):
                        with patch.object(sync, "release_lock"):
                            with patch.object(sync, "log"):
                                result = sync.run()

                                # Should complete successfully
                                assert result == 0

    def test_integration_with_file_creation(self) -> None:
        """Test integration that actually creates directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dst_path = str(Path(temp_dir) / "test_camera")
            cameras = [("src", dst_path, "test")]
            sync = HikvisionSync(cameras=cameras)

            # Create directories
            sync.create_directories()

            # Verify directories exist
            video_dir = Path(dst_path) / "video"
            images_dir = Path(dst_path) / "images"

            assert video_dir.exists() and video_dir.is_dir()
            assert images_dir.exists() and images_dir.is_dir()
