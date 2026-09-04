# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_export module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock, patch

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

from plugins.modules.purefa_export import (
    create_export,
    delete_export,
)


class TestCreateExport:
    """Tests for create_export function"""

    def test_create_export_no_policy(self):
        """Test create_export when no policy is provided"""
        mock_module = Mock()
        mock_module.params = {
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": None,
            "smb_policy": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.42"

        create_export(mock_module, mock_array)

        mock_module.fail_json.assert_called_once_with(
            msg="At least one policy must be provided"
        )


class TestDeleteExport:
    """Tests for delete_export function"""

    def test_delete_export_no_policy(self):
        """Test delete_export when no policy is provided"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": None,
            "smb_policy": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.42"

        delete_export(mock_module, mock_array)

        mock_module.fail_json.assert_called_once_with(
            msg="At least one policy must be provided"
        )

    @patch("plugins.modules.purefa_export.check_response")
    @patch("plugins.modules.purefa_export.delete_with_context")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_delete_export_nfs_policy_success(
        self, mock_get_with_context, mock_delete_with_context, mock_check_response
    ):
        """Test delete_export with NFS policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        mock_delete_with_context.return_value = Mock(status_code=200)

        delete_export(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_export.get_with_context")
    def test_delete_export_check_mode(self, mock_get_with_context):
        """Test delete_export in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": None,
            "context": "",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_export(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_export.get_with_context")
    def test_delete_export_policy_not_exists(self, mock_get_with_context):
        """Test delete_export when policy doesn't exist"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=400)

        delete_export(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_export.check_response")
    @patch("plugins.modules.purefa_export.delete_with_context")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_delete_export_smb_policy_success(
        self, mock_get_with_context, mock_delete_with_context, mock_check_response
    ):
        """Test delete_export with SMB policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": None,
            "smb_policy": "smb_policy1",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        mock_delete_with_context.return_value = Mock(status_code=200)

        delete_export(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateExportExtended:
    """Additional tests for create_export function"""

    @patch("plugins.modules.purefa_export.check_response")
    @patch("plugins.modules.purefa_export.post_with_context")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_create_export_nfs_policy_success(
        self, mock_get_with_context, mock_post_with_context, mock_check_response
    ):
        """Test create_export with NFS policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        # First call: get_policies_nfs (200), second call: get_directory_exports (400)
        mock_get_with_context.side_effect = [
            Mock(status_code=200),
            Mock(status_code=400),
        ]
        mock_post_with_context.return_value = Mock(status_code=200)

        create_export(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_export.check_response")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_create_export_check_mode(self, mock_get_with_context, mock_check_response):
        """Test create_export in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": None,
            "context": "",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        # First call: get_policies_nfs (200), second call: get_directory_exports (400)
        mock_get_with_context.side_effect = [
            Mock(status_code=200),
            Mock(status_code=400),
        ]

        create_export(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_export.check_response")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_create_export_already_exists(
        self, mock_get_with_context, mock_check_response
    ):
        """Test create_export when export already exists"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        # First call: get_policies_nfs (200), second call: get_directory_exports (200)
        mock_get_with_context.side_effect = [
            Mock(status_code=200),
            Mock(status_code=200),
        ]

        create_export(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_export.check_response")
    @patch("plugins.modules.purefa_export.post_with_context")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_create_export_smb_policy_success(
        self, mock_get_with_context, mock_post_with_context, mock_check_response
    ):
        """Test create_export with SMB policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": None,
            "smb_policy": "smb_policy1",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        # First call: get_policies_smb (200), second call: get_directory_exports (400)
        mock_get_with_context.side_effect = [
            Mock(status_code=200),
            Mock(status_code=400),
        ]
        mock_post_with_context.return_value = Mock(status_code=200)

        create_export(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_export.check_response")
    @patch("plugins.modules.purefa_export.post_with_context")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_create_export_both_policies(
        self, mock_get_with_context, mock_post_with_context, mock_check_response
    ):
        """Test create_export with both NFS and SMB policies"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": "smb_policy1",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        # get_policies_nfs(200), get_dir_exports(400), get_policies_smb(200), get_dir_exports(400)
        mock_get_with_context.side_effect = [
            Mock(status_code=200),
            Mock(status_code=400),
            Mock(status_code=200),
            Mock(status_code=400),
        ]
        mock_post_with_context.return_value = Mock(status_code=200)

        create_export(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_export.check_response")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_create_export_smb_already_exists(
        self, mock_get_with_context, mock_check_response
    ):
        """Test create_export when SMB export already exists"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": None,
            "smb_policy": "smb_policy1",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        # get_policies_smb(200), get_directory_exports(200) - already exists
        mock_get_with_context.side_effect = [
            Mock(status_code=200),
            Mock(status_code=200),
        ]

        create_export(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestDeleteExportExtended:
    """Extended tests for delete_export function"""

    @patch("plugins.modules.purefa_export.check_response")
    @patch("plugins.modules.purefa_export.delete_with_context")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_delete_export_both_policies(
        self, mock_get_with_context, mock_delete_with_context, mock_check_response
    ):
        """Test delete_export with both NFS and SMB policies"""
        mock_module = Mock()
        mock_module.params = {
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": "smb_policy1",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        mock_delete_with_context.return_value = Mock(status_code=200)

        delete_export(mock_module, mock_array)

        # delete_with_context called once with all policies in a single call
        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Tests for main function"""

    @patch("plugins.modules.purefa_export.AnsibleModule")
    @patch("plugins.modules.purefa_export.get_array")
    @patch("plugins.modules.purefa_export.get_with_context")
    @patch("plugins.modules.purefa_export.create_export")
    def test_main_create_export(
        self, mock_create_export, mock_get_with_context, mock_get_array, mock_ansible
    ):
        """Test main function calls create_export when state is present"""
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": None,
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.42"
        mock_get_array.return_value = mock_array
        mock_get_with_context.return_value = Mock(status_code=400)

        import plugins.modules.purefa_export as export_module

        original_has = export_module.HAS_PURESTORAGE
        export_module.HAS_PURESTORAGE = True

        try:
            export_module.main()
            mock_create_export.assert_called_once_with(mock_module, mock_array)
        finally:
            export_module.HAS_PURESTORAGE = original_has

    @patch("plugins.modules.purefa_export.AnsibleModule")
    @patch("plugins.modules.purefa_export.get_array")
    @patch("plugins.modules.purefa_export.get_with_context")
    @patch("plugins.modules.purefa_export.delete_export")
    def test_main_delete_export(
        self, mock_delete_export, mock_get_with_context, mock_get_array, mock_ansible
    ):
        """Test main function calls delete_export when state is absent"""
        mock_module = Mock()
        mock_module.params = {
            "state": "absent",
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": None,
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.42"
        mock_get_array.return_value = mock_array
        mock_get_with_context.return_value = Mock(status_code=200)

        import plugins.modules.purefa_export as export_module

        original_has = export_module.HAS_PURESTORAGE
        export_module.HAS_PURESTORAGE = True

        try:
            export_module.main()
            mock_delete_export.assert_called_once_with(mock_module, mock_array)
        finally:
            export_module.HAS_PURESTORAGE = original_has

    @patch("plugins.modules.purefa_export.AnsibleModule")
    @patch("plugins.modules.purefa_export.get_array")
    @patch("plugins.modules.purefa_export.get_with_context")
    def test_main_absent_not_exists(
        self, mock_get_with_context, mock_get_array, mock_ansible
    ):
        """Test main function exits unchanged when absent and doesn't exist"""
        mock_module = Mock()
        mock_module.params = {
            "state": "absent",
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": "nfs_policy1",
            "smb_policy": None,
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.42"
        mock_get_array.return_value = mock_array
        mock_get_with_context.return_value = Mock(status_code=400)

        import plugins.modules.purefa_export as export_module

        original_has = export_module.HAS_PURESTORAGE
        export_module.HAS_PURESTORAGE = True

        try:
            export_module.main()
            mock_module.exit_json.assert_called_with(changed=False)
        finally:
            export_module.HAS_PURESTORAGE = original_has

    @patch("plugins.modules.purefa_export.AnsibleModule")
    @patch("plugins.modules.purefa_export.get_array")
    def test_main_missing_purestorage(self, mock_get_array, mock_ansible):
        """Test main function fails when pypureclient is missing"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": None,
            "smb_policy": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.42"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_export as export_module

        original_has = export_module.HAS_PURESTORAGE
        export_module.HAS_PURESTORAGE = False

        try:
            with pytest.raises(SystemExit):
                export_module.main()
            mock_module.fail_json.assert_called_once()
        finally:
            export_module.HAS_PURESTORAGE = original_has

    @patch("plugins.modules.purefa_export.AnsibleModule")
    @patch("plugins.modules.purefa_export.get_array")
    def test_main_api_version_too_low(self, mock_get_array, mock_ansible):
        """Test main function fails when API version is too low"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "export1",
            "filesystem": "fs1",
            "directory": "dir1",
            "nfs_policy": None,
            "smb_policy": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "1.0"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_export as export_module

        original_has = export_module.HAS_PURESTORAGE
        export_module.HAS_PURESTORAGE = True

        try:
            with pytest.raises(SystemExit):
                export_module.main()
            mock_module.fail_json.assert_called_once()
        finally:
            export_module.HAS_PURESTORAGE = original_has
