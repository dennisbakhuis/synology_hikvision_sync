#!/usr/bin/env python3
"""
Tests for new HikvisionSync parameters (video_sync_days, image_sync_days, etc.)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncNewParameters:
    """Test new parameters added to HikvisionSync"""

    def test_init_with_all_new_parameters(self) -> None:
        """Test initialization with all new parameters"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")],
            video_sync_days=14,
            image_sync_days=3,
            sync_images=False,
            extraction_timeout_seconds=120,
            use_fast_extraction=False,
        )

        assert sync.video_sync_days == 14
        assert sync.image_sync_days == 3
        assert sync.sync_images is False
        assert sync.extraction_timeout_seconds == 120
        assert sync.use_fast_extraction is False

    def test_init_with_defaults(self) -> None:
        """Test that defaults are applied when parameters not provided"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])

        assert sync.video_sync_days == 7
        assert sync.image_sync_days == 7
        assert sync.sync_images is True
        assert sync.extraction_timeout_seconds == 60
        assert sync.use_fast_extraction is True

    def test_init_with_none_uses_defaults(self) -> None:
        """Test that None values use defaults"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")],
            video_sync_days=None,
            image_sync_days=None,
            extraction_timeout_seconds=None,
        )

        assert sync.video_sync_days == 7
        assert sync.image_sync_days == 7
        assert sync.extraction_timeout_seconds == 60

    def test_init_with_zero_values(self) -> None:
        """Test that zero values are accepted (disable features)"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")],
            video_sync_days=0,
            image_sync_days=0,
            extraction_timeout_seconds=0,
        )

        assert sync.video_sync_days == 0
        assert sync.image_sync_days == 0
        assert sync.extraction_timeout_seconds == 0

    def test_init_backward_compatibility(self) -> None:
        """Test that old code without new parameters still works"""
        sync = HikvisionSync(
            cameras=[("/test/src", "/test/dst", "test_cam")],
            lock_file="/tmp/test.lock",
            cache_directory="/tmp/cache",
            retention_days=90,
        )

        assert sync.retention_days == 90
        assert sync.video_sync_days == 7
        assert sync.image_sync_days == 7
        assert sync.sync_images is True
