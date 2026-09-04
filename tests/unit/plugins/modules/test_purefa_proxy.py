# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_proxy module."""

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

from plugins.modules.purefa_proxy import main, delete_proxy, create_proxy


class TestDeleteProxy:
    """Test cases for delete_proxy function"""

    @patch("plugins.modules.purefa_proxy.check_response")
    def test_delete_proxy_success(self, mock_check_response):
        """Test successful proxy deletion"""
        mock_module = Mock()
        mock_module.check_mode = False

        mock_array = Mock()
        mock_support = Mock()
        mock_support.proxy = "https://proxy.example.com:8080"
        mock_support_response = Mock()
        mock_support_response.items = [mock_support]
        mock_array.get_support.return_value = mock_support_response
        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_array.patch_support.return_value = mock_patch_response

        delete_proxy(mock_module, mock_array)

        mock_array.patch_support.assert_called_once()
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_proxy.check_response")
    def test_delete_proxy_no_proxy(self, mock_check_response):
        """Test delete when no proxy is set"""
        mock_module = Mock()
        mock_module.check_mode = False

        mock_array = Mock()
        mock_support = Mock()
        mock_support.proxy = ""
        mock_support_response = Mock()
        mock_support_response.items = [mock_support]
        mock_array.get_support.return_value = mock_support_response

        delete_proxy(mock_module, mock_array)

        mock_array.patch_support.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestCreateProxy:
    """Test cases for create_proxy function"""

    @patch("plugins.modules.purefa_proxy.check_response")
    def test_create_proxy_success(self, mock_check_response):
        """Test successful proxy creation"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "protocol": "https",
            "host": "proxy.example.com",
            "port": 8080,
        }

        mock_array = Mock()
        mock_support = Mock()
        mock_support.proxy = ""
        mock_support_response = Mock()
        mock_support_response.items = [mock_support]
        mock_array.get_support.return_value = mock_support_response
        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_array.patch_support.return_value = mock_patch_response

        create_proxy(mock_module, mock_array)

        mock_array.patch_support.assert_called_once()
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_proxy_no_change(self):
        """Test create when proxy already matches"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "protocol": "https",
            "host": "proxy.example.com",
            "port": 8080,
        }

        mock_array = Mock()
        mock_support = Mock()
        mock_support.proxy = "https://proxy.example.com:8080"
        mock_support_response = Mock()
        mock_support_response.items = [mock_support]
        mock_array.get_support.return_value = mock_support_response

        create_proxy(mock_module, mock_array)

        mock_array.patch_support.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_proxy.get_array")
    @patch("plugins.modules.purefa_proxy.AnsibleModule")
    @patch("plugins.modules.purefa_proxy.HAS_PURESTORAGE", False)
    def test_main_missing_sdk(self, mock_ansible_module, mock_get_array):
        """Test main when pypureclient SDK is missing"""
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "protocol": "https",
            "host": "proxy.example.com",
            "port": 8080,
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
