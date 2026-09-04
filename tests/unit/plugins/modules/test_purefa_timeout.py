# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_timeout module."""

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

from plugins.modules.purefa_timeout import main, set_timeout, disable_timeout


class TestSetTimeout:
    """Test cases for set_timeout function"""

    @patch("plugins.modules.purefa_timeout.check_response")
    @patch("plugins.modules.purefa_timeout.get_with_context")
    def test_set_timeout_success(self, mock_get_with_context, mock_check_response):
        """Test successful timeout setting"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"timeout": 1800000}  # 30 minutes in ms

        mock_array = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get_with_context.return_value = mock_response

        set_timeout(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_timeout.check_response")
    @patch("plugins.modules.purefa_timeout.get_with_context")
    def test_set_timeout_check_mode(self, mock_get_with_context, mock_check_response):
        """Test timeout setting in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"timeout": 1800000}

        mock_array = Mock()

        set_timeout(mock_module, mock_array)

        mock_get_with_context.assert_not_called()
        mock_check_response.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDisableTimeout:
    """Test cases for disable_timeout function"""

    @patch("plugins.modules.purefa_timeout.check_response")
    @patch("plugins.modules.purefa_timeout.get_with_context")
    def test_disable_timeout_success(self, mock_get_with_context, mock_check_response):
        """Test successful timeout disable"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"timeout": 0}

        mock_array = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get_with_context.return_value = mock_response

        disable_timeout(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_timeout.check_response")
    @patch("plugins.modules.purefa_timeout.get_with_context")
    def test_disable_timeout_check_mode(
        self, mock_get_with_context, mock_check_response
    ):
        """Test timeout disable in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"timeout": 0}

        mock_array = Mock()

        disable_timeout(mock_module, mock_array)

        mock_get_with_context.assert_not_called()
        mock_check_response.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_timeout.get_with_context")
    @patch("plugins.modules.purefa_timeout.get_array")
    @patch("plugins.modules.purefa_timeout.AnsibleModule")
    @patch("plugins.modules.purefa_timeout.HAS_PURESTORAGE", False)
    def test_main_missing_sdk(
        self, mock_ansible_module, mock_get_array, mock_get_with_context
    ):
        """Test main when pypureclient SDK is missing"""
        mock_module = Mock()
        mock_module.params = {"timeout": 30, "state": "present", "context": ""}
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "py-pure-client sdk is required" in call_args["msg"]

    @patch("plugins.modules.purefa_timeout.get_with_context")
    @patch("plugins.modules.purefa_timeout.get_array")
    @patch("plugins.modules.purefa_timeout.AnsibleModule")
    @patch("plugins.modules.purefa_timeout.HAS_PURESTORAGE", True)
    def test_main_timeout_unchanged(
        self, mock_ansible_module, mock_get_array, mock_get_with_context
    ):
        """Test main when timeout is already set"""
        mock_module = Mock()
        mock_module.params = {"timeout": 30, "state": "present", "context": ""}
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        mock_current = Mock()
        mock_current.idle_timeout = (
            1800000  # 30 minutes in ms (matches after conversion)
        )
        mock_response = Mock()
        mock_response.items = [mock_current]
        mock_get_with_context.return_value = mock_response

        main()

        mock_module.exit_json.assert_called_with(changed=False)
