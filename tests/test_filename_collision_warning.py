import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from process_hikvision_folder import HikvisionSync


def test_get_unique_filename_many_collisions_warning():
    """Test that get_unique_filename logs warning after many collisions"""
    with tempfile.TemporaryDirectory() as temp_dir:
        sync = HikvisionSync()
        
        # Mock logger to capture log calls
        mock_logger = MagicMock()
        sync.logger = mock_logger
        
        # Mock Path.exists to return True for first 1000+ files
        def mock_exists(self):
            # Extract counter from filename
            filename = str(self)
            if '_' in filename and filename.count('_') >= 1:
                try:
                    counter_part = filename.split('_')[-1].split('.')[0]
                    counter = int(counter_part)
                    return counter <= 1000  # Return True for first 1000 files
                except:
                    return True
            return True
        
        with patch.object(Path, 'exists', mock_exists):
            result = sync.get_unique_filename(temp_dir, "2023-01-01_12-00-00", "test", "mp4")
            
        # Should log warning about too many collisions
        mock_logger.log.assert_called()
        log_calls = [call.args[0] for call in mock_logger.log.call_args_list]
        assert any("Too many filename collisions" in call for call in log_calls)