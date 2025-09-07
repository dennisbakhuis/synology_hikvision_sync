"""Tests for logger implementations"""

import pytest
from datetime import datetime
from unittest.mock import patch

from src.process_hikvision_folder import ConsoleLogger


class TestConsoleLogger:
    """Test cases for ConsoleLogger"""
    
    def test_console_logger_output(self, capsys):
        """Test that ConsoleLogger outputs to stdout with timestamp"""
        logger = ConsoleLogger()
        
        with patch('src.process_hikvision_folder.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.strftime = datetime.strftime
            
            logger.log("Test message")
        
        captured = capsys.readouterr()
        assert captured.out == "[2024-01-01 10:00:00] Test message\n"
    
    def test_console_logger_multiple_messages(self, capsys):
        """Test multiple log messages"""
        logger = ConsoleLogger()
        
        with patch('src.process_hikvision_folder.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.strftime = datetime.strftime
            
            logger.log("Message 1")
            logger.log("Message 2")
        
        captured = capsys.readouterr()
        lines = captured.out.split('\n')
        assert "[2024-01-01 10:00:00] Message 1" in lines
        assert "[2024-01-01 10:00:00] Message 2" in lines
    
    def test_console_logger_empty_message(self, capsys):
        """Test logging empty message"""
        logger = ConsoleLogger()
        
        with patch('src.process_hikvision_folder.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.strftime = datetime.strftime
            
            logger.log("")
        
        captured = capsys.readouterr()
        assert captured.out == "[2024-01-01 10:00:00] \n"
    
    def test_console_logger_special_characters(self, capsys):
        """Test logging message with special characters"""
        logger = ConsoleLogger()
        
        with patch('src.process_hikvision_folder.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.strftime = datetime.strftime
            
            logger.log("Test with 🎥 emoji and special chars: àáâã")
        
        captured = capsys.readouterr()
        assert "[2024-01-01 10:00:00] Test with 🎥 emoji and special chars: àáâã\n" in captured.out