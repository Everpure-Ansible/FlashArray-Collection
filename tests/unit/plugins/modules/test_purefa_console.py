# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_console module."""

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

from plugins.modules.purefa_console import main, update_console


class TestUpdateConsole:
    """Test cases for update_console function"""

    @patch("plugins.modules.purefa_console.check_response")
    @patch("plugins.modules.purefa_console.get_with_context")
    def test_enable_console_lock(self, mock_get_with_context, mock_check_response):
        """Test enabling console lock"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"state": "enable"}

        mock_array = Mock()
        mock_current = Mock()
        mock_current.console_lock_enabled = False
        mock_get_response = Mock()
        mock_get_response.items = [mock_current]
        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_get_with_context.side_effect = [mock_get_response, mock_patch_response]

        update_console(mock_module, mock_array)

        assert mock_get_with_context.call_count == 2
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_console.check_response")
    @patch("plugins.modules.purefa_console.get_with_context")
    def test_disable_console_lock(self, mock_get_with_context, mock_check_response):
        """Test disabling console lock"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"state": "disable"}

        mock_array = Mock()
        mock_current = Mock()
        mock_current.console_lock_enabled = True
        mock_get_response = Mock()
        mock_get_response.items = [mock_current]
        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_get_with_context.side_effect = [mock_get_response, mock_patch_response]

        update_console(mock_module, mock_array)

        assert mock_get_with_context.call_count == 2
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_console.check_response")
    @patch("plugins.modules.purefa_console.get_with_context")
    def test_no_change_needed(self, mock_get_with_context, mock_check_response):
        """Test when console lock state already matches"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"state": "enable"}

        mock_array = Mock()
        mock_current = Mock()
        mock_current.console_lock_enabled = True  # Already enabled
        mock_get_response = Mock()
        mock_get_response.items = [mock_current]
        mock_get_with_context.return_value = mock_get_response

        update_console(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_console.check_response")
    @patch("plugins.modules.purefa_console.get_with_context")
    def test_check_mode(self, mock_get_with_context, mock_check_response):
        """Test console lock update in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"state": "enable"}

        mock_array = Mock()
        mock_current = Mock()
        mock_current.console_lock_enabled = False
        mock_get_response = Mock()
        mock_get_response.items = [mock_current]
        mock_get_with_context.return_value = mock_get_response

        update_console(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_console.get_array")
    @patch("plugins.modules.purefa_console.AnsibleModule")
    @patch("plugins.modules.purefa_console.HAS_PYPURECLIENT", False)
    def test_main_missing_sdk(self, mock_ansible_module, mock_get_array):
        """Test main when pypureclient SDK is missing"""
        mock_module = Mock()
        mock_module.params = {"state": "enable", "context": ""}
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "py-pure-client sdk is required" in call_args["msg"]
