"""Tests for HikvisionSync camera processing functionality"""

import os
from datetime import datetime
from unittest.mock import Mock
from pathlib import Path

from src.process_hikvision_folder import HikvisionSync


def test_process_camera_nonexistent_source(hikvision_sync, test_logger):
    """Test processing camera with nonexistent source directory"""
    hikvision_sync.process_camera('/nonexistent', '/dst', 'test')
    
    assert len(test_logger.messages) == 2
    assert "Processing camera 'test':" in test_logger.messages[0]
    assert "Warning: Source directory does not exist" in test_logger.messages[1]


def test_process_camera_success(temp_dirs, test_logger):
    """Test successful camera processing"""
    # Create source directory
    src_dir = os.path.join(temp_dirs['src'], 'camera1')
    os.makedirs(src_dir, exist_ok=True)
    
    # Create destination directory structure
    dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
    os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
    os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
    
    # Mock Hikvision interface
    mock_hik = Mock()
    mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
    mock_hik.get_segments.return_value = [
        {
            'cust_startTime': datetime(2024, 1, 1, 10, 0, 0),
            'cust_filePath': '/test/segment1.mp4'
        }
    ]
    
    # Mock extraction functions to create test files
    def mock_extract_mp4(segment_num, cache_path, filename):
        file_path = os.path.join(cache_path, filename)
        os.makedirs(cache_path, exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(b'test video content')
        return file_path
    
    def mock_extract_jpg(segment_num, cache_path, filename):
        file_path = os.path.join(cache_path, filename)
        os.makedirs(cache_path, exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(b'test image content')
        return file_path
    
    mock_hik.extract_segment_mp4 = mock_extract_mp4
    mock_hik.extract_segment_jpg = mock_extract_jpg
    
    def mock_factory(src_path):
        return mock_hik
    
    sync = HikvisionSync(
        logger=test_logger,
        cache_dir=temp_dirs['cache'],
        hikvision_factory=mock_factory
    )
    
    sync.process_camera(src_dir, dst_dir, 'test')
    
    # Check if files were created
    video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
    image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
    
    assert len(video_files) == 1
    assert len(image_files) == 1
    
    # Check filename format
    video_file = video_files[0]
    assert 'test' in video_file.name
    assert '2024-01-01_10-00-00' in video_file.name
    
    image_file = image_files[0]
    assert 'test' in image_file.name
    assert '2024-01-01_10-00-00' in image_file.name