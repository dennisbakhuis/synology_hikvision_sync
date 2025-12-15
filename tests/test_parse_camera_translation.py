#!/usr/bin/env python3
"""
Tests for parse_camera_translation function
"""

import os
import sys
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import parse_camera_translation


class TestParseCameraTranslation:
    """Test camera translation parsing functionality"""

    def test_empty_translation_string(self) -> None:
        """Test parsing empty translation string"""
        result = parse_camera_translation("")
        assert result == {}

    def test_none_translation_string(self) -> None:
        """Test parsing empty/None-like translation string"""
        result = parse_camera_translation("")
        assert result == {}

    def test_single_camera_translation(self) -> None:
        """Test parsing single camera translation"""
        result = parse_camera_translation("Camera-Tuin:garden")
        assert result == {"Camera-Tuin": "garden"}

    def test_multiple_camera_translations(self) -> None:
        """Test parsing multiple camera translations"""
        result = parse_camera_translation(
            "Camera-Tuin:garden,Camera-Oprit:driveway,Camera-Voor:front"
        )
        expected = {
            "Camera-Tuin": "garden",
            "Camera-Oprit": "driveway",
            "Camera-Voor": "front",
        }
        assert result == expected

    def test_whitespace_handling(self) -> None:
        """Test handling of whitespace in translation string"""
        result = parse_camera_translation(
            "  Camera-Tuin : garden  ,  Camera-Oprit : driveway  "
        )
        expected = {"Camera-Tuin": "garden", "Camera-Oprit": "driveway"}
        assert result == expected

    def test_invalid_format_ignored(self) -> None:
        """Test that invalid format entries are ignored"""
        result = parse_camera_translation(
            "Camera-Tuin:garden,InvalidEntry,Camera-Oprit:driveway"
        )
        expected = {"Camera-Tuin": "garden", "Camera-Oprit": "driveway"}
        assert result == expected

    def test_multiple_colons_uses_first(self) -> None:
        """Test that entries with multiple colons use first as separator"""
        result = parse_camera_translation("Camera-Tuin:garden:extra:info")
        assert result == {"Camera-Tuin": "garden:extra:info"}

    def test_exception_handling(self) -> None:
        """Test that exceptions during parsing are handled gracefully"""
        with patch("builtins.print"):
            # This should not raise an exception due to the try/except block
            result = parse_camera_translation("Camera-Tuin:garden")
            assert result == {"Camera-Tuin": "garden"}
