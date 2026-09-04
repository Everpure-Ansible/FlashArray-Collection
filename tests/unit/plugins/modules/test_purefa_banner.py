# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_banner module."""

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

from plugins.modules.purefa_banner import main, set_banner, delete_banner


class TestSetBanner:
    """Test cases for set_banner function"""

    @patch("plugins.modules.purefa_banner.check_response")
    @patch("plugins.modules.purefa_banner.get_with_context")
    def test_set_banner_success(self, mock_get_with_context, mock_check_response):
        """Test successful banner setting"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"banner": "Welcome to Pure Storage"}

        mock_array = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get_with_context.return_value = mock_response

        set_banner(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_banner.check_response")
    @patch("plugins.modules.purefa_banner.get_with_context")
    def test_set_banner_check_mode(self, mock_get_with_context, mock_check_response):
        """Test banner setting in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"banner": "Welcome to Pure Storage"}

        mock_array = Mock()

        set_banner(mock_module, mock_array)

        mock_get_with_context.assert_not_called()
        mock_check_response.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_set_banner_empty_banner(self):
        """Test set_banner with empty banner fails"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"banner": ""}
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()

        try:
            set_banner(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "Invalid MOTD banner given" in call_args["msg"]


class TestDeleteBanner:
    """Test cases for delete_banner function"""

    @patch("plugins.modules.purefa_banner.check_response")
    @patch("plugins.modules.purefa_banner.get_with_context")
    def test_delete_banner_success(self, mock_get_with_context, mock_check_response):
        """Test successful banner deletion"""
        mock_module = Mock()
        mock_module.check_mode = False

        mock_array = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get_with_context.return_value = mock_response

        delete_banner(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_banner.check_response")
    @patch("plugins.modules.purefa_banner.get_with_context")
    def test_delete_banner_check_mode(self, mock_get_with_context, mock_check_response):
        """Test banner deletion in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True

        mock_array = Mock()

        delete_banner(mock_module, mock_array)

        mock_get_with_context.assert_not_called()
        mock_check_response.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_banner.get_array")
    @patch("plugins.modules.purefa_banner.AnsibleModule")
    @patch("plugins.modules.purefa_banner.HAS_PURESTORAGE", False)
    def test_main_missing_sdk(self, mock_ansible_module, mock_get_array):
        """Test main when pypureclient SDK is missing"""
        mock_module = Mock()
        mock_module.params = {
            "banner": "Welcome",
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
        assert "py-pure-client sdk is required" in call_args["msg"]
