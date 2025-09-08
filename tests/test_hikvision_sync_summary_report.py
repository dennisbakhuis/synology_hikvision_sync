#!/usr/bin/env python3
"""
Tests for HikvisionSync._generate_summary_report method
"""

import pytest
import os
import sys
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sync_hikvision_cameras import HikvisionSync


class TestHikvisionSyncSummaryReport:
    """Test HikvisionSync summary report generation"""
    
    def test_generate_summary_report_single_camera(self):
        """Test summary report generation for single camera"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        camera_stats = {
            'test_cam': {
                'videos': {'total': 10, 'existing': 3, 'new': 5, 'failed': 2},
                'images': {'total': 8, 'existing': 2, 'new': 4, 'failed': 2}
            }
        }
        
        with patch.object(sync, 'log') as mock_log:
            sync._generate_summary_report(camera_stats, 0)
            
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            
            # Check key elements are logged
            assert any("SYNC SUMMARY REPORT" in call for call in log_calls)
            assert any("test_cam: Videos 5/10, Images 4/8" in call for call in log_calls)
            assert any("Total: 9 new, 5 existing, 18 segments" in call for call in log_calls)
            assert any("Efficiency: 27.8% skipped" in call for call in log_calls)
    
    def test_generate_summary_report_multiple_cameras(self):
        """Test summary report generation for multiple cameras"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        camera_stats = {
            'cam1': {
                'videos': {'total': 5, 'existing': 1, 'new': 3, 'failed': 1},
                'images': {'total': 4, 'existing': 1, 'new': 2, 'failed': 1}
            },
            'cam2': {
                'videos': {'total': 6, 'existing': 2, 'new': 3, 'failed': 1},
                'images': {'total': 5, 'existing': 1, 'new': 3, 'failed': 1}
            }
        }
        
        with patch.object(sync, 'log') as mock_log:
            sync._generate_summary_report(camera_stats, 5)
            
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            
            # Check aggregated totals
            assert any("Total: 11 new, 5 existing, 20 segments" in call for call in log_calls)
            assert any("Retention: 5 old files deleted" in call for call in log_calls)
    
    def test_generate_summary_report_no_segments(self):
        """Test summary report with no segments processed"""
        sync = HikvisionSync(cameras=[("/test/src", "/test/dst", "test_cam")])
        
        camera_stats = {
            'cam1': {
                'videos': {'total': 0, 'existing': 0, 'new': 0, 'failed': 0},
                'images': {'total': 0, 'existing': 0, 'new': 0, 'failed': 0}
            }
        }
        
        with patch.object(sync, 'log') as mock_log:
            sync._generate_summary_report(camera_stats, 0)
            
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            
            # Should not calculate efficiency for 0 segments
            assert any("Total: 0 new, 0 existing, 0 segments" in call for call in log_calls)
            assert not any("Efficiency:" in call for call in log_calls)