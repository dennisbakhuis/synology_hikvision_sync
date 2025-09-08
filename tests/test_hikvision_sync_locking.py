#!/usr/bin/env python3
"""
Tests for HikvisionSync locking methods (acquire_lock, release_lock)
"""

import pytest
import os
import sys
import tempfile
from unittest.mock import patch, mock_open, Mock
import fcntl

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncLocking:
    """Test HikvisionSync file locking functionality"""
    
    def test_acquire_lock_success(self):
        """Test successful lock acquisition"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('fcntl.flock') as mock_flock:
                with patch('os.getpid', return_value=12345):
                    result = sync.acquire_lock()
                    
                    assert result is True
                    assert sync.lock_file_descriptor is not None
                    mock_file.assert_called_once_with(sync.lock_file, 'w')
                    mock_flock.assert_called_once_with(sync.lock_file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    
    def test_acquire_lock_failure_flock_exception(self):
        """Test lock acquisition failure due to flock exception"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('fcntl.flock', side_effect=OSError("Lock failed")):
                result = sync.acquire_lock()
                
                assert result is False
                # File descriptor should be closed on failure
                sync.lock_file_descriptor.close.assert_called_once()
    
    def test_acquire_lock_failure_file_exception(self):
        """Test lock acquisition failure due to file open exception"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        with patch('builtins.open', side_effect=IOError("File error")):
            result = sync.acquire_lock()
            
            assert result is False
    
    def test_release_lock_success(self):
        """Test successful lock release"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        # Set up a mock file descriptor
        mock_fd = Mock()
        sync.lock_file_descriptor = mock_fd
        
        with patch('fcntl.flock') as mock_flock:
            with patch('os.unlink') as mock_unlink:
                sync.release_lock()
                
                mock_flock.assert_called_once_with(mock_fd, fcntl.LOCK_UN)
                mock_fd.close.assert_called_once()
                mock_unlink.assert_called_once_with(sync.lock_file)
    
    def test_release_lock_unlink_failure(self):
        """Test lock release when unlink fails"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        # Set up a mock file descriptor
        mock_fd = Mock()
        sync.lock_file_descriptor = mock_fd
        
        with patch('fcntl.flock') as mock_flock:
            with patch('os.unlink', side_effect=OSError("Unlink failed")):
                # Should not raise exception despite unlink failure
                sync.release_lock()
                
                mock_flock.assert_called_once_with(mock_fd, fcntl.LOCK_UN)
                mock_fd.close.assert_called_once()
    
    def test_release_lock_no_descriptor(self):
        """Test release lock when no file descriptor exists"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        # This should not raise an exception
        sync.release_lock()