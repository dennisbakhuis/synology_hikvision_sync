#!/usr/bin/env python3
"""
Tests for log_message function
"""

import pytest
import os
import sys
from unittest.mock import patch
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sync_hikvision_cameras import log_message


class TestLogMessage:
    """Test log message functionality"""
    
    @patch('sync_hikvision_cameras.datetime')
    @patch('builtins.print')
    def test_log_message_format(self, mock_print, mock_datetime):
        """Test log message formatting with timestamp"""
        # Mock datetime to return consistent timestamp
        mock_datetime.now.return_value.strftime.return_value = "2023-01-01 12:00:00"
        
        log_message("Test message")
        
        mock_print.assert_called_once_with("[2023-01-01 12:00:00] Test message")