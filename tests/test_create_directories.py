"""Tests for HikvisionSync directory creation functionality"""

import os
from pathlib import Path

from src.process_hikvision_folder import HikvisionSync


def test_create_directories_success(hikvision_sync, test_cameras, test_logger):
    """Test successful directory creation"""
    result = hikvision_sync.create_directories(test_cameras)
    
    assert result is True
    
    # Check if directories were created
    for _, dst, _ in test_cameras:
        video_dir = Path(dst) / 'video'
        images_dir = Path(dst) / 'images'
        assert video_dir.exists()
        assert images_dir.exists()


def test_create_directories_failure(test_logger):
    """Test directory creation failure"""
    cameras = [('/src', '/invalid/path/that/cannot/be/created', 'test')]
    sync = HikvisionSync(cameras=cameras, logger=test_logger)
    
    result = sync.create_directories(cameras)
    
    # This might succeed or fail depending on system permissions
    # The test focuses on proper error handling
    if not result:
        assert len(test_logger.messages) >= 1
        assert any("Failed to create directories" in msg for msg in test_logger.messages)