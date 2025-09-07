"""Tests for HikvisionSync atomic write functionality"""

import os
from unittest.mock import Mock

from src.process_hikvision_folder import HikvisionSync


def test_atomic_write_success(temp_dirs):
    """Test successful atomic write operation"""
    sync = HikvisionSync()
    dest_path = os.path.join(temp_dirs['dst'], 'test.mp4')
    
    def content_func(temp_path):
        with open(temp_path, 'w') as f:
            f.write('test content')
        return True
    
    result = sync.atomic_write(content_func, dest_path)
    
    assert result is True
    assert os.path.exists(dest_path)
    with open(dest_path, 'r') as f:
        assert f.read() == 'test content'


def test_atomic_write_content_func_failure(temp_dirs, test_logger):
    """Test atomic write when content function fails"""
    sync = HikvisionSync(logger=test_logger)
    dest_path = os.path.join(temp_dirs['dst'], 'test.mp4')
    
    def failing_content_func(temp_path):
        return False
    
    result = sync.atomic_write(failing_content_func, dest_path)
    
    assert result is False
    assert not os.path.exists(dest_path)


def test_atomic_write_exception(temp_dirs, test_logger):
    """Test atomic write when exception occurs"""
    sync = HikvisionSync(logger=test_logger)
    dest_path = os.path.join(temp_dirs['dst'], 'test.mp4')
    
    def exception_content_func(temp_path):
        raise Exception("Test exception")
    
    result = sync.atomic_write(exception_content_func, dest_path)
    
    assert result is False
    assert not os.path.exists(dest_path)
    assert len(test_logger.messages) == 1
    assert "Atomic write failed" in test_logger.messages[0]