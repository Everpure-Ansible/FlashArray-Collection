# Copyright: (c) 2026, Pure Storage Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_eula module."""

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

from plugins.modules.purefa_eula import main, set_eula


class TestSetEula:
    """Test cases for set_eula function"""

    def test_set_eula_success(self):
        """Test successful EULA signing"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "company": "ACME Storage, Inc.",
            "name": "Fred Bloggs",
            "title": "Storage Manager",
        }

        mock_array = Mock()
        mock_current_eula = Mock(spec=[])  # No signature.accepted attribute
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_current_eula]
        mock_array.get_arrays_eula.return_value = mock_response

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_array.patch_arrays_eula.return_value = mock_patch_response

        set_eula(mock_module, mock_array)

        mock_array.patch_arrays_eula.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_set_eula_check_mode(self):
        """Test EULA signing in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "company": "ACME Storage, Inc.",
            "name": "Fred Bloggs",
            "title": "Storage Manager",
        }

        mock_array = Mock()
        mock_current_eula = Mock(spec=[])  # No signature.accepted attribute
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_current_eula]
        mock_array.get_arrays_eula.return_value = mock_response

        set_eula(mock_module, mock_array)

        # Should not call patch in check mode
        mock_array.patch_arrays_eula.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_set_eula_already_signed(self):
        """Test that an already-signed EULA is not signed again"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "company": "ACME Storage, Inc.",
            "name": "Fred Bloggs",
            "title": "Storage Manager",
        }

        mock_array = Mock()
        mock_signature = Mock(spec=["accepted"])
        mock_signature.accepted = 1687000000000  # ms since epoch
        mock_current_eula = Mock(spec=["signature"])
        mock_current_eula.signature = mock_signature
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_current_eula]
        mock_array.get_arrays_eula.return_value = mock_response

        set_eula(mock_module, mock_array)

        mock_array.patch_arrays_eula.assert_not_called()
        mock_module.warn.assert_called_once_with("EULA already signed")
        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_set_eula_signature_present_but_unaccepted(self):
        """Test signing when a signature object exists but accepted is null"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "company": "ACME Storage, Inc.",
            "name": "Fred Bloggs",
            "title": "Storage Manager",
        }

        mock_array = Mock()
        mock_signature = Mock(spec=["accepted"])
        mock_signature.accepted = None
        mock_current_eula = Mock(spec=["signature"])
        mock_current_eula.signature = mock_signature
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_current_eula]
        mock_array.get_arrays_eula.return_value = mock_response

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_array.patch_arrays_eula.return_value = mock_patch_response

        set_eula(mock_module, mock_array)

        mock_array.patch_arrays_eula.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_get_eula_failure(self):
        """Test when getting EULA fails"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "company": "ACME Storage, Inc.",
            "name": "Fred Bloggs",
            "title": "Storage Manager",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()
        mock_error = Mock()
        mock_error.message = "API Error"
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.errors = [mock_error]
        mock_array.get_arrays_eula.return_value = mock_response

        try:
            set_eula(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "Failed to get current EULA" in call_args["msg"]


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_eula.get_array")
    @patch("plugins.modules.purefa_eula.AnsibleModule")
    @patch("plugins.modules.purefa_eula.HAS_PURESTORAGE", False)
    def test_main_missing_sdk(self, mock_ansible_module, mock_get_array):
        """Test main when pypureclient SDK is missing"""
        mock_module = Mock()
        mock_module.params = {
            "company": "ACME Storage, Inc.",
            "name": "Fred Bloggs",
            "title": "Storage Manager",
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

    @patch("plugins.modules.purefa_eula.set_eula")
    @patch("plugins.modules.purefa_eula.LooseVersion")
    @patch("plugins.modules.purefa_eula.get_array")
    @patch("plugins.modules.purefa_eula.AnsibleModule")
    @patch("plugins.modules.purefa_eula.HAS_PURESTORAGE", True)
    def test_main_calls_set_eula(
        self, mock_ansible_module, mock_get_array, mock_loose_version, mock_set_eula
    ):
        """Test main function calls set_eula"""
        mock_module = Mock()
        mock_module.params = {
            "company": "ACME Storage, Inc.",
            "name": "Fred Bloggs",
            "title": "Storage Manager",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array
        mock_loose_version.side_effect = float

        main()

        mock_set_eula.assert_called_once_with(mock_module, mock_array)
