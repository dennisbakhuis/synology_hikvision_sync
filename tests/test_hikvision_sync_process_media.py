#!/usr/bin/env python3
"""
Tests for HikvisionSync._process_media method
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncProcessMedia:
    """Test HikvisionSync media processing"""
    
    def test_process_media_video_success(self):
        """Test successful video media processing"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        # Mock segment data
        mock_segments = [
            {'cust_startTime': datetime(2023, 1, 1, 12, 0, 0)},
            {'cust_startTime': datetime(2023, 1, 1, 12, 5, 0)},
        ]
        
        with patch('sync_hikvision_cameras.libHikvision') as mock_lib:
            mock_instance = Mock()
            mock_instance.getSegments.return_value = mock_segments
            mock_instance.extractSegmentMP4.return_value = True
            mock_lib.return_value = mock_instance
            
            with patch.object(sync, 'log') as mock_log:
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.getsize', return_value=1024):
                        with patch('pathlib.Path.mkdir'):
                            with patch('pathlib.Path.iterdir', return_value=[]):
                                result = sync._process_media("/src", "/dst", "test_cam", "video")
                                
                                expected = {'total': 2, 'existing': 0, 'new': 2, 'failed': 0}
                                assert result == expected
                                
                                # Verify libHikvision was called correctly
                                mock_lib.assert_called_once_with("/src/", "video")
                                assert mock_instance.extractSegmentMP4.call_count == 2
    
    def test_process_media_image_success(self):
        """Test successful image media processing"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        # Mock segment data
        mock_segments = [
            {'cust_startTime': datetime(2023, 1, 1, 12, 0, 0)},
        ]
        
        with patch('sync_hikvision_cameras.libHikvision') as mock_lib:
            mock_instance = Mock()
            mock_instance.getSegments.return_value = mock_segments
            mock_instance.extractSegmentJPG.return_value = True
            mock_lib.return_value = mock_instance
            
            with patch.object(sync, 'log') as mock_log:
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.getsize', return_value=1024):
                        with patch('pathlib.Path.mkdir'):
                            with patch('pathlib.Path.iterdir', return_value=[]):
                                result = sync._process_media("/src", "/dst", "test_cam", "image")
                                
                                expected = {'total': 1, 'existing': 0, 'new': 1, 'failed': 0}
                                assert result == expected
                                
                                # Verify libHikvision was called correctly for images
                                mock_lib.assert_called_once_with("/src/", "image")
                                mock_instance.extractSegmentJPG.assert_called_once()
    
    def test_process_media_existing_files_skipped(self):
        """Test that existing files are skipped"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        mock_segments = [
            {'cust_startTime': datetime(2023, 1, 1, 12, 0, 0)},
        ]
        
        with patch('sync_hikvision_cameras.libHikvision') as mock_lib:
            mock_instance = Mock()
            mock_instance.getSegments.return_value = mock_segments
            mock_lib.return_value = mock_instance
            
            with patch.object(sync, 'log') as mock_log:
                with patch('pathlib.Path.mkdir'):
                    # Mock that a file already exists with the same name
                    with patch('pathlib.Path.exists', return_value=True):
                        with patch('pathlib.Path.iterdir') as mock_iterdir:
                            # Mock existing file
                            mock_file = Mock()
                            mock_file.name = "2023-01-01_12-00-00-test_cam.mp4"
                            mock_file.is_file.return_value = True
                            mock_iterdir.return_value = [mock_file]
                            
                            result = sync._process_media("/src", "/dst", "test_cam", "video")
                            
                            expected = {'total': 1, 'existing': 1, 'new': 0, 'failed': 0}
                            assert result == expected
    
    def test_process_media_extraction_failure(self):
        """Test handling of extraction failures"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        mock_segments = [
            {'cust_startTime': datetime(2023, 1, 1, 12, 0, 0)},
        ]
        
        with patch('sync_hikvision_cameras.libHikvision') as mock_lib:
            mock_instance = Mock()
            mock_instance.getSegments.return_value = mock_segments
            mock_instance.extractSegmentMP4.return_value = False
            mock_lib.return_value = mock_instance
            
            with patch.object(sync, 'log') as mock_log:
                with patch('os.path.exists', return_value=False):
                    with patch('pathlib.Path.mkdir'):
                        with patch('pathlib.Path.iterdir', return_value=[]):
                            result = sync._process_media("/src", "/dst", "test_cam", "video")
                            
                            expected = {'total': 1, 'existing': 0, 'new': 0, 'failed': 1}
                            assert result == expected
    
    def test_process_media_missing_timestamp(self):
        """Test handling of segments with missing timestamps"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        mock_segments = [
            {'cust_startTime': None},  # Missing timestamp
            {'cust_startTime': datetime(2023, 1, 1, 12, 0, 0)},  # Valid timestamp
        ]
        
        with patch('sync_hikvision_cameras.libHikvision') as mock_lib:
            mock_instance = Mock()
            mock_instance.getSegments.return_value = mock_segments
            mock_instance.extractSegmentMP4.return_value = True
            mock_lib.return_value = mock_instance
            
            with patch.object(sync, 'log'):
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.getsize', return_value=1024):
                        with patch('pathlib.Path.mkdir'):
                            with patch('pathlib.Path.iterdir', return_value=[]):
                                result = sync._process_media("/src", "/dst", "test_cam", "video")
                                
                                # Should only process valid segment
                                expected = {'total': 2, 'existing': 0, 'new': 1, 'failed': 0}
                                assert result == expected
    
    def test_process_media_segment_exception(self):
        """Test handling of exceptions during segment processing"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        mock_segments = [
            {'cust_startTime': datetime(2023, 1, 1, 12, 0, 0)},
        ]
        
        with patch('sync_hikvision_cameras.libHikvision') as mock_lib:
            mock_instance = Mock()
            mock_instance.getSegments.return_value = mock_segments
            mock_instance.extractSegmentMP4.side_effect = Exception("Extraction error")
            mock_lib.return_value = mock_instance
            
            with patch.object(sync, 'log'):
                with patch('pathlib.Path.mkdir'):
                    with patch('pathlib.Path.iterdir', return_value=[]):
                        result = sync._process_media("/src", "/dst", "test_cam", "video")
                        
                        expected = {'total': 1, 'existing': 0, 'new': 0, 'failed': 1}
                        assert result == expected
    
    def test_process_media_library_exception(self):
        """Test handling of libHikvision library exceptions"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        with patch('sync_hikvision_cameras.libHikvision', side_effect=Exception("Library error")):
            with patch.object(sync, 'log') as mock_log:
                result = sync._process_media("/src", "/dst", "test_cam", "video")
                
                assert result == {'total': 0, 'existing': 0, 'new': 0, 'failed': 0}
                mock_log.assert_any_call("Error processing videos for camera test_cam: Library error")