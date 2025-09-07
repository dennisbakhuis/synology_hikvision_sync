"""Tests for HikvisionSync initialization"""

import pytest
from src.process_hikvision_folder import HikvisionSync, DEFAULT_CAMERAS, DEFAULT_LOCK_FILE, DEFAULT_CACHE_DIR


def test_init_with_defaults():
    """Test HikvisionSync initialization with default parameters"""
    sync = HikvisionSync()
    
    assert sync.cameras == DEFAULT_CAMERAS
    assert sync.lock_file == DEFAULT_LOCK_FILE
    assert sync.cache_dir == DEFAULT_CACHE_DIR
    assert sync.lock_fd is None
    assert sync.hikvision_factory is not None
    assert sync.logger is not None


def test_init_with_custom_params(test_cameras, temp_dirs, test_logger):
    """Test HikvisionSync initialization with custom parameters"""
    custom_lock_file = temp_dirs['lock']
    custom_cache_dir = temp_dirs['cache']
    
    def mock_factory(src_path):
        return None
    
    sync = HikvisionSync(
        cameras=test_cameras,
        lock_file=custom_lock_file,
        cache_dir=custom_cache_dir,
        logger=test_logger,
        hikvision_factory=mock_factory
    )
    
    assert sync.cameras == test_cameras
    assert sync.lock_file == custom_lock_file
    assert sync.cache_dir == custom_cache_dir
    assert sync.logger == test_logger
    assert sync.hikvision_factory == mock_factory
    assert sync.lock_fd is None