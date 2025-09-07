import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from process_hikvision_folder import HikvisionSync


def test_release_lock_with_unlink_error():
    """Test release_lock handles OSError when unlinking lock file"""
    with tempfile.TemporaryDirectory() as temp_dir:
        lock_file = os.path.join(temp_dir, 'test.lock')
        sync = HikvisionSync(lock_file=lock_file)
        
        # Create a real temporary file to simulate lock - keep it open
        f = tempfile.NamedTemporaryFile(delete=False)
        sync.lock_fd = f
        temp_lock_path = f.name
        
        # Mock os.unlink to raise OSError
        with patch('os.unlink', side_effect=OSError("Permission denied")):
            # Should not raise exception
            sync.release_lock()
        
        # Clean up the temp file manually since unlink was mocked
        try:
            os.unlink(temp_lock_path)
        except:
            pass
        
        # Reset for cleanup
        sync.lock_fd = None