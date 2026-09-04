# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for common module utilities."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import MagicMock

# Mock external dependencies before importing common
# Note: common.py imports from ansible.module_utils which has platform-specific code
sys.modules["ansible"] = MagicMock()
sys.modules["ansible.module_utils"] = MagicMock()
sys.modules["ansible.module_utils.common"] = MagicMock()
sys.modules["ansible.module_utils.common.process"] = MagicMock()
sys.modules["ansible.module_utils.facts"] = MagicMock()
sys.modules["ansible.module_utils.facts.utils"] = MagicMock()

from plugins.module_utils.common import (
    _findstr,
    human_to_bytes,
    human_to_real,
    convert_to_millisecs,
    convert_time_to_millisecs,
)


class TestFindstr:
    """Tests for _findstr function."""

    def test_match_found_single_line(self):
        """Test finding match in single line."""
        text = "this is a test line"
        assert _findstr(text, "test") == "this is a test line"

    def test_match_found_multiline(self):
        """Test finding match in multiline text."""
        text = "line1\nline2 target\nline3"
        assert _findstr(text, "target") == "line2 target"

    def test_match_found_first_occurrence(self):
        """Test that first occurrence is returned."""
        text = "line1 match\nline2 match\nline3"
        assert _findstr(text, "match") == "line1 match"

    def test_match_not_found(self):
        """Test that None is returned when match not found."""
        text = "line1\nline2\nline3"
        assert _findstr(text, "missing") is None

    def test_empty_text(self):
        """Test with empty text."""
        assert _findstr("", "test") is None

    def test_empty_match(self):
        """Test with empty match string."""
        text = "line1\nline2"
        # Empty string matches every line, should return first line
        assert _findstr(text, "") == "line1"

    def test_partial_match(self):
        """Test partial string matching."""
        text = "prefix_target_suffix"
        assert _findstr(text, "target") == "prefix_target_suffix"

    def test_case_sensitive(self):
        """Test that matching is case-sensitive."""
        text = "line1 TEST\nline2 test"
        assert _findstr(text, "test") == "line2 test"
        assert _findstr(text, "TEST") == "line1 TEST"


class TestHumanToBytes:
    """Tests for human_to_bytes function."""

    def test_kilobytes(self):
        """Test kilobyte conversion."""
        assert human_to_bytes("1K") == 1024
        assert human_to_bytes("10K") == 10240

    def test_megabytes(self):
        """Test megabyte conversion."""
        assert human_to_bytes("1M") == 1048576
        assert human_to_bytes("100M") == 104857600

    def test_gigabytes(self):
        """Test gigabyte conversion."""
        assert human_to_bytes("1G") == 1073741824
        assert human_to_bytes("100G") == 107374182400

    def test_terabytes(self):
        """Test terabyte conversion."""
        assert human_to_bytes("1T") == 1099511627776
        assert human_to_bytes("10T") == 10995116277760

    def test_petabytes(self):
        """Test petabyte conversion."""
        assert human_to_bytes("1P") == 1125899906842624

    def test_case_insensitive(self):
        """Test that units are case-insensitive."""
        assert human_to_bytes("1g") == 1073741824
        assert human_to_bytes("1G") == 1073741824

    def test_invalid_unit_returns_zero(self):
        """Test that invalid unit returns 0."""
        assert human_to_bytes("100X") == 0

    def test_non_numeric_returns_zero(self):
        """Test that non-numeric value returns 0."""
        assert human_to_bytes("abcG") == 0


class TestHumanToReal:
    """Tests for human_to_real function."""

    def test_plain_number(self):
        """Test plain number without suffix."""
        assert human_to_real("1000") == "1000"
        assert human_to_real("5000") == "5000"

    def test_thousands(self):
        """Test K (thousands) suffix."""
        assert human_to_real("1K") == 1000
        assert human_to_real("10K") == 10000
        assert human_to_real("100K") == 100000

    def test_millions(self):
        """Test M (millions) suffix."""
        assert human_to_real("1M") == 1000000
        assert human_to_real("10M") == 10000000

    def test_case_insensitive(self):
        """Test that units are case-insensitive."""
        assert human_to_real("5k") == 5000
        assert human_to_real("5K") == 5000
        assert human_to_real("2m") == 2000000
        assert human_to_real("2M") == 2000000

    def test_invalid_unit_returns_zero(self):
        """Test that invalid unit returns 0."""
        assert human_to_real("100X") == 0

    def test_non_numeric_digit_returns_zero(self):
        """Test that non-numeric digit part returns 0."""
        assert human_to_real("abcM") == 0
        assert human_to_real("x.yK") == 0


class TestConvertToMillisecs:
    """Tests for convert_to_millisecs function (12-hour clock)."""

    def test_midnight(self):
        """Test 12AM (midnight)."""
        assert convert_to_millisecs("12AM") == 0

    def test_noon(self):
        """Test 12PM (noon)."""
        assert convert_to_millisecs("12PM") == 43200000

    def test_am_hours(self):
        """Test AM hours."""
        assert convert_to_millisecs("1AM") == 3600000
        assert convert_to_millisecs("6AM") == 21600000
        assert convert_to_millisecs("11AM") == 39600000

    def test_pm_hours(self):
        """Test PM hours."""
        assert convert_to_millisecs("1PM") == 46800000
        assert convert_to_millisecs("6PM") == 64800000
        assert convert_to_millisecs("11PM") == 82800000


class TestConvertTimeToMillisecs:
    """Tests for convert_time_to_millisecs function (duration)."""

    def test_weeks(self):
        """Test week conversion."""
        assert convert_time_to_millisecs("1w") == 604800000
        assert convert_time_to_millisecs("2w") == 1209600000

    def test_days(self):
        """Test day conversion."""
        assert convert_time_to_millisecs("1d") == 86400000
        assert convert_time_to_millisecs("7d") == 604800000

    def test_hours(self):
        """Test hour conversion."""
        assert convert_time_to_millisecs("1h") == 3600000
        assert convert_time_to_millisecs("24h") == 86400000

    def test_minutes(self):
        """Test minute conversion."""
        assert convert_time_to_millisecs("1m") == 60000
        assert convert_time_to_millisecs("60m") == 3600000

    def test_seconds(self):
        """Test second conversion."""
        assert convert_time_to_millisecs("1s") == 1000
        assert convert_time_to_millisecs("60s") == 60000

    def test_invalid_unit_returns_zero(self):
        """Test that invalid unit returns 0."""
        assert convert_time_to_millisecs("100x") == 0

    def test_case_insensitive(self):
        """Test that units are case-insensitive."""
        assert convert_time_to_millisecs("1D") == 86400000
        assert convert_time_to_millisecs("1d") == 86400000

    def test_non_numeric_value_returns_zero(self):
        """Test that non-numeric value causes exception and returns 0."""
        assert convert_time_to_millisecs("abcd") == 0
        assert convert_time_to_millisecs("x.yw") == 0
