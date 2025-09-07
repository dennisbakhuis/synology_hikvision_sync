"""Tests for extraction functionality"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.process_hikvision_folder import HikvisionSync


class TestExtraction:
    """Test extraction functionality without testing libhikvision"""
    
    def test_extraction_success(self, temp_dirs, test_logger):
        """Test successful video and image extraction"""
        # Setup directories
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        # Create mock Hikvision interface
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = [
            {
                'cust_startTime': datetime(2024, 1, 1, 10, 0, 0),
                'cust_filePath': '/test/path.mp4'
            }
        ]
        
        # Mock successful extraction
        def mock_extract_mp4(segment_num, cache_path, filename):
            # Create fake file
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(b'fake mp4 content')
            return file_path
        
        def mock_extract_jpg(segment_num, cache_path, filename):
            # Create fake file
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(b'fake jpg content')
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
        
        sync.process_camera(src_dir, dst_dir, 'test1')
        
        # Verify files were moved to destination
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 1
        assert len(image_files) == 1
        
        # Verify filename format
        video_file = video_files[0]
        assert video_file.name == '2024-01-01_10-00-00-test1.mp4'
        
        image_file = image_files[0]
        assert image_file.name == '2024-01-01_10-00-00-test1.jpg'
        
        # Verify content
        assert video_file.read_bytes() == b'fake mp4 content'
        assert image_file.read_bytes() == b'fake jpg content'
    
    def test_extraction_failure(self, temp_dirs, test_logger):
        """Test extraction failure handling"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        # Create mock Hikvision interface that fails extraction
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = [
            {
                'cust_startTime': datetime(2024, 1, 1, 10, 0, 0),
                'cust_filePath': '/test/path.mp4'
            }
        ]
        mock_hik.extract_segment_mp4.return_value = None
        mock_hik.extract_segment_jpg.return_value = None
        
        def mock_factory(src_path):
            return mock_hik
        
        sync = HikvisionSync(
            logger=test_logger,
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        sync.process_camera(src_dir, dst_dir, 'test1')
        
        # Verify no files were created
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 0
        assert len(image_files) == 0
        
        # Verify failure was logged
        log_messages = ' '.join(test_logger.messages)
        assert "Video extraction failed" in log_messages
        assert "Image extraction failed" in log_messages
    
    def test_extraction_file_created_but_empty(self, temp_dirs, test_logger):
        """Test extraction where file is created but empty"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        # Create mock that creates empty files
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = [
            {
                'cust_startTime': datetime(2024, 1, 1, 10, 0, 0),
                'cust_filePath': '/test/path.mp4'
            }
        ]
        
        def mock_extract_mp4_empty(segment_num, cache_path, filename):
            # Create empty file
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                pass  # Empty file
            return file_path
        
        def mock_extract_jpg_empty(segment_num, cache_path, filename):
            # Create empty file
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                pass  # Empty file
            return file_path
        
        mock_hik.extract_segment_mp4 = mock_extract_mp4_empty
        mock_hik.extract_segment_jpg = mock_extract_jpg_empty
        
        def mock_factory(src_path):
            return mock_hik
        
        sync = HikvisionSync(
            logger=test_logger,
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        sync.process_camera(src_dir, dst_dir, 'test1')
        
        # Verify no files were moved (empty files are rejected)
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 0
        assert len(image_files) == 0
        
        # Verify appropriate log messages
        log_messages = ' '.join(test_logger.messages)
        assert "extraction succeeded but file not found" in log_messages
    
    def test_extraction_file_not_created(self, temp_dirs, test_logger):
        """Test extraction where file is not created despite success return"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        # Create mock that returns success but doesn't create file
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = [
            {
                'cust_startTime': datetime(2024, 1, 1, 10, 0, 0),
                'cust_filePath': '/test/path.mp4'
            }
        ]
        mock_hik.extract_segment_mp4.return_value = "/fake/nonexistent.mp4"  # Says success but no file
        mock_hik.extract_segment_jpg.return_value = "/fake/nonexistent.jpg"  # Says success but no file
        
        def mock_factory(src_path):
            return mock_hik
        
        sync = HikvisionSync(
            logger=test_logger,
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        sync.process_camera(src_dir, dst_dir, 'test1')
        
        # Verify no files were moved
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 0
        assert len(image_files) == 0
        
        # Verify appropriate log messages
        log_messages = ' '.join(test_logger.messages)
        assert "extraction succeeded but file not found" in log_messages
    
    def test_extraction_exception_handling(self, temp_dirs, test_logger):
        """Test extraction with exceptions"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        # Create mock that raises exceptions
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = [
            {
                'cust_startTime': datetime(2024, 1, 1, 10, 0, 0),
                'cust_filePath': '/test/path.mp4'
            }
        ]
        mock_hik.extract_segment_mp4.side_effect = Exception("MP4 extraction error")
        mock_hik.extract_segment_jpg.side_effect = Exception("JPG extraction error")
        
        def mock_factory(src_path):
            return mock_hik
        
        sync = HikvisionSync(
            logger=test_logger,
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        sync.process_camera(src_dir, dst_dir, 'test1')
        
        # Verify no files were created
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 0
        assert len(image_files) == 0
        
        # Verify exceptions were logged
        log_messages = ' '.join(test_logger.messages)
        assert "Extract video error for segment 0: MP4 extraction error" in log_messages
        assert "Extract image error for segment 0: JPG extraction error" in log_messages
    
    def test_multiple_segments_extraction(self, temp_dirs, test_logger):
        """Test extraction of multiple segments"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        # Create mock with multiple segments
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = [
            {
                'cust_startTime': datetime(2024, 1, 1, 10, 0, 0),
                'cust_filePath': '/test/path1.mp4'
            },
            {
                'cust_startTime': datetime(2024, 1, 1, 10, 1, 0),
                'cust_filePath': '/test/path2.mp4'
            },
            {
                'cust_startTime': datetime(2024, 1, 1, 10, 2, 0),
                'cust_filePath': '/test/path3.mp4'
            }
        ]
        
        def mock_extract_mp4(segment_num, cache_path, filename):
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(f'fake mp4 content {segment_num}'.encode())
            return file_path
        
        def mock_extract_jpg(segment_num, cache_path, filename):
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(f'fake jpg content {segment_num}'.encode())
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
        
        sync.process_camera(src_dir, dst_dir, 'test1')
        
        # Verify all files were created
        video_files = sorted(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = sorted(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 3
        assert len(image_files) == 3
        
        # Verify filenames and content
        expected_video_names = [
            '2024-01-01_10-00-00-test1.mp4',
            '2024-01-01_10-01-00-test1.mp4',
            '2024-01-01_10-02-00-test1.mp4'
        ]
        expected_image_names = [
            '2024-01-01_10-00-00-test1.jpg',
            '2024-01-01_10-01-00-test1.jpg',
            '2024-01-01_10-02-00-test1.jpg'
        ]
        
        actual_video_names = [f.name for f in video_files]
        actual_image_names = [f.name for f in image_files]
        
        assert actual_video_names == expected_video_names
        assert actual_image_names == expected_image_names