"""Tests for edge cases and error conditions"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.process_hikvision_folder import HikvisionSync


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_filename_collision_edge_cases(self, temp_dirs):
        """Test filename collision handling with edge cases"""
        sync = HikvisionSync()
        base_path = temp_dirs['dst']
        
        # Test collision limit (1000 files)
        # Create files up to the limit
        for i in range(5):  # Just test a few to avoid creating 1000 files
            if i == 0:
                existing_file = os.path.join(base_path, '2024-01-01_10-00-00-test.mp4')
            else:
                existing_file = os.path.join(base_path, f'2024-01-01_10-00-00-test_{i}.mp4')
            Path(existing_file).touch()
        
        filename = sync.get_unique_filename(
            base_path,
            '2024-01-01_10-00-00', 
            'test', 
            'mp4'
        )
        
        expected = os.path.join(base_path, '2024-01-01_10-00-00-test_5.mp4')
        assert filename == expected
    
    def test_timestamp_formatting_edge_cases(self, temp_dirs, test_logger):
        """Test timestamp formatting with various datetime formats"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        # Test various timestamp formats
        test_cases = [
            # Edge cases for datetime parsing
            datetime(1970, 1, 1, 0, 0, 0),  # Unix epoch
            datetime(2000, 1, 1, 0, 0, 0),  # Y2K
            datetime(2024, 12, 31, 23, 59, 59),  # End of year
            datetime(2024, 2, 29, 12, 0, 0),  # Leap year
            datetime(2024, 1, 1, 0, 0, 1),  # Beginning of year
        ]
        
        for i, test_time in enumerate(test_cases):
            mock_hik = Mock()
            mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
            mock_hik.get_segments.return_value = [
                {'cust_startTime': test_time, 'cust_filePath': f'/test/{i}.mp4'}
            ]
            
            def mock_extract_mp4(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'content {i}'.encode())
                return file_path
            
            def mock_extract_jpg(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'content {i}'.encode())
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
            
            # Clear previous test files
            for f in Path(dst_dir, 'video').glob('*.mp4'):
                f.unlink()
            for f in Path(dst_dir, 'images').glob('*.jpg'):
                f.unlink()
    
    def test_very_long_filenames(self, temp_dirs):
        """Test handling of very long camera tags and timestamps"""
        sync = HikvisionSync()
        
        # Test with very long camera tag
        long_cam_tag = 'a' * 100
        filename = sync.get_unique_filename(
            temp_dirs['dst'],
            '2024-01-01_10-00-00', 
            long_cam_tag, 
            'mp4'
        )
        
        # Should still work
        assert filename.endswith('.mp4')
        assert long_cam_tag in filename
    
    def test_special_characters_in_paths(self, temp_dirs):
        """Test handling of special characters in file paths"""
        sync = HikvisionSync()
        
        # Test with special characters (that are valid in filenames)
        special_cam_tag = 'test-camera_01'
        filename = sync.get_unique_filename(
            temp_dirs['dst'],
            '2024-01-01_10-00-00', 
            special_cam_tag, 
            'mp4'
        )
        
        assert special_cam_tag in filename
        assert filename.endswith('.mp4')
    
    def test_disk_space_exhaustion_simulation(self, temp_dirs, test_logger):
        """Test behavior when disk space is exhausted"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = [
            {'cust_startTime': datetime(2024, 1, 1, 10, 0, 0), 'cust_filePath': '/test/1.mp4'}
        ]
        mock_hik.extract_segment_mp4.return_value = '/fake/path.mp4'
        mock_hik.extract_segment_jpg.return_value = '/fake/path.jpg'
        
        def mock_factory(src_path):
            return mock_hik
        
        sync = HikvisionSync(
            logger=test_logger,
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        # Mock os.rename to raise OSError (simulating disk full)
        with patch('os.rename', side_effect=OSError("No space left on device")):
            sync.process_camera(src_dir, dst_dir, 'test')
        
        # Should handle the error gracefully
        # No files should be in destination
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 0
        assert len(image_files) == 0
    
    def test_permission_errors(self, temp_dirs, test_logger):
        """Test handling of permission errors"""
        # Create readonly directory to simulate permission issues
        readonly_dir = os.path.join(temp_dirs['dst'], 'readonly')
        os.makedirs(readonly_dir, exist_ok=True)
        
        cameras = [('/nonexistent', readonly_dir, 'test')]
        
        sync = HikvisionSync(
            cameras=cameras,
            logger=test_logger,
            cache_dir=temp_dirs['cache']
        )
        
        # Mock Path.mkdir to raise PermissionError
        with patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied")):
            result = sync.create_directories(cameras)
        
        assert result is False
        assert len(test_logger.messages) == 1
        assert "Failed to create directories" in test_logger.messages[0]
    
    def test_corrupted_nas_info(self, temp_dirs, test_logger):
        """Test handling of corrupted NAS info"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        mock_hik = Mock()
        mock_hik.get_nas_info.side_effect = Exception("Corrupted NAS data")
        
        def mock_factory(src_path):
            return mock_hik
        
        sync = HikvisionSync(
            logger=test_logger,
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        sync.process_camera(src_dir, dst_dir, 'test')
        
        # Should log the error
        log_messages = ' '.join(test_logger.messages)
        assert "Error processing camera test: Corrupted NAS data" in log_messages
    
    def test_malformed_segment_data(self, temp_dirs, test_logger):
        """Test handling of malformed segment data"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        
        # Test various malformed segment data
        malformed_segments = [
            {},  # Empty dict
            {'no_start_time': True},  # Missing cust_startTime
            {'cust_startTime': 'bad_format', 'cust_filePath': None},  # Bad format
            {'cust_startTime': [], 'cust_filePath': '/test.mp4'},  # Wrong type
            {'cust_startTime': {'nested': 'dict'}, 'cust_filePath': '/test.mp4'},  # Wrong type
        ]
        
        for malformed_data in malformed_segments:
            mock_hik.get_segments.return_value = [malformed_data]
            
            def mock_factory(src_path):
                return mock_hik
            
            sync = HikvisionSync(
                logger=test_logger,
                cache_dir=temp_dirs['cache'],
                hikvision_factory=mock_factory
            )
            
            sync.process_camera(src_dir, dst_dir, 'test')
            
            # Should handle gracefully without crashing
            # No files should be created for malformed data
            video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
            image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
            
            assert len(video_files) == 0
            assert len(image_files) == 0
    
    def test_cache_directory_creation_failure(self, temp_dirs, test_logger):
        """Test behavior when cache directory creation fails"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = [
            {'cust_startTime': datetime(2024, 1, 1, 10, 0, 0), 'cust_filePath': '/test/1.mp4'}
        ]
        mock_hik.extract_segment_mp4.return_value = '/fake/path.mp4'
        mock_hik.extract_segment_jpg.return_value = '/fake/path.jpg'
        
        def mock_factory(src_path):
            return mock_hik
        
        # Use invalid cache directory that cannot be created
        invalid_cache = '/invalid/cache/path'
        sync = HikvisionSync(
            logger=test_logger,
            cache_dir=invalid_cache,
            hikvision_factory=mock_factory
        )
        
        sync.process_camera(src_dir, dst_dir, 'test')
        
        # Should handle the error and log it
        log_messages = ' '.join(test_logger.messages)
        assert ("Extract video error" in log_messages or 
                "Extract image error" in log_messages)
    
    def test_zero_byte_files_in_cache(self, temp_dirs, test_logger):
        """Test handling of zero-byte files created in cache"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = [
            {'cust_startTime': datetime(2024, 1, 1, 10, 0, 0), 'cust_filePath': '/test/1.mp4'}
        ]
        
        def mock_extract_mp4_zero(segment_num, cache_path, filename):
            # Create zero-byte file
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            Path(file_path).touch()  # Creates empty file
            return file_path
        
        def mock_extract_jpg_zero(segment_num, cache_path, filename):
            # Create zero-byte file
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            Path(file_path).touch()  # Creates empty file
            return file_path
        
        mock_hik.extract_segment_mp4 = mock_extract_mp4_zero
        mock_hik.extract_segment_jpg = mock_extract_jpg_zero
        
        def mock_factory(src_path):
            return mock_hik
        
        sync = HikvisionSync(
            logger=test_logger,
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        sync.process_camera(src_dir, dst_dir, 'test')
        
        # Zero-byte files should be rejected
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 0
        assert len(image_files) == 0
        
        log_messages = ' '.join(test_logger.messages)
        assert "extraction succeeded but file not found" in log_messages
    
    def test_huge_number_of_segments(self, temp_dirs):
        """Test handling of very large number of segments"""
        src_dir = os.path.join(temp_dirs['src'], 'camera1')
        os.makedirs(src_dir, exist_ok=True)
        dst_dir = os.path.join(temp_dirs['dst'], 'camera1')
        os.makedirs(os.path.join(dst_dir, 'video'), exist_ok=True)
        os.makedirs(os.path.join(dst_dir, 'images'), exist_ok=True)
        
        # Create a large number of segments (but not too many for test performance)
        num_segments = 100
        segments = []
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        for i in range(num_segments):
            # Calculate minutes and hours correctly to avoid overflow
            total_minutes = base_time.minute + i
            hours = base_time.hour + (total_minutes // 60)
            minutes = total_minutes % 60
            segments.append({
                'cust_startTime': datetime(
                    base_time.year, 
                    base_time.month, 
                    base_time.day,
                    hours,
                    minutes,
                    base_time.second
                ),
                'cust_filePath': f'/test/{i}.mp4'
            })
        
        mock_hik = Mock()
        mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
        mock_hik.get_segments.return_value = segments
        
        def mock_extract_mp4(segment_num, cache_path, filename):
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(f'video {segment_num}'.encode())
            return file_path
        
        def mock_extract_jpg(segment_num, cache_path, filename):
            file_path = os.path.join(cache_path, filename)
            os.makedirs(cache_path, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(f'image {segment_num}'.encode())
            return file_path
        
        mock_hik.extract_segment_mp4 = mock_extract_mp4
        mock_hik.extract_segment_jpg = mock_extract_jpg
        
        def mock_factory(src_path):
            return mock_hik
        
        sync = HikvisionSync(
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        sync.process_camera(src_dir, dst_dir, 'test')
        
        # All segments should be processed
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == num_segments
        assert len(image_files) == num_segments