"""Pytest configuration and shared fixtures"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, MagicMock

import pytest

from src.process_hikvision_folder import (
    HikvisionSync, 
    Logger, 
    HikvisionInterface,
    DEFAULT_CAMERAS
)


class TestLogger(Logger):
    """Test logger that captures log messages"""
    
    def __init__(self):
        self.messages: List[str] = []
    
    def log(self, message: str) -> None:
        self.messages.append(message)
    
    def clear(self):
        self.messages.clear()


class MockHikvisionInterface(HikvisionInterface):
    """Mock implementation of Hikvision interface for testing"""
    
    def __init__(self, src_path: str):
        self.src_path = src_path
        self.nas_info = {
            'serialNumber': b'TEST-CAMERA-12345\x00\x00\x00\x00\x00',
            'MACAddr': b'\x00\x01\x02\x03\x04\x05',
            'byRes': 208,
            'f_bsize': 4096,
            'f_blocks': 1000000,
            'DataDirs': 4
        }
        self.segments = []
        self.extraction_results = {}
        
    def get_nas_info(self) -> dict:
        return self.nas_info
    
    def get_segments(self) -> List[dict]:
        return self.segments
    
    def extract_segment_mp4(self, segment_num: int, cache_path: str, filename: str) -> Optional[str]:
        result = self.extraction_results.get(('mp4', segment_num), True)
        if result:
            # Create mock file
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(b'fake mp4 content for segment ' + str(segment_num).encode())
            return file_path
        return None
    
    def extract_segment_jpg(self, segment_num: int, cache_path: str, filename: str) -> Optional[str]:
        result = self.extraction_results.get(('jpg', segment_num), True)
        if result:
            # Create mock file
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(b'fake jpg content for segment ' + str(segment_num).encode())
            return file_path
        return None
    
    def add_segment(self, segment_num: int, start_time: datetime, duration: int = 30):
        """Add a mock segment"""
        self.segments.append({
            'cust_filePath': f'/mock/path/hiv{segment_num:05d}.mp4',
            'cust_duration': duration,
            'startOffset': segment_num * 1000,
            'endOffset': (segment_num + 1) * 1000,
            'cust_startTime': start_time,
            'cust_endTime': start_time
        })
    
    def set_extraction_result(self, file_type: str, segment_num: int, result: bool):
        """Set extraction result for testing failures"""
        self.extraction_results[(file_type, segment_num)] = result


@pytest.fixture
def test_logger():
    """Provide a test logger that captures messages"""
    return TestLogger()


@pytest.fixture
def mock_hikvision():
    """Provide a mock Hikvision interface"""
    return MockHikvisionInterface('/mock/path')


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing"""
    temp_dir = tempfile.mkdtemp()
    
    # Create source directories
    src_dir = Path(temp_dir) / 'src'
    src_dir.mkdir(parents=True)
    
    # Create destination directories
    dst_dir = Path(temp_dir) / 'dst'
    dst_dir.mkdir(parents=True)
    
    # Create cache directory
    cache_dir = Path(temp_dir) / 'cache'
    cache_dir.mkdir(parents=True)
    
    # Create lock directory
    lock_dir = Path(temp_dir) / 'lock'
    lock_dir.mkdir(parents=True)
    
    yield {
        'temp': temp_dir,
        'src': str(src_dir),
        'dst': str(dst_dir),
        'cache': str(cache_dir),
        'lock': str(lock_dir / 'test.lock')
    }
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_cameras(temp_dirs):
    """Provide test camera configuration"""
    return [
        (temp_dirs['src'] + '/Camera1', temp_dirs['dst'] + '/Camera1', 'test1'),
        (temp_dirs['src'] + '/Camera2', temp_dirs['dst'] + '/Camera2', 'test2'),
    ]


@pytest.fixture
def hikvision_sync(test_cameras, temp_dirs, test_logger, mock_hikvision):
    """Create a HikvisionSync instance for testing"""
    def mock_factory(src_path: str) -> HikvisionInterface:
        mock = MockHikvisionInterface(src_path)
        # Add some default test segments
        mock.add_segment(0, datetime(2024, 1, 1, 10, 0, 0))
        mock.add_segment(1, datetime(2024, 1, 1, 10, 1, 0))
        mock.add_segment(2, datetime(2024, 1, 1, 10, 2, 0))
        return mock
    
    return HikvisionSync(
        cameras=test_cameras,
        lock_file=temp_dirs['lock'],
        cache_dir=temp_dirs['cache'],
        logger=test_logger,
        hikvision_factory=mock_factory
    )


@pytest.fixture
def sample_segments():
    """Provide sample segment data for testing"""
    return [
        {
            'cust_filePath': '/mock/path/hiv00001.mp4',
            'cust_duration': 30,
            'startOffset': 1000,
            'endOffset': 2000,
            'cust_startTime': datetime(2024, 1, 1, 10, 0, 0),
            'cust_endTime': datetime(2024, 1, 1, 10, 0, 30)
        },
        {
            'cust_filePath': '/mock/path/hiv00002.mp4',
            'cust_duration': 45,
            'startOffset': 2000,
            'endOffset': 3000,
            'cust_startTime': datetime(2024, 1, 1, 10, 1, 0),
            'cust_endTime': datetime(2024, 1, 1, 10, 1, 45)
        },
        {
            'cust_filePath': '/mock/path/hiv00003.mp4',
            'cust_duration': 60,
            'startOffset': 3000,
            'endOffset': 4000,
            'cust_startTime': '2024-01-01 10:02:00',  # String format test
            'cust_endTime': '2024-01-01 10:03:00'
        },
        {
            'cust_filePath': '/mock/path/hiv00004.mp4',
            'cust_duration': 30,
            'startOffset': 4000,
            'endOffset': 5000,
            'cust_startTime': '2024-01-01T10:03:00Z',  # ISO format test
            'cust_endTime': '2024-01-01T10:03:30Z'
        },
        {
            'cust_filePath': '/mock/path/hiv00005.mp4',
            'cust_duration': 30,
            'startOffset': 5000,
            'endOffset': 6000,
            'cust_startTime': None,  # Missing time test
            'cust_endTime': None
        }
    ]