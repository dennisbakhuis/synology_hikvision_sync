"""Tests for camera discovery and translation functionality"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.process_hikvision_folder import parse_camera_translation, discover_cameras


def test_parse_camera_translation_empty():
    """Test parsing empty translation string"""
    result = parse_camera_translation("")
    assert result == {}


def test_parse_camera_translation_single():
    """Test parsing single camera translation"""
    result = parse_camera_translation("Camera-Tuin:garden")
    assert result == {"Camera-Tuin": "garden"}


def test_parse_camera_translation_multiple():
    """Test parsing multiple camera translations"""
    result = parse_camera_translation("Camera-Tuin:garden,Camera-Oprit:driveway,Door-Cam:entrance")
    expected = {
        "Camera-Tuin": "garden",
        "Camera-Oprit": "driveway", 
        "Door-Cam": "entrance"
    }
    assert result == expected


def test_parse_camera_translation_whitespace():
    """Test parsing with extra whitespace"""
    result = parse_camera_translation(" Camera-Tuin : garden , Camera-Oprit : driveway ")
    expected = {
        "Camera-Tuin": "garden",
        "Camera-Oprit": "driveway"
    }
    assert result == expected


def test_parse_camera_translation_invalid_format():
    """Test parsing invalid format (no colon)"""
    with patch('builtins.print') as mock_print:
        result = parse_camera_translation("Camera-Tuin-garden,Camera-Oprit:driveway")
        # Should skip invalid entry and continue with valid ones
        assert result == {"Camera-Oprit": "driveway"}


def test_discover_cameras_nonexistent_input():
    """Test camera discovery with nonexistent input directory"""
    with patch('builtins.print') as mock_print:
        result = discover_cameras("/nonexistent/path", "/output")
        assert result == []
        mock_print.assert_called_with("Warning: Input directory /nonexistent/path does not exist")


def test_discover_cameras_empty_directory(temp_dirs):
    """Test camera discovery with empty input directory"""
    input_dir = temp_dirs['src']  # Empty directory from fixture
    
    with patch('builtins.print') as mock_print:
        result = discover_cameras(input_dir, temp_dirs['dst'])
        assert result == []
        mock_print.assert_called_with("Discovered 0 camera(s): []")


def test_discover_cameras_with_cameras(temp_dirs):
    """Test camera discovery with actual camera directories"""
    input_dir = temp_dirs['src']
    output_dir = temp_dirs['dst']
    
    # Create mock camera directories
    camera_dirs = ['Camera-Tuin', 'Camera-Oprit', 'Door-Cam']
    for cam_name in camera_dirs:
        os.makedirs(os.path.join(input_dir, cam_name))
    
    # Also create a file (should be ignored)
    Path(input_dir, 'some_file.txt').touch()
    
    with patch('builtins.print') as mock_print:
        result = discover_cameras(input_dir, output_dir)
        
        expected = [
            (os.path.join(input_dir, 'Camera-Tuin'), os.path.join(output_dir, 'Camera-Tuin'), 'Camera-Tuin'),
            (os.path.join(input_dir, 'Camera-Oprit'), os.path.join(output_dir, 'Camera-Oprit'), 'Camera-Oprit'),
            (os.path.join(input_dir, 'Door-Cam'), os.path.join(output_dir, 'Door-Cam'), 'Door-Cam'),
        ]
        
        # Sort both lists to handle directory iteration order differences
        result_sorted = sorted(result)
        expected_sorted = sorted(expected)
        
        assert result_sorted == expected_sorted
        # Check that the print was called with discovered cameras (order may vary)
        assert mock_print.call_count == 1
        call_args = mock_print.call_args[0][0]
        assert "Discovered 3 camera(s):" in call_args
        for cam in ['Camera-Tuin', 'Camera-Oprit', 'Door-Cam']:
            assert cam in call_args


def test_discover_cameras_with_translation(temp_dirs):
    """Test camera discovery with translation mapping"""
    input_dir = temp_dirs['src']
    output_dir = temp_dirs['dst']
    
    # Create mock camera directories
    os.makedirs(os.path.join(input_dir, 'Camera-Tuin'))
    os.makedirs(os.path.join(input_dir, 'Camera-Oprit'))
    
    translation_map = {
        'Camera-Tuin': 'garden',
        'Camera-Oprit': 'driveway'
    }
    
    with patch('builtins.print'):
        result = discover_cameras(input_dir, output_dir, translation_map)
        
        expected = [
            (os.path.join(input_dir, 'Camera-Tuin'), os.path.join(output_dir, 'garden'), 'garden'),
            (os.path.join(input_dir, 'Camera-Oprit'), os.path.join(output_dir, 'driveway'), 'driveway'),
        ]
        
        result_sorted = sorted(result)
        expected_sorted = sorted(expected)
        
        assert result_sorted == expected_sorted


def test_discover_cameras_partial_translation(temp_dirs):
    """Test camera discovery with partial translation mapping"""
    input_dir = temp_dirs['src']
    output_dir = temp_dirs['dst']
    
    # Create mock camera directories
    os.makedirs(os.path.join(input_dir, 'Camera-Tuin'))
    os.makedirs(os.path.join(input_dir, 'Camera-Oprit'))
    os.makedirs(os.path.join(input_dir, 'Untranslated-Cam'))
    
    translation_map = {
        'Camera-Tuin': 'garden',
        # Camera-Oprit and Untranslated-Cam have no translation
    }
    
    with patch('builtins.print'):
        result = discover_cameras(input_dir, output_dir, translation_map)
        
        expected = [
            (os.path.join(input_dir, 'Camera-Tuin'), os.path.join(output_dir, 'garden'), 'garden'),
            (os.path.join(input_dir, 'Camera-Oprit'), os.path.join(output_dir, 'Camera-Oprit'), 'Camera-Oprit'),
            (os.path.join(input_dir, 'Untranslated-Cam'), os.path.join(output_dir, 'Untranslated-Cam'), 'Untranslated-Cam'),
        ]
        
        result_sorted = sorted(result)
        expected_sorted = sorted(expected)
        
        assert result_sorted == expected_sorted


def test_discover_cameras_exception_handling():
    """Test camera discovery handles exceptions gracefully"""
    with patch('src.process_hikvision_folder.Path') as mock_path_class:
        mock_path = mock_path_class.return_value
        mock_path.exists.return_value = True
        mock_path.iterdir.side_effect = Exception("Test exception")
        
        with patch('builtins.print') as mock_print:
            result = discover_cameras("/input", "/output")
            assert result == []
            mock_print.assert_called_with("Error discovering cameras from /input: Test exception")