# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_arrayname module."""

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

from plugins.modules.purefa_arrayname import main, update_name


class TestUpdateName:
    """Test cases for update_name function"""

    @patch("plugins.modules.purefa_arrayname.check_response")
    @patch("plugins.modules.purefa_arrayname.get_with_context")
    def test_update_name_success(self, mock_get_with_context, mock_check_response):
        """Test successful array name update"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "new-array-name"}

        mock_array = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get_with_context.return_value = mock_response

        update_name(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_arrayname.check_response")
    @patch("plugins.modules.purefa_arrayname.get_with_context")
    def test_update_name_check_mode(self, mock_get_with_context, mock_check_response):
        """Test array name update in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "new-array-name"}

        mock_array = Mock()

        update_name(mock_module, mock_array)

        # Should not call API in check mode
        mock_get_with_context.assert_not_called()
        mock_check_response.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_arrayname.get_array")
    @patch("plugins.modules.purefa_arrayname.AnsibleModule")
    @patch("plugins.modules.purefa_arrayname.HAS_PURESTORAGE", False)
    def test_main_missing_sdk(self, mock_ansible_module, mock_get_array):
        """Test main when pypureclient SDK is missing"""
        mock_module = Mock()
        mock_module.params = {"name": "test-array", "state": "present", "context": ""}
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "py-pure-client sdk is required" in call_args["msg"]

    @patch("plugins.modules.purefa_arrayname.get_with_context")
    @patch("plugins.modules.purefa_arrayname.get_array")
    @patch("plugins.modules.purefa_arrayname.AnsibleModule")
    @patch("plugins.modules.purefa_arrayname.HAS_PURESTORAGE", True)
    def test_main_invalid_name(
        self, mock_ansible_module, mock_get_array, mock_get_with_context
    ):
        """Test main with invalid array name"""
        mock_module = Mock()
        mock_module.params = {
            "name": "-invalid-name-",  # Invalid: starts and ends with dash
            "state": "present",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "does not conform to array name rules" in call_args["msg"]

    @patch("plugins.modules.purefa_arrayname.get_with_context")
    @patch("plugins.modules.purefa_arrayname.get_array")
    @patch("plugins.modules.purefa_arrayname.AnsibleModule")
    @patch("plugins.modules.purefa_arrayname.HAS_PURESTORAGE", True)
    def test_main_name_unchanged(
        self, mock_ansible_module, mock_get_array, mock_get_with_context
    ):
        """Test main when name is already set"""
        mock_module = Mock()
        mock_module.params = {
            "name": "existing-array",
            "state": "present",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        mock_current = Mock()
        mock_current.name = "existing-array"  # Same as requested
        mock_response = Mock()
        mock_response.items = [mock_current]
        mock_get_with_context.return_value = mock_response

        main()

        mock_module.exit_json.assert_called_once_with(changed=False)
