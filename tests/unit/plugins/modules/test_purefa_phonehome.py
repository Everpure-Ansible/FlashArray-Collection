# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_phonehome module."""

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
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    MagicMock()
)
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()

from plugins.modules.purefa_phonehome import main


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_phonehome.get_array")
    @patch("plugins.modules.purefa_phonehome.AnsibleModule")
    @patch("plugins.modules.purefa_phonehome.HAS_PURESTORAGE", False)
    def test_main_missing_sdk(self, mock_ansible_module, mock_get_array):
        """Test main when pypureclient SDK is missing"""
        mock_module = Mock()
        mock_module.params = {"state": "present", "excludes": None}
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "py-pure-client sdk is required" in call_args["msg"]

    @patch("plugins.modules.purefa_phonehome.check_response")
    @patch("plugins.modules.purefa_phonehome.LooseVersion")
    @patch("plugins.modules.purefa_phonehome.get_array")
    @patch("plugins.modules.purefa_phonehome.AnsibleModule")
    @patch("plugins.modules.purefa_phonehome.HAS_PURESTORAGE", True)
    def test_enable_phonehome(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_check_response,
    ):
        """Test enabling phonehome"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"state": "present", "excludes": None}
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_support = Mock()
        mock_support.phonehome_enabled = False
        mock_support_response = Mock()
        mock_support_response.items = [mock_support]
        mock_array.get_support.return_value = mock_support_response
        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_array.patch_support.return_value = mock_patch_response
        mock_get_array.return_value = mock_array
        mock_loose_version.side_effect = float

        main()

        mock_array.patch_support.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_phonehome.check_response")
    @patch("plugins.modules.purefa_phonehome.LooseVersion")
    @patch("plugins.modules.purefa_phonehome.get_array")
    @patch("plugins.modules.purefa_phonehome.AnsibleModule")
    @patch("plugins.modules.purefa_phonehome.HAS_PURESTORAGE", True)
    def test_disable_phonehome(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_check_response,
    ):
        """Test disabling phonehome"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"state": "absent", "excludes": None}
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_support = Mock()
        mock_support.phonehome_enabled = True
        mock_support_response = Mock()
        mock_support_response.items = [mock_support]
        mock_array.get_support.return_value = mock_support_response
        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_array.patch_support.return_value = mock_patch_response
        mock_get_array.return_value = mock_array
        mock_loose_version.side_effect = float

        main()

        mock_array.patch_support.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_phonehome.LooseVersion")
    @patch("plugins.modules.purefa_phonehome.get_array")
    @patch("plugins.modules.purefa_phonehome.AnsibleModule")
    @patch("plugins.modules.purefa_phonehome.HAS_PURESTORAGE", True)
    def test_no_change_needed(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test when phonehome state already matches"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"state": "present", "excludes": None}
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_support = Mock()
        mock_support.phonehome_enabled = True  # Already enabled
        mock_support_response = Mock()
        mock_support_response.items = [mock_support]
        mock_array.get_support.return_value = mock_support_response
        mock_get_array.return_value = mock_array
        mock_loose_version.side_effect = float

        main()

        mock_array.patch_support.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)
