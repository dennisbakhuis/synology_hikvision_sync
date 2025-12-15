#!/usr/bin/env python3
"""
Tests for discover_cameras function
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import discover_cameras


class TestDiscoverCameras:
    """Test camera discovery functionality"""

    def test_discover_cameras_handles_camera_processing_exception(self) -> None:
        """Test discover_cameras handles exception during camera processing gracefully"""
        with patch("builtins.print") as mock_print:
            # Mock Path to raise exception during iteration
            with patch("pathlib.Path") as mock_path_class:
                mock_path_instance = mock_path_class.return_value
                mock_path_instance.exists.return_value = True
                mock_path_instance.iterdir.side_effect = Exception(
                    "Directory iteration error"
                )

                result = discover_cameras("/test/input", "/test/output")

                # Should return empty list and log error
                assert result == []
                mock_print.assert_called()

    def test_nonexistent_input_directory(self) -> None:
        """Test handling of non-existent input directory"""
        with patch("builtins.print") as mock_print:
            result = discover_cameras("/nonexistent", "/output")

            assert result == []
            mock_print.assert_any_call(
                "Warning: Input directory /nonexistent does not exist"
            )

    def test_empty_input_directory(self) -> None:
        """Test handling of empty input directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = discover_cameras(temp_dir, "/output")

            assert result == []

    def test_discover_single_camera(self) -> None:
        """Test discovering single camera directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a camera directory
            camera_dir = Path(temp_dir) / "Camera-Tuin"
            camera_dir.mkdir()

            result = discover_cameras(temp_dir, "/output")

            expected = [(camera_dir, Path("/output/Camera-Tuin"), "Camera-Tuin")]
            assert result == expected

    def test_discover_multiple_cameras(self) -> None:
        """Test discovering multiple camera directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple camera directories
            camera1 = Path(temp_dir) / "Camera-Tuin"
            camera2 = Path(temp_dir) / "Camera-Oprit"
            camera1.mkdir()
            camera2.mkdir()

            result = discover_cameras(temp_dir, "/output")

            # Should discover both cameras (order may vary)
            assert len(result) == 2
            camera_names = [cam[2] for cam in result]
            assert "Camera-Tuin" in camera_names
            assert "Camera-Oprit" in camera_names

            # Check that paths are Path objects
            for src_path, dst_path, _ in result:
                assert isinstance(src_path, Path)
                assert isinstance(dst_path, Path)

    def test_discover_with_translation_map(self) -> None:
        """Test discovering cameras with translation map"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create camera directory
            camera_dir = Path(temp_dir) / "Camera-Tuin"
            camera_dir.mkdir()

            translation_map = {"Camera-Tuin": "garden"}
            result = discover_cameras(temp_dir, "/output", translation_map)

            expected = [(camera_dir, Path("/output/garden"), "garden")]
            assert result == expected

    def test_discover_ignores_files(self) -> None:
        """Test that discovery ignores files and only processes directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file (should be ignored)
            test_file = Path(temp_dir) / "not_a_camera.txt"
            test_file.write_text("test")

            # Create a directory (should be discovered)
            camera_dir = Path(temp_dir) / "Camera-Tuin"
            camera_dir.mkdir()

            result = discover_cameras(temp_dir, "/output")

            # Should only find the directory, not the file
            assert len(result) == 1
            assert result[0][2] == "Camera-Tuin"
            assert isinstance(result[0][0], Path)  # source path is Path object
            assert isinstance(result[0][1], Path)  # destination path is Path object

    def test_discover_exception_handling(self) -> None:
        """Test that exceptions during discovery are handled gracefully"""
        with patch("builtins.print") as mock_print:
            with patch("pathlib.Path") as mock_path:
                mock_path.side_effect = Exception("Path error")

                result = discover_cameras("/test", "/output")

                assert result == []
                mock_print.assert_called()

    def test_discover_iterdir_exception_handling(self) -> None:
        """Test that exceptions during directory iteration are handled gracefully"""
        with patch("builtins.print") as mock_print:
            # Create a real temporary directory to pass the exists() check
            with tempfile.TemporaryDirectory() as temp_dir:
                # Patch the specific Path instance created within discover_cameras
                with patch("sync_hikvision_cameras.Path") as mock_path_class:
                    # Set up the mock to pass the initial exists check
                    mock_path_instance = mock_path_class.return_value
                    mock_path_instance.exists.return_value = True
                    # Make iterdir raise an exception after exists passes
                    mock_path_instance.iterdir.side_effect = PermissionError(
                        "Permission denied"
                    )

                    result = discover_cameras(temp_dir, "/output")

                    assert result == []
                    # Verify the error message was printed
                    mock_print.assert_called()
                    args, _ = mock_print.call_args
                    assert "Error discovering cameras" in args[0]
                    assert "Permission denied" in args[0]
