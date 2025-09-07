"""Tests for HikvisionSync unique filename generation"""

import os
from pathlib import Path

from src.process_hikvision_folder import HikvisionSync


def test_get_unique_filename_no_collision(temp_dirs):
    """Test unique filename generation without collision"""
    sync = HikvisionSync()
    
    filename = sync.get_unique_filename(
        base_path=temp_dirs['dst'],
        timestamp='2024-01-01_10-00-00',
        cam_tag='test',
        ext='mp4'
    )
    
    expected = os.path.join(temp_dirs['dst'], '2024-01-01_10-00-00-test.mp4')
    assert filename == expected


def test_get_unique_filename_with_collision(temp_dirs):
    """Test unique filename generation with collision"""
    sync = HikvisionSync()
    
    # Create existing file
    existing_file = os.path.join(temp_dirs['dst'], '2024-01-01_10-00-00-test.mp4')
    Path(existing_file).touch()
    
    filename = sync.get_unique_filename(
        base_path=temp_dirs['dst'],
        timestamp='2024-01-01_10-00-00',
        cam_tag='test',
        ext='mp4'
    )
    
    expected = os.path.join(temp_dirs['dst'], '2024-01-01_10-00-00-test_1.mp4')
    assert filename == expected


def test_get_unique_filename_many_collisions(temp_dirs, test_logger):
    """Test unique filename generation with many collisions"""
    sync = HikvisionSync(logger=test_logger)
    
    # Create multiple existing files
    for i in range(5):
        if i == 0:
            existing_file = os.path.join(temp_dirs['dst'], '2024-01-01_10-00-00-test.mp4')
        else:
            existing_file = os.path.join(temp_dirs['dst'], f'2024-01-01_10-00-00-test_{i}.mp4')
        Path(existing_file).touch()
    
    filename = sync.get_unique_filename(
        base_path=temp_dirs['dst'],
        timestamp='2024-01-01_10-00-00',
        cam_tag='test',
        ext='mp4'
    )
    
    expected = os.path.join(temp_dirs['dst'], '2024-01-01_10-00-00-test_5.mp4')
    assert filename == expected