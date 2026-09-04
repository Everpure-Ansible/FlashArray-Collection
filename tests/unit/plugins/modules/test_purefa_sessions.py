# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_sessions module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock, patch

# Mock pytz before importing module
mock_pytz = MagicMock()
mock_pytz.all_timezones_set = {"UTC", "America/New_York", "Europe/London"}


def mock_timezone(tz_name):
    """Mock timezone function that returns a datetime.timezone-like object"""
    mock_tz = MagicMock()
    # Implement strftime behavior for datetime.now(tz).strftime("%z")
    return mock_tz


mock_pytz.timezone = mock_timezone
sys.modules["pytz"] = mock_pytz

# Mock external dependencies before importing module
sys.modules["grp"] = MagicMock()
sys.modules["pwd"] = MagicMock()
sys.modules["fcntl"] = MagicMock()
sys.modules["ansible"] = MagicMock()
sys.modules["ansible.module_utils"] = MagicMock()
sys.modules["ansible.module_utils.basic"] = MagicMock()
sys.modules["pypureclient"] = MagicMock()
sys.modules["pypureclient.flasharray"] = MagicMock()
sys.modules["ansible_collections"] = MagicMock()
sys.modules["ansible_collections.everpure"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray.plugins"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils"] = (
    MagicMock()
)
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.purefa"] = (
    MagicMock()
)
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.common"] = (
    MagicMock()
)
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.error_handlers"
] = MagicMock()

# Create a mock version module with real LooseVersion
mock_version_module = MagicMock()
from packaging.version import Version as LooseVersion

mock_version_module.LooseVersion = LooseVersion
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    mock_version_module
)

from plugins.modules.purefa_sessions import (
    _get_filter_string,
    main,
)


class TestGetFilterString:
    """Tests for _get_filter_string function"""

    def test_get_filter_string_no_params(self):
        """Test _get_filter_string when neither start nor end provided"""
        mock_module = Mock()
        mock_module.params = {"start": None, "end": None}

        result = _get_filter_string(mock_module, "+00:00")

        assert result == ""

    def test_get_filter_string_start_only(self):
        """Test _get_filter_string with start time only"""
        mock_module = Mock()
        mock_module.params = {"start": "2024-01-01 00:00:00", "end": None}

        result = _get_filter_string(mock_module, "+00:00")

        assert "start_time>=" in result
        assert "end_time" not in result

    def test_get_filter_string_end_only(self):
        """Test _get_filter_string with end time only"""
        mock_module = Mock()
        mock_module.params = {"start": None, "end": "2024-01-01 23:59:59"}

        result = _get_filter_string(mock_module, "+00:00")

        assert "end_time<=" in result
        assert "start_time" not in result

    def test_get_filter_string_both_params(self):
        """Test _get_filter_string with both start and end times"""
        mock_module = Mock()
        mock_module.params = {
            "start": "2024-01-01 00:00:00",
            "end": "2024-01-01 23:59:59",
        }

        result = _get_filter_string(mock_module, "+00:00")

        assert "start_time>=" in result
        assert "end_time<=" in result
        assert " and " in result

    def test_get_filter_string_start_zero(self):
        """Test _get_filter_string with start time of 0"""
        mock_module = Mock()
        mock_module.params = {"start": "0", "end": None}

        result = _get_filter_string(mock_module, "+00:00")

        assert "start_time>=0" in result

    def test_get_filter_string_end_zero(self):
        """Test _get_filter_string with end time of 0"""
        mock_module = Mock()
        mock_module.params = {"start": None, "end": "0"}

        result = _get_filter_string(mock_module, "+00:00")

        assert "end_time<=0" in result


def _mock_datetime_now(*args, **kwargs):
    """Return a mock datetime that supports strftime and fromtimestamp"""
    mock_dt = Mock()
    mock_dt.strftime.return_value = "+0000"
    return mock_dt


class TestMain:
    """Test cases for main() function"""

    def test_main_no_pytz(self):
        """Test main() fails when pytz is not available"""
        import pytest

        with patch("plugins.modules.purefa_sessions.HAS_PYTZ", False):
            with patch(
                "plugins.modules.purefa_sessions.AnsibleModule"
            ) as mock_ansible_module:
                mock_module = Mock()
                mock_module.fail_json.side_effect = SystemExit(1)
                mock_ansible_module.return_value = mock_module

                with pytest.raises(SystemExit):
                    main()

                mock_module.fail_json.assert_called()

    def test_main_invalid_timezone(self):
        """Test main() fails when invalid timezone provided"""
        import pytest

        with patch(
            "plugins.modules.purefa_sessions.AnsibleModule"
        ) as mock_ansible_module:
            with patch("plugins.modules.purefa_sessions.get_array") as mock_get_array:
                mock_module = Mock()
                mock_module.params = {
                    "start": None,
                    "end": None,
                    "timezone": "Invalid/Timezone",
                }
                mock_module.fail_json.side_effect = SystemExit(1)
                mock_ansible_module.return_value = mock_module

                mock_array = Mock()
                mock_array.get_rest_version.return_value = "2.20"
                mock_get_array.return_value = mock_array

                with pytest.raises(SystemExit):
                    main()

                mock_module.fail_json.assert_called()

    def test_main_with_timezone_from_api(self):
        """Test main() gets timezone from API when version >= 2.26"""
        with patch(
            "plugins.modules.purefa_sessions.AnsibleModule"
        ) as mock_ansible_module:
            with patch("plugins.modules.purefa_sessions.get_array") as mock_get_array:
                with patch("plugins.modules.purefa_sessions.datetime") as mock_datetime:
                    mock_datetime.datetime.now.return_value = _mock_datetime_now()
                    mock_datetime.datetime.fromtimestamp.return_value = (
                        _mock_datetime_now()
                    )

                    mock_module = Mock()
                    mock_module.params = {
                        "start": None,
                        "end": None,
                        "timezone": None,
                    }
                    mock_ansible_module.return_value = mock_module

                    mock_array_info = Mock()
                    mock_array_info.time_zone = "UTC"

                    mock_array = Mock()
                    mock_array.get_rest_version.return_value = "2.30"
                    mock_array.get_arrays.return_value = Mock(items=[mock_array_info])
                    mock_array.get_sessions.return_value = Mock(
                        status_code=200, items=[]
                    )
                    mock_get_array.return_value = mock_array

                    main()

                    mock_module.exit_json.assert_called()

    def test_main_with_timezone_from_local(self):
        """Test main() gets timezone from local when version < 2.26"""
        with patch(
            "plugins.modules.purefa_sessions.AnsibleModule"
        ) as mock_ansible_module:
            with patch("plugins.modules.purefa_sessions.get_array") as mock_get_array:
                with patch(
                    "plugins.modules.purefa_sessions.get_local_tz"
                ) as mock_get_local_tz:
                    with patch(
                        "plugins.modules.purefa_sessions.datetime"
                    ) as mock_datetime:
                        mock_datetime.datetime.now.return_value = _mock_datetime_now()
                        mock_datetime.datetime.fromtimestamp.return_value = (
                            _mock_datetime_now()
                        )
                        mock_get_local_tz.return_value = "America/New_York"

                        mock_module = Mock()
                        mock_module.params = {
                            "start": None,
                            "end": None,
                            "timezone": None,
                        }
                        mock_ansible_module.return_value = mock_module

                        mock_array = Mock()
                        mock_array.get_rest_version.return_value = "2.20"
                        mock_array.get_sessions.return_value = Mock(
                            status_code=200, items=[]
                        )
                        mock_get_array.return_value = mock_array

                        main()

                        mock_get_local_tz.assert_called_once()
                        mock_module.exit_json.assert_called()

    def test_main_with_explicit_timezone(self):
        """Test main() uses explicit timezone when provided"""
        with patch(
            "plugins.modules.purefa_sessions.AnsibleModule"
        ) as mock_ansible_module:
            with patch("plugins.modules.purefa_sessions.get_array") as mock_get_array:
                with patch("plugins.modules.purefa_sessions.datetime") as mock_datetime:
                    mock_datetime.datetime.now.return_value = _mock_datetime_now()
                    mock_datetime.datetime.fromtimestamp.return_value = (
                        _mock_datetime_now()
                    )

                    mock_module = Mock()
                    mock_module.params = {
                        "start": None,
                        "end": None,
                        "timezone": "UTC",
                    }
                    mock_ansible_module.return_value = mock_module

                    mock_array = Mock()
                    mock_array.get_rest_version.return_value = "2.30"
                    mock_array.get_sessions.return_value = Mock(
                        status_code=200, items=[]
                    )
                    mock_get_array.return_value = mock_array

                    main()

                    mock_module.exit_json.assert_called()

    def test_main_get_sessions_failed(self):
        """Test main() fails when get_sessions returns error"""
        import pytest

        with patch(
            "plugins.modules.purefa_sessions.AnsibleModule"
        ) as mock_ansible_module:
            with patch("plugins.modules.purefa_sessions.get_array") as mock_get_array:
                with patch("plugins.modules.purefa_sessions.datetime") as mock_datetime:
                    mock_datetime.datetime.now.return_value = _mock_datetime_now()

                    mock_module = Mock()
                    mock_module.params = {
                        "start": None,
                        "end": None,
                        "timezone": "UTC",
                    }
                    mock_module.fail_json.side_effect = SystemExit(1)
                    mock_ansible_module.return_value = mock_module

                    mock_error = Mock()
                    mock_error.message = "API Error"

                    mock_array = Mock()
                    mock_array.get_rest_version.return_value = "2.30"
                    mock_array.get_sessions.return_value = Mock(
                        status_code=400, errors=[mock_error]
                    )
                    mock_get_array.return_value = mock_array

                    with pytest.raises(SystemExit):
                        main()

                    mock_module.fail_json.assert_called()

    def test_main_sessions_with_times(self):
        """Test main() returns sessions with proper time formatting"""
        with patch(
            "plugins.modules.purefa_sessions.AnsibleModule"
        ) as mock_ansible_module:
            with patch("plugins.modules.purefa_sessions.get_array") as mock_get_array:
                with patch("plugins.modules.purefa_sessions.datetime") as mock_datetime:
                    mock_datetime.datetime.now.return_value = _mock_datetime_now()
                    mock_datetime.datetime.fromtimestamp.return_value = (
                        _mock_datetime_now()
                    )

                    mock_module = Mock()
                    mock_module.params = {
                        "start": None,
                        "end": None,
                        "timezone": "UTC",
                    }
                    mock_ansible_module.return_value = mock_module

                    mock_session = Mock()
                    mock_session.name = "session1"
                    mock_session.start_time = 1704067200000  # Jan 1 2024 00:00:00 UTC
                    mock_session.end_time = 1704153600000  # Jan 2 2024 00:00:00 UTC
                    mock_session.user_interface = "web"
                    mock_session.user = "admin"
                    mock_session.location = "192.168.1.1"
                    mock_session.event_count = 1
                    mock_session.event = "login"
                    mock_session.method = "POST"

                    mock_array = Mock()
                    mock_array.get_rest_version.return_value = "2.30"
                    mock_array.get_sessions.return_value = Mock(
                        status_code=200, items=[mock_session]
                    )
                    mock_get_array.return_value = mock_array

                    main()

                    mock_module.exit_json.assert_called_once()
                    call_args = mock_module.exit_json.call_args
                    assert "purefa_sessions" in call_args[1]

    def test_main_sessions_without_times(self):
        """Test main() handles sessions without start/end times"""
        with patch(
            "plugins.modules.purefa_sessions.AnsibleModule"
        ) as mock_ansible_module:
            with patch("plugins.modules.purefa_sessions.get_array") as mock_get_array:
                with patch("plugins.modules.purefa_sessions.datetime") as mock_datetime:
                    mock_datetime.datetime.now.return_value = _mock_datetime_now()

                    mock_module = Mock()
                    mock_module.params = {
                        "start": None,
                        "end": None,
                        "timezone": "UTC",
                    }
                    mock_ansible_module.return_value = mock_module

                    mock_session = Mock(spec=["name", "user_interface", "event"])
                    mock_session.name = "session1"
                    mock_session.user_interface = "web"
                    mock_session.event = "login"
                    # No start_time or end_time

                    mock_array = Mock()
                    mock_array.get_rest_version.return_value = "2.30"
                    mock_array.get_sessions.return_value = Mock(
                        status_code=200, items=[mock_session]
                    )
                    mock_get_array.return_value = mock_array

                    main()

                    mock_module.exit_json.assert_called_once()

    def test_main_with_filter_string(self):
        """Test main() passes filter string when start/end times provided"""
        with patch(
            "plugins.modules.purefa_sessions.AnsibleModule"
        ) as mock_ansible_module:
            with patch("plugins.modules.purefa_sessions.get_array") as mock_get_array:
                with patch("plugins.modules.purefa_sessions.datetime") as mock_datetime:
                    mock_datetime.datetime.now.return_value = _mock_datetime_now()
                    mock_datetime.datetime.strptime.return_value = _mock_datetime_now()
                    mock_datetime.datetime.timestamp.return_value = 1704067200

                    mock_module = Mock()
                    mock_module.params = {
                        "start": "2024-01-01 00:00:00",
                        "end": None,
                        "timezone": "UTC",
                    }
                    mock_ansible_module.return_value = mock_module

                    mock_array = Mock()
                    mock_array.get_rest_version.return_value = "2.30"
                    mock_array.get_sessions.return_value = Mock(
                        status_code=200, items=[]
                    )
                    mock_get_array.return_value = mock_array

                    main()

                    # Verify get_sessions was called with a filter argument
                    mock_array.get_sessions.assert_called_once()
                    call_kwargs = mock_array.get_sessions.call_args[1]
                    assert "filter" in call_kwargs
                    mock_module.exit_json.assert_called()
