# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_audits module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock

# Mock pytz before importing module
mock_pytz = MagicMock()
mock_pytz.all_timezones_set = {"UTC", "America/New_York", "Europe/London"}


def mock_timezone(tz_name):
    """Mock timezone function"""
    mock_tz = MagicMock()
    mock_tz.__str__ = lambda x: tz_name
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

from plugins.modules.purefa_audits import (
    _get_filter_string,
)


class TestGetFilterString:
    """Tests for _get_filter_string function"""

    def test_get_filter_string_no_start(self):
        """Test _get_filter_string when start is not provided"""
        mock_module = Mock()
        mock_module.params = {"start": None}

        result = _get_filter_string(mock_module, "+00:00")

        assert result == "time>=0"

    def test_get_filter_string_start_zero(self):
        """Test _get_filter_string when start is '0'"""
        mock_module = Mock()
        mock_module.params = {"start": "0"}

        result = _get_filter_string(mock_module, "+00:00")

        assert result == "time>=0"

    def test_get_filter_string_with_date(self):
        """Test _get_filter_string with a valid date"""
        mock_module = Mock()
        mock_module.params = {"start": "2026-01-15 10:30:00"}

        result = _get_filter_string(mock_module, "+00:00")

        # Should contain time>= with a non-zero timestamp
        assert result.startswith("time>=")
        assert result != "time>=0"

    def test_get_filter_string_with_timezone_offset(self):
        """Test _get_filter_string with timezone offset"""
        mock_module = Mock()
        mock_module.params = {"start": "2026-02-20 12:00:00"}

        result = _get_filter_string(mock_module, "-05:00")

        assert result.startswith("time>=")
        # The timestamp should be calculated with timezone offset


# Import main for testing
from plugins.modules.purefa_audits import main
import pytest
from unittest.mock import patch


class TestAuditsMissingDependency:
    """Test cases for missing dependency"""

    @patch("plugins.modules.purefa_audits.HAS_PYTZ", False)
    @patch("plugins.modules.purefa_audits.AnsibleModule")
    def test_missing_pytz_dependency_fails(self, mock_ansible_module):
        """Test that missing pytz dependency fails"""
        mock_module = Mock()
        mock_module.params = {
            "start": None,
            "timezone": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once_with(
            msg="pytz is required for this module"
        )


class TestMainTimezone:
    """Test cases for timezone handling in main"""

    @patch("plugins.modules.purefa_audits.datetime")
    @patch("plugins.modules.purefa_audits.get_with_context")
    @patch("plugins.modules.purefa_audits.get_array")
    @patch("plugins.modules.purefa_audits.AnsibleModule")
    def test_main_timezone_from_api(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_datetime,
    ):
        """Test timezone retrieved from API for new Purity version"""
        mock_module = Mock()
        mock_module.params = {
            "start": None,
            "timezone": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        # Mock array info with timezone
        mock_array_info = Mock()
        mock_array_info.time_zone = "America/New_York"
        mock_response_arrays = Mock()
        mock_response_arrays.items = [mock_array_info]

        # Mock audits response
        mock_response_audits = Mock()
        mock_response_audits.status_code = 200
        mock_response_audits.items = []

        mock_get_with_context.side_effect = [mock_response_arrays, mock_response_audits]

        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.return_value = "-0500"
        mock_datetime.datetime.now.return_value = mock_now

        main()

        mock_module.exit_json.assert_called_once_with(changed=False, purefa_audits={})

    @patch("plugins.modules.purefa_audits.get_local_tz")
    @patch("plugins.modules.purefa_audits.datetime")
    @patch("plugins.modules.purefa_audits.get_with_context")
    @patch("plugins.modules.purefa_audits.get_array")
    @patch("plugins.modules.purefa_audits.AnsibleModule")
    def test_main_timezone_from_local(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_datetime,
        mock_get_local_tz,
    ):
        """Test timezone from local for old Purity version"""
        mock_module = Mock()
        mock_module.params = {
            "start": None,
            "timezone": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"  # Old version
        mock_get_array.return_value = mock_array

        mock_get_local_tz.return_value = "UTC"

        # Mock audits response
        mock_response_audits = Mock()
        mock_response_audits.status_code = 200
        mock_response_audits.items = []
        mock_get_with_context.return_value = mock_response_audits

        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.return_value = "+0000"
        mock_datetime.datetime.now.return_value = mock_now

        main()

        mock_module.exit_json.assert_called_once_with(changed=False, purefa_audits={})

    @patch("plugins.modules.purefa_audits.pytz")
    @patch("plugins.modules.purefa_audits.datetime")
    @patch("plugins.modules.purefa_audits.get_with_context")
    @patch("plugins.modules.purefa_audits.get_array")
    @patch("plugins.modules.purefa_audits.AnsibleModule")
    def test_main_invalid_timezone_fails(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_datetime,
        mock_pytz,
    ):
        """Test invalid timezone fails"""
        mock_module = Mock()
        mock_module.params = {
            "start": None,
            "timezone": "Invalid/Timezone",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        # Set up pytz mock - timezone not in all_timezones_set
        mock_pytz.all_timezones_set = {"UTC", "America/New_York"}

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once_with(
            msg="Timezone Invalid/Timezone is not valid"
        )

    @patch("plugins.modules.purefa_audits.pytz")
    @patch("plugins.modules.purefa_audits.datetime")
    @patch("plugins.modules.purefa_audits.get_with_context")
    @patch("plugins.modules.purefa_audits.get_array")
    @patch("plugins.modules.purefa_audits.AnsibleModule")
    def test_main_explicit_timezone(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_datetime,
        mock_pytz,
    ):
        """Test explicit timezone is used"""
        mock_module = Mock()
        mock_module.params = {
            "start": None,
            "timezone": "UTC",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        mock_pytz.all_timezones_set = {"UTC", "America/New_York"}
        mock_tz = Mock()
        mock_pytz.timezone.return_value = mock_tz

        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.return_value = "+0000"
        mock_datetime.datetime.now.return_value = mock_now

        # Mock audits response
        mock_response_audits = Mock()
        mock_response_audits.status_code = 200
        mock_response_audits.items = []
        mock_get_with_context.return_value = mock_response_audits

        main()

        mock_module.exit_json.assert_called_once_with(changed=False, purefa_audits={})


class TestMainAudits:
    """Test cases for audit retrieval"""

    @patch("plugins.modules.purefa_audits.pytz")
    @patch("plugins.modules.purefa_audits.datetime")
    @patch("plugins.modules.purefa_audits.get_with_context")
    @patch("plugins.modules.purefa_audits.get_array")
    @patch("plugins.modules.purefa_audits.AnsibleModule")
    def test_main_get_audits_success(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_datetime,
        mock_pytz,
    ):
        """Test successful retrieval of audits"""
        mock_module = Mock()
        mock_module.params = {
            "start": None,
            "timezone": "UTC",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        mock_pytz.all_timezones_set = {"UTC"}
        mock_tz = Mock()
        mock_pytz.timezone.return_value = mock_tz

        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.return_value = "+0000"
        mock_datetime.datetime.now.return_value = mock_now

        # Mock audit
        mock_origin = Mock()
        mock_origin.name = "cli"
        mock_audit = Mock()
        mock_audit.name = "audit1"
        mock_audit.time = 1700000000000
        mock_audit.arguments = "arg1"
        mock_audit.user = "admin"
        mock_audit.command = "purarray"
        mock_audit.subcommand = "list"
        mock_audit.origin = mock_origin

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_audit]
        mock_get_with_context.return_value = mock_response

        # Mock fromtimestamp
        mock_dt = Mock()
        mock_dt.strftime.return_value = "2023-11-14 22:13:20 UTC"
        mock_datetime.datetime.fromtimestamp.return_value = mock_dt

        main()

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args
        assert call_args.kwargs["changed"] is False
        audits = call_args.kwargs["purefa_audits"]
        assert "audit1" in audits
        assert audits["audit1"]["user"] == "admin"
        assert audits["audit1"]["command"] == "purarray"

    @patch("plugins.modules.purefa_audits.pytz")
    @patch("plugins.modules.purefa_audits.datetime")
    @patch("plugins.modules.purefa_audits.get_with_context")
    @patch("plugins.modules.purefa_audits.get_array")
    @patch("plugins.modules.purefa_audits.AnsibleModule")
    def test_main_get_audits_failed(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_datetime,
        mock_pytz,
    ):
        """Test failed retrieval of audits"""
        mock_module = Mock()
        mock_module.params = {
            "start": None,
            "timezone": "UTC",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        mock_pytz.all_timezones_set = {"UTC"}
        mock_tz = Mock()
        mock_pytz.timezone.return_value = mock_tz

        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.return_value = "+0000"
        mock_datetime.datetime.now.return_value = mock_now

        # Mock error response
        mock_error = Mock()
        mock_error.message = "API error"
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.errors = [mock_error]
        mock_get_with_context.return_value = mock_response

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once_with(
            msg="Failed to get audit events. Error: API error"
        )
