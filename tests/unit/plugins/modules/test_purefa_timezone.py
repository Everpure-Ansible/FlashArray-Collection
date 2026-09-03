# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_timezone module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, patch, MagicMock

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
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()

# pytz may not be installed in the test environment, and another test module
# may already have replaced it, so stub it out here and patch the module's own
# reference in each test that needs a known set of zone names.
if "pytz" not in sys.modules:
    sys.modules["pytz"] = MagicMock()

from plugins.modules.purefa_timezone import main, update_timezone


def _pytz_stub():
    """Return a pytz stub holding a known set of time zone names"""
    stub = Mock()
    stub.all_timezones_set = {"UTC", "America/New_York", "Europe/London"}
    return stub


def _patch_response(timezone):
    """Return a mock patch_arrays response echoing back the given time zone"""
    updated = Mock()
    updated.time_zone = timezone
    response = Mock()
    response.status_code = 200
    response.items = [updated]
    return response


class TestUpdateTimezone:
    """Test cases for update_timezone function"""

    @patch("plugins.modules.purefa_timezone.check_response")
    @patch("plugins.modules.purefa_timezone.get_with_context")
    def test_update_timezone_success(self, mock_get_with_context, mock_check_response):
        """Test successful time zone update"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"timezone": "America/New_York"}

        mock_array = Mock()
        mock_get_with_context.return_value = _patch_response("America/New_York")

        update_timezone(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_called_once()
        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_timezone.check_response")
    @patch("plugins.modules.purefa_timezone.get_with_context")
    def test_update_timezone_sends_dict_body(
        self, mock_get_with_context, mock_check_response
    ):
        """Test the patch body carries time_zone

        time_zone is a read-only field of the SDK Arrays model, so it is only
        sent if the body is passed as a dict. Building the body from
        Arrays(time_zone=...) would silently patch nothing.
        """
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"timezone": "Europe/London"}

        mock_array = Mock()
        mock_get_with_context.return_value = _patch_response("Europe/London")

        update_timezone(mock_module, mock_array)

        call_args = mock_get_with_context.call_args
        assert call_args[0][1] == "patch_arrays"
        assert call_args[1]["array"] == {"time_zone": "Europe/London"}

    @patch("plugins.modules.purefa_timezone.check_response")
    @patch("plugins.modules.purefa_timezone.get_with_context")
    def test_update_timezone_not_applied(
        self, mock_get_with_context, mock_check_response
    ):
        """Test failure when the array does not take the new time zone"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"timezone": "Europe/London"}
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()
        # Array reported success but kept its old time zone
        mock_get_with_context.return_value = _patch_response("UTC")

        try:
            update_timezone(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "did not apply the requested time zone" in call_args["msg"]
        mock_module.exit_json.assert_not_called()

    @patch("plugins.modules.purefa_timezone.check_response")
    @patch("plugins.modules.purefa_timezone.get_with_context")
    def test_update_timezone_no_echo(self, mock_get_with_context, mock_check_response):
        """Test success when the response does not report a time zone"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"timezone": "Europe/London"}

        mock_array = Mock()
        mock_get_with_context.return_value = _patch_response(None)

        update_timezone(mock_module, mock_array)

        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_timezone.check_response")
    @patch("plugins.modules.purefa_timezone.get_with_context")
    def test_update_timezone_check_mode(
        self, mock_get_with_context, mock_check_response
    ):
        """Test time zone update in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"timezone": "America/New_York"}

        mock_array = Mock()

        update_timezone(mock_module, mock_array)

        # Should not call API in check mode
        mock_get_with_context.assert_not_called()
        mock_check_response.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_timezone.get_array")
    @patch("plugins.modules.purefa_timezone.AnsibleModule")
    @patch("plugins.modules.purefa_timezone.HAS_PYTZ", False)
    def test_main_missing_pytz(self, mock_ansible_module, mock_get_array):
        """Test main when pytz is missing"""
        mock_module = Mock()
        mock_module.params = {
            "timezone": "America/New_York",
            "state": "present",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "pytz is required" in call_args["msg"]
        mock_get_array.assert_not_called()

    @patch("plugins.modules.purefa_timezone.pytz", new_callable=_pytz_stub)
    @patch("plugins.modules.purefa_timezone.get_array")
    @patch("plugins.modules.purefa_timezone.AnsibleModule")
    @patch("plugins.modules.purefa_timezone.HAS_PYTZ", True)
    def test_main_invalid_timezone(
        self, mock_ansible_module, mock_get_array, mock_pytz
    ):
        """Test main with a time zone that is not in the tz database"""
        mock_module = Mock()
        mock_module.params = {
            "timezone": "Mars/Olympus_Mons",
            "state": "present",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "is not valid" in call_args["msg"]
        # The array should not be contacted with an invalid time zone
        mock_get_array.assert_not_called()

    @patch("plugins.modules.purefa_timezone.check_response")
    @patch("plugins.modules.purefa_timezone.get_with_context")
    @patch("plugins.modules.purefa_timezone.check_api_version")
    @patch("plugins.modules.purefa_timezone.pytz", new_callable=_pytz_stub)
    @patch("plugins.modules.purefa_timezone.get_array")
    @patch("plugins.modules.purefa_timezone.AnsibleModule")
    @patch("plugins.modules.purefa_timezone.HAS_PYTZ", True)
    def test_main_timezone_unchanged(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_pytz,
        mock_check_api_version,
        mock_get_with_context,
        mock_check_response,
    ):
        """Test main when the requested time zone is already set"""
        mock_module = Mock()
        mock_module.params = {
            "timezone": "Europe/London",
            "state": "present",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        mock_current = Mock()
        mock_current.time_zone = "Europe/London"  # Same as requested
        mock_response = Mock()
        mock_response.items = [mock_current]
        mock_get_with_context.return_value = mock_response

        main()

        mock_check_api_version.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_timezone.check_response")
    @patch("plugins.modules.purefa_timezone.get_with_context")
    @patch("plugins.modules.purefa_timezone.check_api_version")
    @patch("plugins.modules.purefa_timezone.pytz", new_callable=_pytz_stub)
    @patch("plugins.modules.purefa_timezone.get_array")
    @patch("plugins.modules.purefa_timezone.AnsibleModule")
    @patch("plugins.modules.purefa_timezone.HAS_PYTZ", True)
    def test_main_timezone_changed(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_pytz,
        mock_check_api_version,
        mock_get_with_context,
        mock_check_response,
    ):
        """Test main patches the array when the time zone differs"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "timezone": "America/New_York",
            "state": "present",
            "context": "",
        }
        # exit_json ends the module run, as it does under Ansible
        mock_module.exit_json.side_effect = SystemExit("exit_json called")
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        mock_current = Mock()
        mock_current.time_zone = "UTC"
        mock_get_response = Mock()
        mock_get_response.items = [mock_current]
        mock_get_with_context.side_effect = [
            mock_get_response,
            _patch_response("America/New_York"),
        ]

        try:
            main()
        except SystemExit:
            pass

        assert mock_get_with_context.call_count == 2
        patch_call = mock_get_with_context.call_args_list[1]
        assert patch_call[0][1] == "patch_arrays"
        assert patch_call[1]["array"] == {"time_zone": "America/New_York"}
        mock_module.exit_json.assert_called_once_with(changed=True)
