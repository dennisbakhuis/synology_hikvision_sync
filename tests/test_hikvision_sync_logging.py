#!/usr/bin/env python3
"""
Tests for HikvisionSync.log method
"""

import pytest
import os
import sys
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncLogging:
    """Test HikvisionSync logging functionality"""
    
    @patch('sync_hikvision_cameras.log_message')
    def test_log_method(self, mock_log_message):
        """Test the log method calls log_message"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        sync.log("Test message")
        mock_log_message.assert_called_once_with("Test message")