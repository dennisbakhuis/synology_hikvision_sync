"""Tests for HikvisionSync logging functionality"""

from src.process_hikvision_folder import HikvisionSync


def test_log_message(test_logger):
    """Test log message functionality"""
    sync = HikvisionSync(logger=test_logger)
    
    sync.log("Test message")
    
    assert len(test_logger.messages) == 1
    assert test_logger.messages[0] == "Test message"