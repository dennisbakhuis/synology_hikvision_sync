#!/usr/bin/env python3
"""
Tests for parse_bool_env function
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sync_hikvision_cameras import parse_bool_env


class TestParseBoolEnv:
    """Test parse_bool_env function"""

    def test_parse_true_variations(self) -> None:
        """Test parsing of true values"""
        assert parse_bool_env("true") is True
        assert parse_bool_env("True") is True
        assert parse_bool_env("TRUE") is True
        assert parse_bool_env("1") is True
        assert parse_bool_env("yes") is True
        assert parse_bool_env("Yes") is True
        assert parse_bool_env("YES") is True
        assert parse_bool_env("on") is True
        assert parse_bool_env("On") is True
        assert parse_bool_env("ON") is True

    def test_parse_false_variations(self) -> None:
        """Test parsing of false values"""
        assert parse_bool_env("false") is False
        assert parse_bool_env("False") is False
        assert parse_bool_env("FALSE") is False
        assert parse_bool_env("0") is False
        assert parse_bool_env("no") is False
        assert parse_bool_env("No") is False
        assert parse_bool_env("NO") is False
        assert parse_bool_env("off") is False
        assert parse_bool_env("Off") is False
        assert parse_bool_env("OFF") is False

    def test_parse_empty_uses_default(self) -> None:
        """Test that empty string uses default"""
        assert parse_bool_env("", default=True) is True
        assert parse_bool_env("", default=False) is False

    def test_parse_invalid_uses_default(self) -> None:
        """Test that invalid values use default"""
        assert parse_bool_env("invalid", default=True) is True
        assert parse_bool_env("invalid", default=False) is False
        assert parse_bool_env("maybe", default=True) is True

    def test_parse_whitespace_handling(self) -> None:
        """Test that whitespace is stripped"""
        assert parse_bool_env("  true  ") is True
        assert parse_bool_env("  false  ") is False
        assert parse_bool_env("\ttrue\t") is True
        assert parse_bool_env("\n1\n") is True

    def test_default_parameter(self) -> None:
        """Test default parameter works correctly"""
        assert parse_bool_env("unknown") is True  # default is True
        assert parse_bool_env("unknown", False) is False
