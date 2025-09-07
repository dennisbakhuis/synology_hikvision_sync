"""Tests for HikvisionSync lock acquisition functionality"""

import os
import fcntl
from unittest.mock import patch, mock_open

from src.process_hikvision_folder import HikvisionSync


def test_acquire_and_release_lock_success(temp_dirs):
    """Test successful lock acquisition and release"""
    sync = HikvisionSync(lock_file=temp_dirs['lock'])
    
    # Acquire lock
    result = sync.acquire_lock()
    assert result is True
    assert sync.lock_fd is not None
    
    # Release lock
    sync.release_lock()
    assert not os.path.exists(temp_dirs['lock'])


def test_acquire_lock_already_locked(temp_dirs):
    """Test lock acquisition when file is already locked"""
    sync1 = HikvisionSync(lock_file=temp_dirs['lock'])
    sync2 = HikvisionSync(lock_file=temp_dirs['lock'])
    
    # First instance acquires lock
    result1 = sync1.acquire_lock()
    assert result1 is True
    
    # Second instance fails to acquire lock
    result2 = sync2.acquire_lock()
    assert result2 is False
    
    # Clean up
    sync1.release_lock()