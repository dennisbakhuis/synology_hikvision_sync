"""Tests for HikvisionSync segment parsing functionality"""

import os
from datetime import datetime
from unittest.mock import Mock
from pathlib import Path

from src.process_hikvision_folder import HikvisionSync


def test_parse_datetime_object(hikvision_sync, temp_dirs):
    """Test processing segment with datetime object"""
    # Create directories
    src_dir = os.path.join(temp_dirs['src'], 'camera1')
    os.makedirs(src_dir, exist_ok=True)
    dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
    os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
    os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
    
    # Mock Hikvision with datetime object
    mock_hik = Mock()
    mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
    mock_hik.get_segments.return_value = [
        {'cust_startTime': datetime(2024, 1, 1, 10, 0, 0)}
    ]
    mock_hik.extract_segment_mp4.return_value = None  # Don't create files
    mock_hik.extract_segment_jpg.return_value = None
    
    def mock_factory(src_path):
        return mock_hik
    
    hikvision_sync.hikvision_factory = mock_factory
    hikvision_sync.process_camera(src_dir, dst_dir, 'test')


def test_parse_string_datetime(hikvision_sync, temp_dirs):
    """Test processing segment with string datetime"""
    # Create directories
    src_dir = os.path.join(temp_dirs['src'], 'camera1')
    os.makedirs(src_dir, exist_ok=True)
    dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
    os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
    os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
    
    # Mock Hikvision with string datetime
    mock_hik = Mock()
    mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
    mock_hik.get_segments.return_value = [
        {'cust_startTime': '2024-01-01 10:00:00'}
    ]
    mock_hik.extract_segment_mp4.return_value = None  # Don't create files
    mock_hik.extract_segment_jpg.return_value = None
    
    def mock_factory(src_path):
        return mock_hik
    
    hikvision_sync.hikvision_factory = mock_factory
    hikvision_sync.process_camera(src_dir, dst_dir, 'test')


def test_parse_iso_datetime(hikvision_sync, temp_dirs):
    """Test processing segment with ISO datetime string"""
    # Create directories
    src_dir = os.path.join(temp_dirs['src'], 'camera1')
    os.makedirs(src_dir, exist_ok=True)
    dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
    os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
    os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
    
    # Mock Hikvision with ISO datetime string
    mock_hik = Mock()
    mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
    mock_hik.get_segments.return_value = [
        {'cust_startTime': '2024-01-01T10:00:00Z'}
    ]
    mock_hik.extract_segment_mp4.return_value = None  # Don't create files
    mock_hik.extract_segment_jpg.return_value = None
    
    def mock_factory(src_path):
        return mock_hik
    
    hikvision_sync.hikvision_factory = mock_factory
    hikvision_sync.process_camera(src_dir, dst_dir, 'test')


def test_parse_invalid_datetime(hikvision_sync, temp_dirs, test_logger):
    """Test processing segment with invalid datetime format"""
    # Create directories
    src_dir = os.path.join(temp_dirs['src'], 'camera1')
    os.makedirs(src_dir, exist_ok=True)
    dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
    os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
    os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
    
    # Mock Hikvision with invalid datetime
    mock_hik = Mock()
    mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
    mock_hik.get_segments.return_value = [
        {'cust_startTime': 'invalid-datetime-format'}
    ]
    mock_hik.extract_segment_mp4.return_value = None  # Don't create files
    mock_hik.extract_segment_jpg.return_value = None
    
    def mock_factory(src_path):
        return mock_hik
    
    sync = HikvisionSync(
        logger=test_logger,
        hikvision_factory=mock_factory
    )
    sync.process_camera(src_dir, dst_dir, 'test')
    
    # Should log parsing error
    log_messages = ' '.join(test_logger.messages)
    assert "Could not parse segment time" in log_messages


def test_parse_missing_datetime(hikvision_sync, temp_dirs):
    """Test processing segment with missing datetime"""
    # Create directories
    src_dir = os.path.join(temp_dirs['src'], 'camera1')
    os.makedirs(src_dir, exist_ok=True)
    dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
    os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
    os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
    
    # Mock Hikvision with missing datetime
    mock_hik = Mock()
    mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
    mock_hik.get_segments.return_value = [
        {'cust_filePath': '/test/segment.mp4'}  # Missing cust_startTime
    ]
    mock_hik.extract_segment_mp4.return_value = None  # Don't create files
    mock_hik.extract_segment_jpg.return_value = None
    
    def mock_factory(src_path):
        return mock_hik
    
    hikvision_sync.hikvision_factory = mock_factory
    hikvision_sync.process_camera(src_dir, dst_dir, 'test')
    
    # Should skip segment - no files should be created
    video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
    image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
    
    assert len(video_files) == 0
    assert len(image_files) == 0