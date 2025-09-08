#!/usr/bin/env python3
"""
Tests for HikvisionSync.create_directories method
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncDirectories:
    """Test HikvisionSync directory creation functionality"""
    
    def test_create_directories_single_camera(self):
        """Test directory creation for single camera"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dst_path = str(Path(temp_dir) / "test_camera")
            sync = HikvisionSync(cameras=[("src", dst_path, "test")])
            
            sync.create_directories()
            
            # Check that video and images directories were created
            video_dir = Path(dst_path) / "video"
            images_dir = Path(dst_path) / "images"
            
            assert video_dir.exists() and video_dir.is_dir()
            assert images_dir.exists() and images_dir.is_dir()
    
    def test_create_directories_multiple_cameras(self):
        """Test directory creation for multiple cameras"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dst_path1 = str(Path(temp_dir) / "camera1")
            dst_path2 = str(Path(temp_dir) / "camera2")
            
            sync = HikvisionSync(cameras=[
                ("src1", dst_path1, "cam1"),
                ("src2", dst_path2, "cam2")
            ])
            
            sync.create_directories()
            
            # Check both camera directories were created
            for dst_path in [dst_path1, dst_path2]:
                video_dir = Path(dst_path) / "video"
                images_dir = Path(dst_path) / "images"
                
                assert video_dir.exists() and video_dir.is_dir()
                assert images_dir.exists() and images_dir.is_dir()
    
    def test_create_directories_existing_dirs(self):
        """Test that existing directories are not affected"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dst_path = str(Path(temp_dir) / "test_camera")
            
            # Pre-create directories
            video_dir = Path(dst_path) / "video"
            images_dir = Path(dst_path) / "images"
            video_dir.mkdir(parents=True)
            images_dir.mkdir(parents=True)
            
            sync = HikvisionSync(cameras=[("src", dst_path, "test")])
            
            # This should not raise an exception
            sync.create_directories()
            
            # Directories should still exist
            assert video_dir.exists() and video_dir.is_dir()
            assert images_dir.exists() and images_dir.is_dir()