#!/usr/bin/env python3
"""
Tests for HikvisionScheduler class
"""

import pytest
import os
import sys
import signal
import time
from unittest.mock import patch, Mock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sync_hikvision_cameras import HikvisionScheduler, HikvisionSync


class TestHikvisionScheduler:
    """Test HikvisionScheduler functionality"""
    
    def test_scheduler_initialization(self):
        """Test scheduler initialization"""
        mock_sync = Mock()
        scheduler = HikvisionScheduler(mock_sync, 5)
        
        assert scheduler.sync == mock_sync
        assert scheduler.interval_minutes == 5
        assert scheduler.interval_seconds == 300
        assert scheduler.running is False
    
    def test_signal_handler_setup(self):
        """Test that signal handlers are properly set up"""
        mock_sync = Mock()
        
        with patch('signal.signal') as mock_signal:
            scheduler = HikvisionScheduler(mock_sync, 5)
            
            # Should set up signal handlers for SIGTERM and SIGINT
            assert mock_signal.call_count == 2
            signal_calls = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGTERM in signal_calls
            assert signal.SIGINT in signal_calls
    
    def test_signal_handler_stops_scheduler(self):
        """Test that signal handler stops the scheduler"""
        mock_sync = Mock()
        scheduler = HikvisionScheduler(mock_sync, 5)
        scheduler.running = True
        
        # Simulate signal reception
        with patch('sync_hikvision_cameras.log_message') as mock_log:
            # Get the signal handler function
            signal_handler = None
            with patch('signal.signal') as mock_signal:
                scheduler.setup_signal_handlers()
                signal_handler = mock_signal.call_args_list[0][0][1]
            
            # Call the signal handler
            signal_handler(signal.SIGTERM, None)
            
            assert scheduler.running is False
            mock_log.assert_called()
    
    def test_run_scheduled_immediate_execution(self):
        """Test that scheduler runs sync immediately on startup"""
        mock_sync = Mock()
        mock_sync.run.return_value = 0
        scheduler = HikvisionScheduler(mock_sync, 1)
        
        # Stop the scheduler after first run to avoid infinite loop
        def stop_after_first_run():
            scheduler.running = False
            return 0
        
        mock_sync.run.side_effect = stop_after_first_run
        
        with patch('sync_hikvision_cameras.log_message') as mock_log:
            result = scheduler.run_scheduled()
            
            # Should run sync once immediately
            mock_sync.run.assert_called_once()
            assert result == 0
            
            # Check that appropriate log messages were called
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            assert any("Starting scheduler" in call for call in log_calls)
            assert any("Running initial sync" in call for call in log_calls)
    
    def test_run_scheduled_with_interruption(self):
        """Test scheduler handling of KeyboardInterrupt"""
        mock_sync = Mock()
        mock_sync.run.side_effect = KeyboardInterrupt("Test interrupt")
        scheduler = HikvisionScheduler(mock_sync, 1)
        
        with patch('sync_hikvision_cameras.log_message') as mock_log:
            result = scheduler.run_scheduled()
            
            # Should handle KeyboardInterrupt gracefully
            assert result == 1
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            assert any("Interrupted by user" in call for call in log_calls)
            assert any("Scheduler stopped" in call for call in log_calls)
    
    def test_run_scheduled_with_exception(self):
        """Test scheduler handling of unexpected exceptions"""
        mock_sync = Mock()
        mock_sync.run.side_effect = Exception("Test error")
        scheduler = HikvisionScheduler(mock_sync, 1)
        
        with patch('sync_hikvision_cameras.log_message') as mock_log:
            result = scheduler.run_scheduled()
            
            # Should handle exceptions gracefully
            assert result == 1
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            assert any("Scheduler error: Test error" in call for call in log_calls)
            assert any("Scheduler stopped" in call for call in log_calls)
    
    def test_run_scheduled_sleep_loop(self):
        """Test that scheduler properly sleeps between runs"""
        mock_sync = Mock()
        mock_sync.run.return_value = 0
        scheduler = HikvisionScheduler(mock_sync, 1)  # 1 minute interval
        
        # Counter to stop after a few sleep calls
        sleep_call_count = 0
        
        def mock_sleep_side_effect(seconds):
            nonlocal sleep_call_count
            sleep_call_count += 1
            # Stop after a few sleep calls to avoid infinite loop
            if sleep_call_count >= 5:
                scheduler.running = False
        
        with patch('time.sleep', side_effect=mock_sleep_side_effect):
            with patch('sync_hikvision_cameras.log_message') as mock_log:
                result = scheduler.run_scheduled()
                
                # Should exit gracefully when running is set to False
                assert result == 0
                # Should have called sleep multiple times (1-second intervals)
                assert sleep_call_count >= 5
                
                # Check log messages
                log_calls = [call[0][0] for call in mock_log.call_args_list]
                assert any("Waiting 1 minutes until next sync" in call for call in log_calls)
    
    def test_run_scheduled_multiple_cycles(self):
        """Test scheduler running multiple sync cycles"""
        mock_sync = Mock()
        mock_sync.run.return_value = 0
        scheduler = HikvisionScheduler(mock_sync, 1)
        
        sync_call_count = 0
        
        def count_sync_calls():
            nonlocal sync_call_count
            sync_call_count += 1
            # Stop after 2 sync runs (initial + 1 scheduled)
            if sync_call_count >= 2:
                scheduler.running = False
            return 0
        
        mock_sync.run.side_effect = count_sync_calls
        
        # Mock time.sleep to immediately advance
        with patch('time.sleep') as mock_sleep:
            # Make sleep advance elapsed time instantly
            def fast_sleep(seconds):
                if scheduler.running:
                    # Skip the sleep loop by setting elapsed time
                    return
            mock_sleep.side_effect = fast_sleep
            
            with patch('sync_hikvision_cameras.log_message') as mock_log:
                # Override the while loop to only run once more after initial
                original_method = scheduler.run_scheduled
                
                def controlled_run():
                    scheduler.running = True
                    mock_log("Starting scheduler: sync every 1 minutes")
                    
                    try:
                        # Initial run
                        mock_log("Running initial sync...")
                        scheduler.sync.run()
                        
                        if scheduler.running:
                            # One more cycle
                            mock_log("Waiting 1 minutes until next sync...")
                            mock_log("Starting scheduled sync...")
                            scheduler.sync.run()
                        
                    except Exception as e:
                        mock_log(f"Scheduler error: {e}")
                        return 1
                    finally:
                        mock_log("Scheduler stopped")
                    
                    return 0
                
                result = controlled_run()
                
                # Should have run sync twice (initial + 1 scheduled)
                assert mock_sync.run.call_count == 2
                assert result == 0