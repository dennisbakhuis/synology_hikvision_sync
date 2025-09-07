"""Integration tests for the complete Hikvision sync workflow"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.process_hikvision_folder import HikvisionSync, ConsoleLogger


class TestIntegration:
    """Integration tests for complete workflow"""
    
    def test_full_workflow_success(self, temp_dirs):
        """Test complete workflow from start to finish"""
        # Setup camera directories
        cameras = []
        for i in range(3):
            src_dir = os.path.join(temp_dirs['src'], f'Camera{i}')
            dst_dir = os.path.join(temp_dirs['dst'], f'Camera{i}')
            os.makedirs(src_dir, exist_ok=True)
            cameras.append((src_dir, dst_dir, f'cam{i}'))
        
        # Create segments for different times
        segments_data = [
            [
                {'cust_startTime': datetime(2024, 1, 1, 10, 0, 0), 'cust_filePath': '/test/1.mp4'},
                {'cust_startTime': datetime(2024, 1, 1, 10, 1, 0), 'cust_filePath': '/test/2.mp4'},
            ],
            [
                {'cust_startTime': datetime(2024, 1, 1, 11, 0, 0), 'cust_filePath': '/test/3.mp4'},
            ],
            [
                {'cust_startTime': datetime(2024, 1, 1, 12, 0, 0), 'cust_filePath': '/test/4.mp4'},
                {'cust_startTime': datetime(2024, 1, 1, 12, 1, 0), 'cust_filePath': '/test/5.mp4'},
                {'cust_startTime': datetime(2024, 1, 1, 12, 2, 0), 'cust_filePath': '/test/6.mp4'},
            ]
        ]
        
        def mock_factory(src_path):
            # Determine which camera based on path
            camera_idx = int(src_path.split('Camera')[-1])
            
            mock_hik = Mock()
            mock_hik.get_nas_info.return_value = {
                'serialNumber': f'TEST-CAMERA-{camera_idx}'.encode() + b'\x00' * 10,
                'MACAddr': bytes([0, 1, 2, 3, 4, camera_idx]),
                'f_blocks': 1000000
            }
            mock_hik.get_segments.return_value = segments_data[camera_idx]
            
            def mock_extract_mp4(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'video content cam{camera_idx} seg{segment_num}'.encode())
                return file_path
            
            def mock_extract_jpg(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'image content cam{camera_idx} seg{segment_num}'.encode())
                return file_path
            
            mock_hik.extract_segment_mp4 = mock_extract_mp4
            mock_hik.extract_segment_jpg = mock_extract_jpg
            return mock_hik
        
        sync = HikvisionSync(
            cameras=cameras,
            lock_file=temp_dirs['lock'],
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        # Run the sync
        result = sync.run()
        
        assert result == 0
        
        # Verify all files were created
        total_videos = 0
        total_images = 0
        
        for i, (_, dst_dir, cam_tag) in enumerate(cameras):
            video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
            image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
            
            expected_count = len(segments_data[i])
            assert len(video_files) == expected_count, f"Camera {i} video count mismatch"
            assert len(image_files) == expected_count, f"Camera {i} image count mismatch"
            
            total_videos += len(video_files)
            total_images += len(image_files)
            
            # Verify file naming convention
            for video_file in video_files:
                assert cam_tag in video_file.name
                assert video_file.name.endswith('.mp4')
                assert len(video_file.read_bytes()) > 0
            
            for image_file in image_files:
                assert cam_tag in image_file.name
                assert image_file.name.endswith('.jpg')
                assert len(image_file.read_bytes()) > 0
        
        # Verify total counts
        assert total_videos == 6  # 2 + 1 + 3
        assert total_images == 6
    
    def test_workflow_with_mixed_failures(self, temp_dirs):
        """Test workflow where some extractions fail"""
        # Setup single camera
        src_dir = os.path.join(temp_dirs['src'], 'Camera1')
        dst_dir = os.path.join(temp_dirs['dst'], 'Camera1')
        os.makedirs(src_dir, exist_ok=True)
        cameras = [(src_dir, dst_dir, 'cam1')]
        
        def mock_factory(src_path):
            mock_hik = Mock()
            mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
            mock_hik.get_segments.return_value = [
                {'cust_startTime': datetime(2024, 1, 1, 10, 0, 0), 'cust_filePath': '/test/1.mp4'},
                {'cust_startTime': datetime(2024, 1, 1, 10, 1, 0), 'cust_filePath': '/test/2.mp4'},
                {'cust_startTime': datetime(2024, 1, 1, 10, 2, 0), 'cust_filePath': '/test/3.mp4'},
            ]
            
            def mock_extract_mp4(segment_num, cache_path, filename):
                if segment_num == 1:  # Fail second segment
                    return None
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'video content seg{segment_num}'.encode())
                return file_path
            
            def mock_extract_jpg(segment_num, cache_path, filename):
                if segment_num == 2:  # Fail third segment
                    return None
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'image content seg{segment_num}'.encode())
                return file_path
            
            mock_hik.extract_segment_mp4 = mock_extract_mp4
            mock_hik.extract_segment_jpg = mock_extract_jpg
            return mock_hik
        
        sync = HikvisionSync(
            cameras=cameras,
            lock_file=temp_dirs['lock'],
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        result = sync.run()
        
        assert result == 0  # Should still complete
        
        # Verify partial success
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 2  # 2 successful, 1 failed
        assert len(image_files) == 2  # 2 successful, 1 failed
    
    def test_workflow_with_empty_segments(self, temp_dirs):
        """Test workflow with no segments"""
        src_dir = os.path.join(temp_dirs['src'], 'Camera1')
        dst_dir = os.path.join(temp_dirs['dst'], 'Camera1')
        os.makedirs(src_dir, exist_ok=True)
        cameras = [(src_dir, dst_dir, 'cam1')]
        
        def mock_factory(src_path):
            mock_hik = Mock()
            mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
            mock_hik.get_segments.return_value = []  # No segments
            return mock_hik
        
        sync = HikvisionSync(
            cameras=cameras,
            lock_file=temp_dirs['lock'],
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        result = sync.run()
        
        assert result == 0
        
        # Verify no files created
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 0
        assert len(image_files) == 0
    
    def test_workflow_with_invalid_segments(self, temp_dirs):
        """Test workflow with invalid segment data"""
        src_dir = os.path.join(temp_dirs['src'], 'Camera1')
        dst_dir = os.path.join(temp_dirs['dst'], 'Camera1')
        os.makedirs(src_dir, exist_ok=True)
        cameras = [(src_dir, dst_dir, 'cam1')]
        
        def mock_factory(src_path):
            mock_hik = Mock()
            mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
            mock_hik.get_segments.return_value = [
                {'cust_startTime': None, 'cust_filePath': '/test/1.mp4'},  # Invalid time
                {'cust_startTime': 'invalid-date', 'cust_filePath': '/test/2.mp4'},  # Invalid format
                {'cust_startTime': datetime(2024, 1, 1, 10, 0, 0), 'cust_filePath': '/test/3.mp4'},  # Valid
            ]
            
            def mock_extract_mp4(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'video content seg{segment_num}'.encode())
                return file_path
            
            def mock_extract_jpg(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'image content seg{segment_num}'.encode())
                return file_path
            
            mock_hik.extract_segment_mp4 = mock_extract_mp4
            mock_hik.extract_segment_jpg = mock_extract_jpg
            return mock_hik
        
        sync = HikvisionSync(
            cameras=cameras,
            lock_file=temp_dirs['lock'],
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        result = sync.run()
        
        assert result == 0
        
        # Only the valid segment should create files
        video_files = list(Path(dst_dir, 'video').glob('*.mp4'))
        image_files = list(Path(dst_dir, 'images').glob('*.jpg'))
        
        assert len(video_files) == 1
        assert len(image_files) == 1
    
    def test_workflow_with_nonexistent_camera(self, temp_dirs):
        """Test workflow with nonexistent camera directory"""
        cameras = [
            ('/nonexistent/path', temp_dirs['dst'] + '/Camera1', 'cam1'),
            (temp_dirs['src'] + '/Camera2', temp_dirs['dst'] + '/Camera2', 'cam2')
        ]
        
        # Create the second camera
        os.makedirs(cameras[1][0], exist_ok=True)
        
        def mock_factory(src_path):
            mock_hik = Mock()
            mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
            mock_hik.get_segments.return_value = [
                {'cust_startTime': datetime(2024, 1, 1, 10, 0, 0), 'cust_filePath': '/test/1.mp4'},
            ]
            
            def mock_extract_mp4(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'video content seg{segment_num}'.encode())
                return file_path
            
            def mock_extract_jpg(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'image content seg{segment_num}'.encode())
                return file_path
            
            mock_hik.extract_segment_mp4 = mock_extract_mp4
            mock_hik.extract_segment_jpg = mock_extract_jpg
            return mock_hik
        
        sync = HikvisionSync(
            cameras=cameras,
            lock_file=temp_dirs['lock'],
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        result = sync.run()
        
        assert result == 0  # Should complete despite one failure
        
        # Only second camera should have files
        camera2_videos = list(Path(cameras[1][1], 'video').glob('*.mp4'))
        camera2_images = list(Path(cameras[1][1], 'images').glob('*.jpg'))
        
        assert len(camera2_videos) == 1
        assert len(camera2_images) == 1
    
    def test_workflow_concurrent_execution(self, temp_dirs):
        """Test that concurrent executions are prevented by locking"""
        src_dir = os.path.join(temp_dirs['src'], 'Camera1')
        dst_dir = os.path.join(temp_dirs['dst'], 'Camera1')
        os.makedirs(src_dir, exist_ok=True)
        cameras = [(src_dir, dst_dir, 'cam1')]
        
        def mock_factory(src_path):
            mock_hik = Mock()
            mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
            mock_hik.get_segments.return_value = []
            return mock_hik
        
        sync1 = HikvisionSync(
            cameras=cameras,
            lock_file=temp_dirs['lock'],
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        sync2 = HikvisionSync(
            cameras=cameras,
            lock_file=temp_dirs['lock'],
            cache_dir=temp_dirs['cache'],
            hikvision_factory=mock_factory
        )
        
        # First sync should succeed
        result1 = sync1.run()
        assert result1 == 0
        
        # Simulate concurrent execution by manually acquiring lock
        assert sync1.acquire_lock()
        
        # Second sync should fail due to lock
        result2 = sync2.run()
        assert result2 == 1
        
        # Release lock
        sync1.release_lock()
    
    def test_workflow_logging_integration(self, temp_dirs, capsys):
        """Test that logging works correctly throughout workflow"""
        src_dir = os.path.join(temp_dirs['src'], 'Camera1')
        dst_dir = os.path.join(temp_dirs['dst'], 'Camera1')
        os.makedirs(src_dir, exist_ok=True)
        cameras = [(src_dir, dst_dir, 'cam1')]
        
        def mock_factory(src_path):
            mock_hik = Mock()
            mock_hik.get_nas_info.return_value = {'serialNumber': b'TEST123'}
            mock_hik.get_segments.return_value = [
                {'cust_startTime': datetime(2024, 1, 1, 10, 0, 0), 'cust_filePath': '/test/1.mp4'},
            ]
            
            def mock_extract_mp4(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'video content seg{segment_num}'.encode())
                return file_path
            
            def mock_extract_jpg(segment_num, cache_path, filename):
                file_path = os.path.join(cache_path, filename)
                os.makedirs(cache_path, exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(f'image content seg{segment_num}'.encode())
                return file_path
            
            mock_hik.extract_segment_mp4 = mock_extract_mp4
            mock_hik.extract_segment_jpg = mock_extract_jpg
            return mock_hik
        
        with patch('src.process_hikvision_folder.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 15, 0, 0)
            mock_datetime.strftime = datetime.strftime
            
            sync = HikvisionSync(
                cameras=cameras,
                lock_file=temp_dirs['lock'],
                cache_dir=temp_dirs['cache'],
                logger=ConsoleLogger(),
                hikvision_factory=mock_factory
            )
            
            result = sync.run()
        
        assert result == 0
        
        captured = capsys.readouterr()
        output_lines = captured.out.strip().split('\n')
        
        # Verify expected log messages are present
        log_content = ' '.join(output_lines)
        assert "Starting multi-camera Hikvision sync for 1 camera(s)" in log_content
        assert "Created directories:" in log_content
        assert "Processing camera 'cam1'" in log_content
        assert "Camera NAS info:" in log_content
        assert "Found 1 segments for camera cam1" in log_content
        assert "Extracted video:" in log_content
        assert "Extracted image:" in log_content
        assert "Completed processing camera cam1: 1 segments processed" in log_content
        assert "Multi-camera Hikvision sync completed" in log_content