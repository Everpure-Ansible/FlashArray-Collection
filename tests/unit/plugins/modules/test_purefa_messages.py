# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_messages module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import MagicMock

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

from plugins.modules.purefa_messages import (
    _create_time_window,
    main,
)

import pytest
from unittest.mock import Mock, patch


class TestCreateTimeWindow:
    """Tests for _create_time_window function"""

    def test_create_time_window_hours(self):
        """Test _create_time_window with hours"""
        result = _create_time_window("2h")
        # HOUR = 3600000 (milliseconds)
        assert result == 3600000 * 2

    def test_create_time_window_days(self):
        """Test _create_time_window with days"""
        result = _create_time_window("3d")
        # DAY = HOUR * 24 = 86400000 (milliseconds)
        assert result == 3600000 * 24 * 3

    def test_create_time_window_weeks(self):
        """Test _create_time_window with weeks"""
        result = _create_time_window("1w")
        # WEEK = DAY * 7 = 604800000 (milliseconds)
        assert result == 3600000 * 24 * 7

    def test_create_time_window_years(self):
        """Test _create_time_window with years"""
        result = _create_time_window("1y")
        # YEAR = WEEK * 52 = 31449600000 (milliseconds)
        assert result == 3600000 * 24 * 7 * 52

    def test_create_time_window_invalid(self):
        """Test _create_time_window with invalid period"""
        result = _create_time_window("5x")
        assert result is None


class TestMain:
    """Tests for main function"""

    @patch("plugins.modules.purefa_messages.get_with_context")
    @patch("plugins.modules.purefa_messages.get_array")
    @patch("plugins.modules.purefa_messages.AnsibleModule")
    def test_main_old_api_version_fails(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
    ):
        """Test that old API version fails with appropriate message"""
        mock_module = Mock()
        mock_module.params = {
            "state": "open",
            "history": "1w",
            "flagged": False,
            "severity": "info",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once_with(
            msg="FlashArray REST version not supported. "
            "Minimum version required: 2.2"
        )

    @patch("plugins.modules.purefa_messages.get_with_context")
    @patch("plugins.modules.purefa_messages.get_array")
    @patch("plugins.modules.purefa_messages.AnsibleModule")
    def test_main_invalid_history_period_fails(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
    ):
        """Test that invalid history period fails with appropriate message"""
        mock_module = Mock()
        mock_module.params = {
            "state": "open",
            "history": "5x",  # Invalid period
            "flagged": False,
            "severity": "info",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once_with(
            msg="historical window value is not an allowsd time period"
        )

    @patch("plugins.modules.purefa_messages.time")
    @patch("plugins.modules.purefa_messages.get_with_context")
    @patch("plugins.modules.purefa_messages.get_array")
    @patch("plugins.modules.purefa_messages.AnsibleModule")
    def test_main_get_alerts_success(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_time,
    ):
        """Test successful retrieval of alerts"""
        mock_module = Mock()
        mock_module.params = {
            "state": "open",
            "history": "1w",
            "flagged": False,
            "severity": "info",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_get_array.return_value = mock_array

        # Mock time
        mock_time.time.return_value = 1700000000
        mock_time.gmtime.return_value = (2023, 11, 14, 10, 0, 0, 0, 0, 0)
        mock_time.strftime.return_value = "2023-11-14 10:00:00"

        # Mock alert
        mock_alert = Mock()
        mock_alert.name = "alert1"
        mock_alert.summary = "Test alert"
        mock_alert.component_type = "hardware"
        mock_alert.component_name = "ct0"
        mock_alert.code = 1001
        mock_alert.severity = "info"
        mock_alert.actual = "test"
        mock_alert.issue = "No issue"
        mock_alert.state = "open"
        mock_alert.flagged = False
        mock_alert.created = 1699900000000
        mock_alert.updated = 1699900000000

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_alert]
        mock_get_with_context.return_value = mock_response

        main()

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args
        assert call_args.kwargs["changed"] is False
        assert "purefa_messages" in call_args.kwargs

    @patch("plugins.modules.purefa_messages.time")
    @patch("plugins.modules.purefa_messages.get_with_context")
    @patch("plugins.modules.purefa_messages.get_array")
    @patch("plugins.modules.purefa_messages.AnsibleModule")
    def test_main_get_alerts_with_flagged_true(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_time,
    ):
        """Test retrieval of alerts with flagged=True"""
        mock_module = Mock()
        mock_module.params = {
            "state": "open",
            "history": "2d",
            "flagged": True,
            "severity": "warning",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_get_array.return_value = mock_array

        mock_time.time.return_value = 1700000000
        mock_time.gmtime.return_value = (2023, 11, 14, 10, 0, 0, 0, 0, 0)
        mock_time.strftime.return_value = "2023-11-14 10:00:00"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = []
        mock_get_with_context.return_value = mock_response

        main()

        mock_module.exit_json.assert_called_once_with(changed=False, purefa_messages={})

    @patch("plugins.modules.purefa_messages.time")
    @patch("plugins.modules.purefa_messages.get_with_context")
    @patch("plugins.modules.purefa_messages.get_array")
    @patch("plugins.modules.purefa_messages.AnsibleModule")
    def test_main_get_alerts_failed(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_time,
    ):
        """Test failed retrieval of alerts"""
        mock_module = Mock()
        mock_module.params = {
            "state": "open",
            "history": "1w",
            "flagged": False,
            "severity": "info",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_get_array.return_value = mock_array

        mock_time.time.return_value = 1700000000

        mock_error = Mock()
        mock_error.message = "API error"
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.errors = [mock_error]
        mock_get_with_context.return_value = mock_response

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once_with(
            msg="Failed to get alert messages. Error: API error"
        )

    @patch("plugins.modules.purefa_messages.time")
    @patch("plugins.modules.purefa_messages.get_with_context")
    @patch("plugins.modules.purefa_messages.get_array")
    @patch("plugins.modules.purefa_messages.AnsibleModule")
    def test_main_closed_alert(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_time,
    ):
        """Test retrieval of closed alerts"""
        mock_module = Mock()
        mock_module.params = {
            "state": "closed",
            "history": "1w",
            "flagged": False,
            "severity": "critical",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_get_array.return_value = mock_array

        mock_time.time.return_value = 1700000000
        mock_time.gmtime.return_value = (2023, 11, 14, 10, 0, 0, 0, 0, 0)
        mock_time.strftime.return_value = "2023-11-14 10:00:00"

        # Mock closed alert
        mock_alert = Mock()
        mock_alert.name = "alert2"
        mock_alert.summary = "Closed alert"
        mock_alert.component_type = "software"
        mock_alert.component_name = "purity"
        mock_alert.code = 2001
        mock_alert.severity = "critical"
        mock_alert.actual = "resolved"
        mock_alert.issue = "Issue resolved"
        mock_alert.state = "closed"
        mock_alert.flagged = False
        mock_alert.created = 1699800000000
        mock_alert.updated = 1699900000000
        mock_alert.closed = 1699950000000

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_alert]
        mock_get_with_context.return_value = mock_response

        main()

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args
        assert call_args.kwargs["changed"] is False
        messages = call_args.kwargs["purefa_messages"]
        assert "alert2" in messages
        # Verify closed timestamp was set
        assert messages["alert2"]["closed"] == "2023-11-14 10:00:00 UTC"
