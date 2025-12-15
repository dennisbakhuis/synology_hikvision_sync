#!/usr/bin/env python3
"""
Tests for HikvisionSync.__init__ method
"""

import pytest
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import (
    HikvisionSync,
    DEFAULT_LOCK_FILE,
    DEFAULT_CACHE_DIR,
    DEFAULT_RETENTION_DAYS,
)


class TestHikvisionSyncInit:
    """Test HikvisionSync initialization"""

    def test_default_initialization(self) -> None:
        """Test that HikvisionSync requires explicit camera configuration"""
        # Should raise ValueError when no cameras provided
        with pytest.raises(ValueError, match="No cameras provided"):
            _ = HikvisionSync()

    def test_initialization_with_cameras(self) -> None:
        """Test initialization with explicit camera configuration"""
        test_cameras: list[tuple[str, str, str]] = [("/src", "/dst", "cam1")]
        sync = HikvisionSync(cameras=test_cameras)

        assert sync.cameras == test_cameras
        assert sync.lock_file == DEFAULT_LOCK_FILE
        assert sync.cache_directory == DEFAULT_CACHE_DIR
        assert sync.retention_days == DEFAULT_RETENTION_DAYS
        assert sync.lock_file_descriptor is None

    def test_custom_initialization(self) -> None:
        """Test custom initialization of HikvisionSync"""
        custom_cameras = [("src1", "dst1", "cam1")]
        custom_lock = "/tmp/custom.lock"
        custom_cache = "/tmp/custom_cache"
        custom_retention = 60

        sync = HikvisionSync(
            cameras=custom_cameras,
            lock_file=custom_lock,
            cache_directory=custom_cache,
            retention_days=custom_retention,
        )

        assert sync.cameras == custom_cameras
        assert sync.lock_file == custom_lock
        assert sync.cache_directory == custom_cache
        assert sync.retention_days == custom_retention
        assert sync.lock_file_descriptor is None
