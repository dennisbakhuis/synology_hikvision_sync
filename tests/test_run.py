"""Tests for HikvisionSync main run functionality"""

from unittest.mock import patch

from src.process_hikvision_folder import HikvisionSync


def test_run_success(hikvision_sync, test_logger):
    """Test successful run operation"""
    result = hikvision_sync.run()
    
    assert result == 0


def test_run_lock_acquisition_failure(hikvision_sync, test_logger):
    """Test run when lock acquisition fails"""
    with patch.object(hikvision_sync, 'acquire_lock', return_value=False):
        result = hikvision_sync.run()
    
    assert result == 1
    assert len(test_logger.messages) == 1
    assert "Another instance is already running" in test_logger.messages[0]


def test_run_keyboard_interrupt(hikvision_sync, test_logger):
    """Test run with keyboard interrupt"""
    with patch.object(hikvision_sync, 'create_directories', side_effect=KeyboardInterrupt):
        result = hikvision_sync.run()
    
    assert result == 1
    assert len(test_logger.messages) >= 1
    assert any("Interrupted by user" in msg for msg in test_logger.messages)


def test_run_unexpected_exception(hikvision_sync, test_logger):
    """Test run with unexpected exception"""
    with patch.object(hikvision_sync, 'create_directories', side_effect=Exception("Test error")):
        result = hikvision_sync.run()
    
    assert result == 1
    assert len(test_logger.messages) >= 1
    assert any("Unexpected error" in msg for msg in test_logger.messages)


def test_run_directory_creation_failure(hikvision_sync, test_logger):
    """Test run when directory creation fails"""
    with patch.object(hikvision_sync, 'create_directories', return_value=False):
        result = hikvision_sync.run()
    
    assert result == 1