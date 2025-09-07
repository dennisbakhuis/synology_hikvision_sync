import pytest
from unittest.mock import patch
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from process_hikvision_folder import parse_camera_translation


def test_parse_camera_translation_exception_handling(capsys):
    """Test exception handling in parse_camera_translation"""
    # Create a mock translation_env that will cause an exception during processing
    class BadString(str):
        def split(self, *args, **kwargs):
            raise Exception("Test exception")
    
    bad_env = BadString("Camera-Tuin:garden")
    result = parse_camera_translation(bad_env)
    
    # Should return empty dict when exception occurs
    assert result == {}
    
    # Should print warning message
    captured = capsys.readouterr()
    assert "Warning: Failed to parse camera translation" in captured.out
    assert "Test exception" in captured.out