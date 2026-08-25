# Copyright: (c) 2026, Pure Storage Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_policy module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

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
# Create a mock version module with real LooseVersion
mock_version_module = MagicMock()
from packaging.version import Version as LooseVersion

mock_version_module.LooseVersion = LooseVersion
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    mock_version_module
)


# Create proper helper functions that work with mocked arrays
def mock_get_with_context(client, method_name, context_version, module, **kwargs):
    """Mock helper that properly calls getattr on the client."""
    api_version = client.get_rest_version()
    method = getattr(client, method_name)
    if LooseVersion(context_version) <= LooseVersion(api_version) and module.params.get(
        "context"
    ):
        kwargs["context_names"] = [module.params["context"]]
    return method(**kwargs)


def mock_check_response(response, module, operation="Operation"):
    """Mock helper that checks API responses."""
    if hasattr(response, "status_code") and response.status_code != 200:
        error_detail = (
            response.errors[0].message
            if hasattr(response, "errors") and response.errors
            else "Unknown error"
        )
        module.fail_json(
            msg=f"{operation} failed. Error: {error_detail}",
            status_code=response.status_code,
            changed=False,
        )


# Create api_helpers mock with real implementations
mock_api_helpers = MagicMock()
mock_api_helpers.get_with_context = mock_get_with_context
mock_api_helpers.post_with_context = mock_get_with_context
mock_api_helpers.patch_with_context = mock_get_with_context
mock_api_helpers.delete_with_context = mock_get_with_context
mock_api_helpers.check_response = mock_check_response

sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = mock_api_helpers
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.error_handlers"
] = MagicMock()

from plugins.modules.purefa_policy import (
    delete_policy,
    rename_policy,
    create_policy,
    update_policy,
    main,
)


class TestDeletePolicy:
    """Tests for delete_policy function"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_policy_check_mode(self, mock_lv):
        """Test delete_policy in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "policy1",
            "policy": "nfs",
            "client": None,
            "context": "",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        delete_policy(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_nfs_policy_success(self, mock_lv):
        """Test successful deletion of NFS policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "client": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_nfs.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_nfs.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_nfs_policy_failure(self, mock_lv):
        """Test failure to delete NFS policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "client": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_res = Mock()
        mock_res.status_code = 400
        mock_res.errors = [Mock(message="Policy in use")]
        mock_array.delete_policies_nfs.return_value = mock_res

        delete_policy(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_smb_policy_success(self, mock_lv):
        """Test successful deletion of SMB policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "client": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_smb.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_smb.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_policy_success(self, mock_lv):
        """Test successful deletion of Snapshot policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "snap_client_name": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_snapshot.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_quota_policy_success(self, mock_lv):
        """Test successful deletion of Quota policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy1",
            "policy": "quota",
            "context": "",
            "quota_limit": None,
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_quota.return_value.status_code = 200
        # Mock members and rules as empty lists
        mock_array.get_policies_quota_members.return_value.items = []
        mock_array.get_policies_quota_rules.return_value.items = []

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_quota.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_autodir_policy_success(self, mock_lv):
        """Test successful deletion of Autodir policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy1",
            "policy": "autodir",
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_autodir.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_autodir.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_password_policy_warns(self, mock_lv):
        """Test that deleting password policy shows warning"""
        mock_module = Mock()
        mock_module.params = {
            "name": "password_policy1",
            "policy": "password",
            "context": "",
            "quota_limit": None,
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Password policy also falls through to quota branch due to code structure
        mock_array.get_policies_quota_members.return_value.items = []
        mock_array.get_policies_quota_rules.return_value.items = []
        mock_array.delete_policies_quota.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_module.warn.assert_called_once()

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_nfs_policy_with_client_rule(self, mock_lv):
        """Test deletion of NFS policy client rule"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "client": "192.168.1.0/24",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock existing rule - include status_code for get_with_context
        mock_rule = Mock()
        mock_rule.client = "192.168.1.0/24"
        mock_rule.name = "rule1"
        mock_array.get_policies_nfs_client_rules.return_value.items = [mock_rule]
        mock_array.get_policies_nfs_client_rules.return_value.status_code = 200
        mock_array.delete_policies_nfs_client_rules.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_nfs_client_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_smb_policy_with_client_rule(self, mock_lv):
        """Test deletion of SMB policy client rule"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "client": "client1",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock existing rule - include status_code for get_with_context
        mock_rule = Mock()
        mock_rule.client = "client1"
        mock_rule.name = "rule1"
        mock_array.get_policies_smb_client_rules.return_value.items = [mock_rule]
        mock_array.get_policies_smb_client_rules.return_value.status_code = 200
        mock_array.delete_policies_smb_client_rules.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_smb_client_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenamePolicy:
    """Tests for rename_policy function"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_rename_nfs_policy_check_mode(self, mock_policy_patch, mock_lv):
        """Test rename_policy in check mode for NFS policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_policy",
            "rename": "new_policy",
            "policy": "nfs",
            "context": "",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # status_code == 200 means target name is available (can proceed)
        mock_array.get_policies.return_value.status_code = 200

        rename_policy(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_rename_nfs_policy_success(self, mock_policy_patch, mock_lv):
        """Test successful NFS policy rename"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_policy",
            "rename": "new_policy",
            "policy": "nfs",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # status_code == 200 means target name is available (can proceed)
        mock_array.get_policies.return_value.status_code = 200
        mock_array.patch_policies_nfs.return_value.status_code = 200

        rename_policy(mock_module, mock_array)

        mock_array.patch_policies_nfs.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_rename_smb_policy_success(self, mock_policy_patch, mock_lv):
        """Test successful SMB policy rename"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_smb_policy",
            "rename": "new_smb_policy",
            "policy": "smb",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_policies.return_value.status_code = 200
        mock_array.patch_policies_smb.return_value.status_code = 200

        rename_policy(mock_module, mock_array)

        mock_array.patch_policies_smb.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_rename_snapshot_policy_success(self, mock_policy_patch, mock_lv):
        """Test successful snapshot policy rename"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_snap_policy",
            "rename": "new_snap_policy",
            "policy": "snapshot",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_policies.return_value.status_code = 200
        mock_array.patch_policies_snapshot.return_value.status_code = 200

        rename_policy(mock_module, mock_array)

        mock_array.patch_policies_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_rename_quota_policy_success(self, mock_policy_patch, mock_lv):
        """Test successful quota policy rename"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_quota_policy",
            "rename": "new_quota_policy",
            "policy": "quota",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_policies.return_value.status_code = 200
        mock_array.patch_policies_quota.return_value.status_code = 200

        rename_policy(mock_module, mock_array)

        mock_array.patch_policies_quota.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_rename_password_policy_fails(self, mock_policy_patch, mock_lv):
        """Test that password policy rename fails with message"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_password_policy",
            "rename": "new_password_policy",
            "policy": "password",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # status_code == 200 means target doesn't exist (can proceed)
        mock_array.get_policies.return_value.status_code = 200

        rename_policy(mock_module, mock_array)

        # Should fail because password policy rename is not supported
        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_rename_policy_target_exists(self, mock_policy_patch, mock_lv):
        """Test rename fails when target policy already exists"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_policy",
            "rename": "existing_policy",
            "policy": "nfs",
            "context": "",
        }
        mock_module.check_mode = False
        # fail_json should raise SystemExit to stop execution
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # status_code == 200 means target policy exists (fail)
        mock_array.get_policies.return_value.status_code = 200

        with pytest.raises(SystemExit):
            rename_policy(mock_module, mock_array)

        # Should fail because target policy already exists
        mock_module.fail_json.assert_called()


class TestCreatePolicy:
    """Tests for create_policy function"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyNfsPatch")
    def test_create_nfs_policy_check_mode(self, mock_nfs_patch, mock_post, mock_lv):
        """Test create_policy in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "new_nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": None,
            "context": "",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        create_policy(mock_module, mock_array, False)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyNfsPatch")
    def test_create_nfs_policy_success(self, mock_nfs_patch, mock_post, mock_lv):
        """Test successful NFS policy creation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "new_nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": None,
            "user_mapping": True,
            "context": "",
            "security": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_nfs.return_value.status_code = 200
        mock_array.patch_policies_nfs.return_value.status_code = 200

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_nfs.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicySmbPatch")
    def test_create_smb_policy_success(self, mock_smb_patch, mock_post, mock_lv):
        """Test successful SMB policy creation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "new_smb_policy",
            "policy": "smb",
            "enabled": True,
            "client": None,
            "smb_anon_allowed": False,
            "smb_encrypt": False,
            "access_based_enumeration": False,
            "continuous_availability": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.43"
        mock_array.post_policies_smb.return_value.status_code = 200
        mock_array.patch_policies_smb.return_value.status_code = 200

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_smb.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_snapshot_policy_success(self, mock_post, mock_lv):
        """Test successful Snapshot policy creation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "new_snap_policy",
            "policy": "snapshot",
            "enabled": True,
            "snap_client_name": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_snapshot.return_value.status_code = 200

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_quota_policy_success(self, mock_post, mock_lv):
        """Test successful Quota policy creation (no quota_limit)"""
        mock_module = Mock()
        mock_module.params = {
            "name": "new_quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_enforced": True,
            "quota_limit": None,
            "quota_notifications": "warning",
            "context": "",
            "ignore_usage": False,
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_quota.return_value.status_code = 200

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_quota.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_autodir_policy_success(self, mock_post, mock_lv):
        """Test successful Autodir policy creation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "new_autodir_policy",
            "policy": "autodir",
            "enabled": True,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_autodir.return_value.status_code = 200

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_autodir.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_nfs_policy_failure(self, mock_post, mock_lv):
        """Test NFS policy creation failure"""
        mock_module = Mock()
        mock_module.params = {
            "name": "new_nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_res = Mock()
        mock_res.status_code = 400
        mock_res.errors = [Mock(message="Creation failed")]
        mock_array.post_policies_nfs.return_value = mock_res

        create_policy(mock_module, mock_array, False)

        mock_module.fail_json.assert_called_once()


class TestUpdatePolicy:
    """Tests for update_policy function"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_nfs_policy_check_mode(self, mock_lv):
        """Test update_policy for NFS in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "nfs_version": None,
            "user_mapping": None,
            "client": None,
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current policy
        mock_policy = Mock()
        mock_policy.enabled = False  # Different from module.params["enabled"]
        mock_policy.nfs_version = []
        mock_array.get_policies_nfs.return_value.items = [mock_policy]
        mock_array.get_policies_nfs.return_value.status_code = 200

        # Mock items for user_mapping
        mock_user_map_item = Mock()
        mock_user_map_item.user_mapping_enabled = False
        mock_array.get_policies_nfs.return_value.items = [mock_user_map_item]

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_update_nfs_policy_enable(self, mock_patch, mock_lv):
        """Test enabling NFS policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "nfs_version": None,
            "user_mapping": None,
            "client": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current policy
        mock_policy = Mock()
        mock_policy.enabled = False  # Different from module.params["enabled"]
        mock_policy.nfs_version = []
        mock_array.get_policies_nfs.return_value.items = [mock_policy]
        mock_array.get_policies_nfs.return_value.status_code = 200

        # Mock user_mapping item
        mock_user_map_item = Mock()
        mock_user_map_item.user_mapping_enabled = False
        mock_array.get_policies_nfs.return_value.items = [mock_user_map_item]

        # Mock patch response
        mock_array.patch_policies_nfs.return_value.status_code = 200

        update_policy(mock_module, mock_array, "2.38", False)

        mock_array.patch_policies_nfs.assert_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_smb_policy_check_mode(self, mock_lv):
        """Test update_policy for SMB in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "enabled": True,
            "context": "",
            "client": None,
            "smb_anon_allowed": None,
            "smb_continuous_avail": None,
            "smb_access_based_enum": None,
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current policy
        mock_policy = Mock()
        mock_policy.enabled = False  # Different
        mock_array.get_policies_smb.return_value.items = [mock_policy]
        mock_array.get_policies_smb.return_value.status_code = 200

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_snapshot_policy_check_mode(self, mock_lv):
        """Test update_policy for snapshot in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "directory": None,
            "snap_at": None,
            "snap_every": None,
            "snap_keep_for": None,
            "snap_client_name": None,
            "snap_suffix": None,
            "snap_timezone": None,
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current policy
        mock_policy = Mock()
        mock_policy.enabled = False  # Different
        mock_array.get_policies_snapshot.return_value.items = [mock_policy]
        mock_array.get_policies_snapshot.return_value.status_code = 200

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_quota_policy_check_mode(self, mock_lv):
        """Test update_policy for quota in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy1",
            "policy": "quota",
            "enabled": True,
            "context": "",
            "quota_enforced": True,
            "quota_limit": None,
            "quota_notifications": "warning",
            "directory": None,
            "ignore_usage": False,
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current policy
        mock_policy = Mock()
        mock_policy.enabled = False  # Different
        mock_array.get_policies_quota.return_value.items = [mock_policy]
        mock_array.get_policies_quota.return_value.status_code = 200

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once()


class TestUpdatePolicySuccess:
    """Test cases for update_policy success paths"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_nfs_policy_success(self, mock_lv):
        """Test update_policy for NFS with actual changes"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "client": None,
            "nfs_access": None,
            "nfs_permission": None,
            "nfs_version": None,
            "user_mapping": False,
            "security": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current policy with different enabled state
        mock_policy = Mock()
        mock_policy.enabled = False
        mock_policy.user_mapping_enabled = False
        mock_policy.security = None
        mock_policy.nfs_version = None
        mock_array.get_policies_nfs.return_value.items = [mock_policy]
        mock_array.get_policies_nfs.return_value.status_code = 200
        mock_array.patch_policies_nfs.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_array.patch_policies_nfs.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_smb_policy_success(self, mock_lv):
        """Test update_policy for SMB with actual changes"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "enabled": True,
            "context": "",
            "client": None,
            "smb_access": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current policy with different enabled state
        mock_policy = Mock()
        mock_policy.enabled = False
        mock_array.get_policies_smb.return_value.items = [mock_policy]
        mock_array.get_policies_smb.return_value.status_code = 200
        mock_array.patch_policies_smb.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_array.patch_policies_smb.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_snapshot_policy_success(self, mock_lv):
        """Test update_policy for snapshot with actual changes"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "snap_at": None,
            "snap_every": None,
            "snap_keep_for": None,
            "snap_client_name": None,
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current policy with different enabled state
        mock_policy = Mock()
        mock_policy.enabled = False
        mock_policy.rules = []
        mock_array.get_policies_snapshot.return_value.items = [mock_policy]
        mock_array.get_policies_snapshot.return_value.status_code = 200
        mock_array.patch_policies_snapshot.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_array.patch_policies_snapshot.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_quota_policy_success(self, mock_lv):
        """Test update_policy for quota with actual changes"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy1",
            "policy": "quota",
            "enabled": True,
            "context": "",
            "quota_enforced": True,
            "quota_limit": None,
            "quota_notifications": "warning",
            "directory": None,
            "ignore_usage": False,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current policy with different enabled state
        mock_policy = Mock()
        mock_policy.enabled = False
        mock_array.get_policies_quota.return_value.items = [mock_policy]
        mock_array.get_policies_quota.return_value.status_code = 200
        mock_array.patch_policies_quota.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_array.patch_policies_quota.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeletePolicySuccess:
    """Test cases for delete_policy success paths"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_nfs_policy_with_client_rule(self, mock_lv):
        """Test successful deletion of NFS client rule"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "client": "192.168.1.0/24",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock existing rule - include status_code for get_with_context
        mock_rule = Mock()
        mock_rule.client = "192.168.1.0/24"
        mock_rule.name = "rule1"
        mock_array.get_policies_nfs_client_rules.return_value.items = [mock_rule]
        mock_array.get_policies_nfs_client_rules.return_value.status_code = 200
        mock_array.delete_policies_nfs_client_rules.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_nfs_client_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_smb_policy_with_client_rule(self, mock_lv):
        """Test successful deletion of SMB client rule"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "client": "192.168.1.0/24",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock existing rule - include status_code for get_with_context
        mock_rule = Mock()
        mock_rule.client = "192.168.1.0/24"
        mock_rule.name = "smb_rule1"
        mock_array.get_policies_smb_client_rules.return_value.items = [mock_rule]
        mock_array.get_policies_smb_client_rules.return_value.status_code = 200
        mock_array.delete_policies_smb_client_rules.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_smb_client_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_autodir_policy_success(self, mock_lv):
        """Test successful deletion of autodir policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy1",
            "policy": "autodir",
            "context": "",
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_autodir.return_value.status_code = 200

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_autodir.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_nfs_policy_full(self, mock_lv):
        """Test successful full deletion of NFS policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "client": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_nfs.return_value = Mock(status_code=200)

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_nfs.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_smb_policy_full(self, mock_lv):
        """Test successful full deletion of SMB policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "client": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_smb.return_value = Mock(status_code=200)

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_smb.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_policy_full(self, mock_lv):
        """Test successful full deletion of snapshot policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "snap_client_name": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_snapshot.return_value = Mock(status_code=200)

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_quota_policy_success(self, mock_lv):
        """Test successful deletion of quota policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy1",
            "policy": "quota",
            "directory": None,
            "quota_limit": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock get_policies_quota_members to return empty list (no members)
        mock_array.get_policies_quota_members.return_value = Mock(items=[])
        mock_array.delete_policies_quota.return_value = Mock(status_code=200)

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_quota.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicySuccess:
    """Test cases for create_policy success paths"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_create_nfs_policy_basic(self, mock_lv):
        """Test successful creation of basic NFS policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "client": None,
            "user_mapping": False,
            "nfs_version": None,
            "security": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_nfs.return_value = Mock(status_code=200)
        mock_array.patch_policies_nfs.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_nfs.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_create_smb_policy_basic(self, mock_lv):
        """Test successful creation of basic SMB policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "enabled": True,
            "context": "",
            "client": None,
            "smb_access": None,
            "access_based_enumeration": False,
            "continuous_availability": False,
            "smb_anon_allowed": False,
            "smb_encrypt": False,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_smb.return_value = Mock(status_code=200)
        mock_array.patch_policies_smb.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_smb.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenamePolicySuccess:
    """Test cases for rename_policy success paths"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_rename_nfs_policy_success(self, mock_lv):
        """Test successful rename of NFS policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_nfs_policy",
            "rename": "new_nfs_policy",
            "policy": "nfs",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Target policy doesn't exist (404 error)
        mock_array.get_policies.return_value = Mock(status_code=404)
        mock_array.patch_policies_nfs.return_value = Mock(status_code=200)

        rename_policy(mock_module, mock_array)

        mock_array.patch_policies_nfs.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_rename_smb_policy_success(self, mock_lv):
        """Test successful rename of SMB policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_smb_policy",
            "rename": "new_smb_policy",
            "policy": "smb",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_policies.return_value = Mock(status_code=404)
        mock_array.patch_policies_smb.return_value = Mock(status_code=200)

        rename_policy(mock_module, mock_array)

        mock_array.patch_policies_smb.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_rename_snapshot_policy_success(self, mock_lv):
        """Test successful rename of snapshot policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_snap_policy",
            "rename": "new_snap_policy",
            "policy": "snapshot",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_policies.return_value = Mock(status_code=404)
        mock_array.patch_policies_snapshot.return_value = Mock(status_code=200)

        rename_policy(mock_module, mock_array)

        mock_array.patch_policies_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_rename_quota_policy_success(self, mock_lv):
        """Test successful rename of quota policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "old_quota_policy",
            "rename": "new_quota_policy",
            "policy": "quota",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_policies.return_value = Mock(status_code=404)
        mock_array.patch_policies_quota.return_value = Mock(status_code=200)

        rename_policy(mock_module, mock_array)

        mock_array.patch_policies_quota.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeletePolicyAutodir:
    """Test cases for delete_policy with autodir policy type"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_autodir_policy_success(self, mock_lv):
        """Test successful deletion of autodir policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy",
            "policy": "autodir",
            "client": None,
            "directory": None,
            "snap_client_name": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_autodir.return_value = Mock(status_code=200)

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_autodir.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_autodir_policy_older_api(self, mock_lv):
        """Test deletion of autodir policy with older API version"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy",
            "policy": "autodir",
            "client": None,
            "directory": None,
            "snap_client_name": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Older than CONTEXT_VERSION
        mock_array.delete_policies_autodir.return_value = Mock(status_code=200)

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_autodir.assert_called_once_with(
            names=["autodir_policy"]
        )
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeletePolicySnapshotExtended:
    """Extended test cases for delete_policy with snapshot policy"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_policy_success(self, mock_lv):
        """Test successful deletion of entire snapshot policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "client": None,
            "directory": None,
            "snap_client_name": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_policies_snapshot.return_value = Mock(status_code=200)

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_policy_with_rule(self, mock_lv):
        """Test deletion of snapshot rule from policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "client": None,
            "directory": None,
            "snap_client_name": "daily_snap",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_rule = Mock()
        mock_rule.client_name = "daily_snap"
        mock_rule.name = "rule1"
        # Include status_code for get_with_context
        mock_array.get_policies_snapshot_rules.return_value = Mock(
            items=[mock_rule], status_code=200
        )
        mock_array.delete_policies_snapshot_rules.return_value = Mock(status_code=200)

        delete_policy(mock_module, mock_array)

        mock_array.delete_policies_snapshot_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicyAutodir:
    """Test cases for create_policy with autodir policy type"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_autodir_policy_success(self, mock_policy_post, mock_lv):
        """Test successful creation of autodir policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy",
            "policy": "autodir",
            "enabled": True,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_autodir.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_autodir.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicyNfs:
    """Test cases for create_policy with NFS policy type"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_nfs_policy_basic(self, mock_policy_post, mock_lv):
        """Test basic NFS policy creation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": None,
            "user_mapping": True,
            "nfs_version": None,
            "security": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_nfs.return_value = Mock(status_code=200)
        mock_array.patch_policies_nfs.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_nfs.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_nfs_policy_check_mode(self, mock_policy_post, mock_lv):
        """Test NFS policy creation in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_nfs.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicySmb:
    """Test cases for create_policy with SMB policy type"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_smb_policy_basic(self, mock_policy_post, mock_lv):
        """Test basic SMB policy creation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy",
            "policy": "smb",
            "enabled": True,
            "smb_anon_allowed": False,
            "smb_encrypt": False,
            "access_based_enumeration": False,
            "continuous_availability": False,
            "client": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_smb.return_value = Mock(status_code=200)
        mock_array.patch_policies_smb.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_smb.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicySnapshot:
    """Test cases for create_policy with snapshot policy type"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_snapshot_policy_basic(self, mock_policy_post, mock_lv):
        """Test basic snapshot policy creation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "enabled": True,
            "snap_client_name": None,
            "snap_every": None,
            "snap_keep_for": None,
            "snap_at": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_snapshot.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicyQuota:
    """Test cases for create_policy with quota policy type"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_quota_policy_basic(self, mock_policy_post, mock_lv):
        """Test basic quota policy creation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_limit": None,
            "directory": None,
            "quota_enforced": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_quota.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_quota.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePolicyNfs:
    """Test cases for update_policy with NFS policy type"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyNfsPatch")
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_update_nfs_policy_enable_change(
        self, mock_policy_patch, mock_nfs_patch, mock_lv
    ):
        """Test updating NFS policy enabled state"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": False,
            "client": None,
            "user_mapping": True,
            "nfs_version": None,
            "security": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_current = Mock()
        mock_current.enabled = True
        mock_current.user_mapping_enabled = True
        mock_array.get_policies_nfs.return_value = Mock(
            status_code=200, items=[mock_current]
        )
        mock_array.patch_policies_nfs.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_array.patch_policies_nfs.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicyPassword:
    """Test cases for create_policy with password policy type"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_create_password_policy_fails(self, mock_lv):
        """Test password policy creation fails with proper error"""
        mock_module = Mock()
        mock_module.params = {
            "name": "password_policy",
            "policy": "password",
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        create_policy(mock_module, mock_array, False)

        mock_module.fail_json.assert_called_once()
        assert "Password policy creation" in str(
            mock_module.fail_json.call_args[1]["msg"]
        )


class TestUpdatePolicySmbExtended:
    """Extended test cases for update_policy with SMB policy"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicySmbPatch")
    def test_update_smb_policy_enable_change(self, mock_smb_patch, mock_lv):
        """Test updating SMB policy enabled state"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy",
            "policy": "smb",
            "enabled": False,
            "client": None,
            "access_based_enumeration": None,
            "continuous_availability": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_current = Mock()
        mock_current.enabled = True
        mock_current.access_based_enumeration_enabled = False
        mock_current.continuous_availability_enabled = False
        mock_array.get_policies_smb.return_value = Mock(
            status_code=200, items=[mock_current]
        )
        mock_array.patch_policies_smb.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_array.patch_policies_smb.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_smb_policy_no_change(self, mock_lv):
        """Test SMB policy with no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy",
            "policy": "smb",
            "enabled": True,
            "client": None,
            "access_based_enumeration": False,  # Match current state
            "continuous_availability": False,  # Match current state
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_current = Mock()
        mock_current.enabled = True
        mock_current.access_based_enumeration_enabled = False
        mock_current.continuous_availability_enabled = False
        mock_array.get_policies_smb.return_value = Mock(
            status_code=200, items=[mock_current]
        )

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdatePolicySnapshotExtended:
    """Extended test cases for update_policy with snapshot policy"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_update_snapshot_policy_enable_change(self, mock_policy_patch, mock_lv):
        """Test updating snapshot policy enabled state"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "enabled": False,
            "snap_client_name": None,
            "snap_every": None,
            "snap_keep_for": None,
            "snap_at": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_current = Mock()
        mock_current.enabled = True
        mock_array.get_policies_snapshot.return_value = Mock(
            status_code=200, items=[mock_current]
        )
        mock_array.patch_policies_snapshot.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_array.patch_policies_snapshot.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePolicyQuotaExtended:
    """Extended test cases for update_policy with quota policy"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPatch")
    def test_update_quota_policy_enable_change(self, mock_policy_patch, mock_lv):
        """Test updating quota policy enabled state"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": False,
            "quota_limit": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_current = Mock()
        mock_current.enabled = True
        mock_array.get_policies_quota.return_value = Mock(
            status_code=200, items=[mock_current]
        )
        mock_array.patch_policies_quota.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_array.patch_policies_quota.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicyNfsWithClient:
    """Test cases for create_policy with NFS policy with client rules"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyrulenfsclientpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleNfsClientPost")
    @patch("plugins.modules.purefa_policy.PolicyNfsPatch")
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_nfs_policy_with_client_all_squash(
        self,
        mock_policy_post,
        mock_nfs_patch,
        mock_rule_post,
        mock_rules,
        mock_lv,
        mock_patch,
        mock_post,
        mock_check,
    ):
        """Test NFS policy creation with client and all_squash=True"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": "192.168.1.0/24",
            "nfs_access": "root-squash",
            "nfs_permission": "rw",
            "anongid": "65534",
            "anonuid": "65534",
            "user_mapping": True,
            "nfs_version": None,
            "security": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post.return_value = Mock(status_code=200)
        mock_patch.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, True)  # all_squash=True

        mock_post.assert_called()
        mock_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyrulenfsclientpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleNfsClientPost")
    @patch("plugins.modules.purefa_policy.PolicyNfsPatch")
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_nfs_policy_with_client_no_squash(
        self,
        mock_policy_post,
        mock_nfs_patch,
        mock_rule_post,
        mock_rules,
        mock_lv,
        mock_patch,
        mock_post,
        mock_check,
    ):
        """Test NFS policy creation with client and all_squash=False"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": "192.168.1.0/24",
            "nfs_access": "no-root-squash",
            "nfs_permission": "rw",
            "user_mapping": True,
            "nfs_version": None,
            "security": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post.return_value = Mock(status_code=200)
        mock_patch.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)  # all_squash=False

        mock_post.assert_called()
        mock_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyNfsPatch")
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_nfs_policy_with_nfs_version(
        self,
        mock_policy_post,
        mock_nfs_patch,
        mock_lv,
        mock_patch,
        mock_post,
        mock_check,
    ):
        """Test NFS policy creation with nfs_version specified"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": None,
            "user_mapping": True,
            "nfs_version": ["nfsv3", "nfsv4"],
            "security": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post.return_value = Mock(status_code=200)
        mock_patch.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_post.assert_called()
        mock_patch.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicySmbWithClient:
    """Test cases for create_policy with SMB policy with client rules"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyrulesmbclientpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleSmbClientPost")
    @patch("plugins.modules.purefa_policy.PolicySmbPatch")
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_smb_policy_with_client(
        self,
        mock_policy_post,
        mock_smb_patch,
        mock_rule_post,
        mock_rules,
        mock_lv,
        mock_patch,
        mock_post,
        mock_check,
    ):
        """Test SMB policy creation with client"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy",
            "policy": "smb",
            "enabled": True,
            "client": "192.168.1.0/24",
            "smb_anon_allowed": False,
            "smb_encrypt": True,
            "access_based_enumeration": False,
            "continuous_availability": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post.return_value = Mock(status_code=200)
        mock_patch.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_post.assert_called()
        mock_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_smb_policy_failure(
        self,
        mock_policy_post,
        mock_lv,
        mock_post,
    ):
        """Test SMB policy creation failure"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy",
            "policy": "smb",
            "enabled": True,
            "client": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_error = Mock()
        mock_error.message = "Policy creation failed"
        mock_post.return_value = Mock(status_code=400, errors=[mock_error])

        create_policy(mock_module, mock_array, False)

        mock_module.fail_json.assert_called_once()


class TestCreatePolicySnapshotWithRules:
    """Test cases for create_policy with snapshot policy rules"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_snapshot_policy_no_rules(
        self,
        mock_policy_post,
        mock_lv,
        mock_post,
        mock_check,
    ):
        """Test snapshot policy creation without rules"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "enabled": True,
            "snap_client_name": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_snapshot_policy_failure(
        self,
        mock_policy_post,
        mock_lv,
        mock_post,
    ):
        """Test snapshot policy creation failure"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "enabled": True,
            "snap_client_name": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_error = Mock()
        mock_error.message = "Policy creation failed"
        mock_post.return_value = Mock(status_code=400, errors=[mock_error])

        create_policy(mock_module, mock_array, False)

        mock_module.fail_json.assert_called_once()


class TestDeletePolicyWithDirectories:
    """Test cases for delete_policy with directory removal"""

    @patch("plugins.modules.purefa_policy.delete_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_policy_with_directories(
        self, mock_lv, mock_get, mock_delete
    ):
        """Test delete snapshot policy with directory removal"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "directory": ["dir1", "dir2"],
            "snap_client_name": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock getting directories - member.name must return actual string
        mock_dir1 = Mock()
        mock_dir1.member.name = "dir1"
        mock_dir2 = Mock()
        mock_dir2.member.name = "dir2"
        mock_get.return_value = Mock(status_code=200, items=[mock_dir1, mock_dir2])
        mock_delete.return_value = Mock(status_code=200)

        delete_policy(mock_module, mock_array)

        mock_get.assert_called()
        mock_delete.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.delete_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_policy_directory_removal_failure(
        self, mock_lv, mock_get, mock_delete
    ):
        """Test delete snapshot policy with directory removal failure"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "directory": ["dir1"],
            "snap_client_name": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock getting directories - member.name must return actual string
        mock_dir1 = Mock()
        mock_dir1.member.name = "dir1"
        mock_get.return_value = Mock(status_code=200, items=[mock_dir1])
        mock_error = Mock()
        mock_error.message = "Failed to remove directory"
        mock_delete.return_value = Mock(status_code=400, errors=[mock_error])

        delete_policy(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestCreatePolicyQuotaExtended:
    """Extended test cases for quota policy creation"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_quota_policy_basic(
        self, mock_policy_post, mock_lv, mock_post, mock_check
    ):
        """Test quota policy creation basic (no rules)"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_limit": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_quota_policy_failure(self, mock_policy_post, mock_lv, mock_post):
        """Test quota policy creation failure"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_limit": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_error = Mock()
        mock_error.message = "Policy creation failed"
        mock_post.return_value = Mock(status_code=400, errors=[mock_error])

        create_policy(mock_module, mock_array, False)

        mock_module.fail_json.assert_called_once()


class TestCreatePolicyAutodirExtended:
    """Extended test cases for autodir policy creation"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_autodir_policy_basic(
        self, mock_policy_post, mock_lv, mock_post, mock_check
    ):
        """Test basic autodir policy creation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy",
            "policy": "autodir",
            "enabled": True,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_autodir_policy_failure(self, mock_policy_post, mock_lv, mock_post):
        """Test autodir policy creation failure"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy",
            "policy": "autodir",
            "enabled": True,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_error = Mock()
        mock_error.message = "Policy creation failed"
        mock_post.return_value = Mock(status_code=400, errors=[mock_error])

        create_policy(mock_module, mock_array, False)

        mock_module.fail_json.assert_called_once()


class TestUpdatePolicyNfsExtended:
    """Test cases for update_policy with NFS policy - extended"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_nfs_policy_add_client_rule(
        self, mock_lv, mock_get, mock_post, mock_check
    ):
        """Test update NFS policy adding a new client rule"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": "192.168.1.0/24",
            "all_squash": False,
            "nfs_permission": "rw",
            "nfs_access": "root-squash",
            "nfs_version": None,
            "security": None,
            "anongid": None,
            "anonuid": None,
            "directory": None,
            "user_mapping": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock policy item returned by first get call
        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.user_mapping_enabled = False
        mock_policy.nfs_version = []

        # Return policy item first, then empty rules
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_nfs
            Mock(status_code=200, items=[mock_policy]),  # get_policies_nfs for user_map
            Mock(status_code=200, items=[]),  # get_directories_policies_nfs
            Mock(status_code=200, items=[]),  # get_policies_nfs_client_rules
        ]
        mock_post.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_nfs_policy_no_changes(self, mock_lv, mock_get):
        """Test update NFS policy with no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": None,
            "all_squash": False,
            "directory": None,
            "nfs_version": None,
            "user_mapping": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock policy item
        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.user_mapping_enabled = False
        mock_policy.nfs_version = []

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_nfs
            Mock(status_code=200, items=[mock_policy]),  # get_policies_nfs for user_map
            Mock(status_code=200, items=[]),  # get_directories_policies_nfs
        ]

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdatePolicySmb:
    """Test cases for update_policy with SMB policy"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicySmbPatch")
    def test_update_smb_policy_add_client(
        self, mock_smb_patch, mock_lv, mock_get, mock_patch, mock_post, mock_check
    ):
        """Test update SMB policy adding a client"""
        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy",
            "policy": "smb",
            "enabled": True,
            "client": "192.168.1.0/24",
            "smb_anon_allowed": False,
            "smb_encrypt": True,
            "access_based_enumeration": True,
            "continuous_availability": False,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock SMB policy item
        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.access_based_enumeration_enabled = False
        mock_policy.continuous_availability_enabled = False

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_smb
            Mock(status_code=200, items=[]),  # get_directories_policies_smb
            Mock(status_code=200, items=[]),  # get_policies_smb_client_rules
        ]
        mock_patch.return_value = Mock(status_code=200)
        mock_post.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_patch.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePolicySnapshot:
    """Test cases for update_policy with snapshot policy"""

    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_snapshot_policy_no_client_name(self, mock_lv, mock_get):
        """Test update snapshot policy without client name"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "enabled": True,
            "snap_client_name": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock snapshot policy item
        mock_policy = Mock()
        mock_policy.enabled = True

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_snapshot_policy_retention_less_than_interval(
        self, mock_lv, mock_get
    ):
        """Test update snapshot policy with retention less than interval fails"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "enabled": True,
            "snap_client_name": "client1",
            "snap_every": 120,
            "snap_keep_for": 60,
            "snap_at": None,
            "snap_suffix": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        # Make fail_json raise an exception to stop execution
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock snapshot policy item
        mock_policy = Mock()
        mock_policy.enabled = True

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])

        with pytest.raises(SystemExit):
            update_policy(mock_module, mock_array, "2.38", False)

        mock_module.fail_json.assert_called_once()


class TestUpdatePolicyQuota:
    """Test cases for update_policy with quota policy"""

    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_quota_policy_no_changes(self, mock_lv, mock_get):
        """Test update quota policy with no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_limit": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock quota policy item
        mock_policy = Mock()
        mock_policy.enabled = True

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdatePolicyAutodir:
    """Test cases for update_policy with autodir policy"""

    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_autodir_policy_no_changes(self, mock_lv, mock_get):
        """Test update autodir policy with no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy",
            "policy": "autodir",
            "enabled": True,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock autodir policy item
        mock_policy = Mock()
        mock_policy.enabled = True

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdatePolicyPassword:
    """Test cases for update_policy with password policy"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPassword")
    def test_update_password_policy_change_enabled(
        self, mock_pwd, mock_lv, mock_get, mock_patch, mock_check
    ):
        """Test update password policy changing enabled state"""
        mock_module = Mock()
        mock_module.params = {
            "name": "password_policy",
            "policy": "password",
            "enabled": False,  # changing to disabled
            "enforce_dictionary_check": False,
            "enforce_username_check": False,
            "min_character_groups": 1,
            "min_characters_per_group": 1,
            "min_password_length": 8,
            "min_password_age": 0,
            "max_password_age": 0,
            "max_login_attempts": 5,
            "lockout_duration": 600,
            "password_history": 0,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock password policy item - attributes must match what the code expects
        mock_policy = Mock()
        mock_policy.enabled = True  # currently enabled
        mock_policy.enforce_dictionary_check = False
        mock_policy.enforce_username_check = False
        mock_policy.min_character_groups = 1
        mock_policy.min_characters_per_group = 1
        mock_policy.min_password_length = 8
        mock_policy.min_password_age = 0
        mock_policy.max_password_age = 0
        mock_policy.max_login_attempts = 5
        mock_policy.lockout_duration = 600
        mock_policy.password_history = 0

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_patch.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateNfsPolicyWithClientRules:
    """Test cases for update_policy with NFS policy client rules"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_nfs_policy_add_new_client_rule_all_squash(
        self, mock_lv, mock_get, mock_post, mock_check
    ):
        """Test update NFS policy adding a new client rule with all_squash=True"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": "192.168.1.0/24",
            "all_squash": True,
            "nfs_permission": "rw",
            "nfs_access": "all-squash",
            "nfs_version": None,
            "security": None,
            "anongid": "65534",
            "anonuid": "65534",
            "directory": None,
            "user_mapping": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock policy item
        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.user_mapping_enabled = False
        mock_policy.nfs_version = []

        # Return policy item first, then empty rules (no existing rule for this client)
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_nfs
            Mock(status_code=200, items=[mock_policy]),  # get_policies_nfs for user_map
            Mock(status_code=200, items=[]),  # get_directories_policies_nfs
            Mock(status_code=200, items=[]),  # get_policies_nfs_client_rules
        ]
        mock_post.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", True)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_nfs_policy_add_new_client_rule_with_security(
        self, mock_lv, mock_get, mock_post, mock_check
    ):
        """Test update NFS policy adding a new client rule with security options"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy",
            "policy": "nfs",
            "enabled": True,
            "client": "10.0.0.0/8",
            "all_squash": False,
            "nfs_permission": "ro",
            "nfs_access": "root-squash",
            "nfs_version": ["nfsv4"],
            "security": ["krb5", "krb5i"],
            "anongid": "65534",
            "anonuid": "65534",
            "directory": None,
            "user_mapping": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock policy item
        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.user_mapping_enabled = False
        mock_policy.nfs_version = ["nfsv4"]

        # Return policy item first, then empty rules (no existing rule for this client)
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_nfs
            Mock(status_code=200, items=[mock_policy]),  # get_policies_nfs for user_map
            Mock(status_code=200, items=[]),  # get_directories_policies_nfs
            Mock(status_code=200, items=[]),  # get_policies_nfs_client_rules
        ]
        mock_post.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicyExtendedCases:
    """Extended test cases for create_policy function"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_quota_policy_with_limit(
        self, mock_policy_post, mock_lv, mock_post, mock_check
    ):
        """Test creating quota policy with quota limit"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_limit": "1G",
            "quota_enforced": True,
            "ignore_usage": False,
            "quota_notifications": [],
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post.return_value = Mock(status_code=200)

        from plugins.modules.purefa_policy import create_policy

        create_policy(mock_module, mock_array, False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_autodir_policy_with_directory(
        self, mock_policy_post, mock_lv, mock_post, mock_check
    ):
        """Test creating autodir policy with directories"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy",
            "policy": "autodir",
            "enabled": True,
            "directory": ["dir1", "dir2"],
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post.return_value = Mock(status_code=200)

        from plugins.modules.purefa_policy import create_policy

        create_policy(mock_module, mock_array, False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSnapshotPolicyWithRules:
    """Test cases for update_policy with snapshot policy rules"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_snapshot_policy_add_rule(
        self, mock_lv, mock_get, mock_post, mock_check
    ):
        """Test update snapshot policy adding a new rule"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "enabled": True,
            "snap_at": None,
            "snap_every": 60,
            "snap_keep_for": 120,
            "snap_client_name": "client1",
            "snap_suffix": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock policy item returned by get calls
        mock_policy = Mock()
        mock_policy.enabled = True

        # Return policy item first, then empty rules (no existing rule matches)
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_snapshot
            Mock(status_code=200, items=[]),  # get_directories_policies_snapshot
            Mock(status_code=200, items=[]),  # get_policies_snapshot_rules
        ]
        mock_post.return_value = Mock(status_code=200)

        from plugins.modules.purefa_policy import update_policy

        update_policy(mock_module, mock_array, "2.38", False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_snapshot_policy_with_snap_at(
        self, mock_lv, mock_get, mock_post, mock_check
    ):
        """Test update snapshot policy with snap_at parameter"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "enabled": True,
            "snap_at": "02:00",
            "snap_every": 1440,  # Must be multiple of 1440 for snap_at
            "snap_keep_for": 2880,
            "snap_client_name": "daily_client",
            "snap_suffix": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True

        # Mock existing rule that doesn't match
        mock_rule = Mock()
        mock_rule.client_name = "other_client"
        mock_rule.every = 60000
        mock_rule.keep_for = 120000

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_snapshot
            Mock(status_code=200, items=[]),  # get_directories_policies_snapshot
            Mock(status_code=200, items=[mock_rule]),  # get_policies_snapshot_rules
        ]
        mock_post.return_value = Mock(status_code=200)

        from plugins.modules.purefa_policy import update_policy

        update_policy(mock_module, mock_array, "2.38", False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_snapshot_policy_retention_less_than_interval_fails(
        self, mock_lv, mock_get
    ):
        """Test update snapshot policy fails when retention < interval"""
        mock_module = Mock()
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "snap_policy",
            "policy": "snapshot",
            "enabled": True,
            "snap_at": None,
            "snap_every": 120,  # 120 minutes
            "snap_keep_for": 60,  # 60 minutes (less than snap_every)
            "snap_client_name": "client1",
            "snap_suffix": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True

        # Mock existing rule that doesn't match
        mock_rule = Mock()
        mock_rule.client_name = "other_client"
        mock_rule.every = 60000
        mock_rule.keep_for = 120000

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_snapshot
            Mock(status_code=200, items=[]),  # get_directories_policies_snapshot
            Mock(status_code=200, items=[mock_rule]),  # get_policies_snapshot_rules
        ]

        from plugins.modules.purefa_policy import update_policy

        with pytest.raises(SystemExit):
            update_policy(mock_module, mock_array, "2.38", False)

        mock_module.fail_json.assert_called_once()


class TestUpdateQuotaPolicyWithRules:
    """Test cases for update_policy with quota policy rules"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_quota_policy_change_limit(
        self, mock_lv, mock_get, mock_patch, mock_check
    ):
        """Test update quota policy changing quota limit"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_limit": "100G",
            "quota_enforced": True,
            "quota_notifications": [],
            "directory": None,
            "ignore_usage": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.quota_limit = 50 * 1024 * 1024 * 1024  # 50GB
        mock_policy.is_enforced = True
        mock_policy.notification = "none"

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_quota
            Mock(status_code=200, items=[]),  # get_directories_policies_quota
        ]
        mock_patch.return_value = Mock(status_code=200)

        from plugins.modules.purefa_policy import update_policy

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_quota_policy_no_change(self, mock_lv, mock_get):
        """Test update quota policy with no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_limit": None,
            "quota_enforced": True,
            "quota_notifications": [],
            "directory": None,
            "ignore_usage": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.quota_limit = 100 * 1024 * 1024 * 1024
        mock_policy.is_enforced = True
        mock_policy.notification = "none"

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_quota
            Mock(status_code=200, items=[]),  # get_directories_policies_quota
        ]

        from plugins.modules.purefa_policy import update_policy

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdateAutodirPolicyWithDirectories:
    """Test cases for update_policy with autodir policy directories"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_autodir_policy_add_directory(
        self, mock_lv, mock_get, mock_post, mock_check
    ):
        """Test update autodir policy adding a directory"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy",
            "policy": "autodir",
            "enabled": True,
            "directory": ["new_dir"],
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_autodir
            Mock(status_code=200, items=[]),  # get_directories_policies_autodir
        ]
        mock_post.return_value = Mock(status_code=200)

        from plugins.modules.purefa_policy import update_policy

        update_policy(mock_module, mock_array, "2.38", False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_autodir_policy_no_change(self, mock_lv, mock_get):
        """Test update autodir policy with no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy",
            "policy": "autodir",
            "enabled": True,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_autodir
            Mock(status_code=200, items=[]),  # get_directories_policies_autodir
        ]

        from plugins.modules.purefa_policy import update_policy

        update_policy(mock_module, mock_array, "2.38", False)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestCreateNfsPolicyWithClient:
    """Tests for create_policy NFS with client rules"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyNfsPatch")
    @patch("plugins.modules.purefa_policy.PolicyrulenfsclientpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleNfsClientPost")
    def test_create_nfs_policy_with_client(
        self, mock_rule_post, mock_rules, mock_nfs_patch, mock_post, mock_lv
    ):
        """Test create NFS policy with client rule"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "client": "192.168.1.0/24",
            "user_mapping": True,
            "nfs_version": None,
            "security": None,
            "nfs_access": "root-squash",
            "nfs_permission": "rw",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_nfs.return_value = Mock(status_code=200)
        mock_array.patch_policies_nfs.return_value = Mock(status_code=200)
        mock_array.post_policies_nfs_client_rules.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_nfs.assert_called_once()
        mock_array.post_policies_nfs_client_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyNfsPatch")
    @patch("plugins.modules.purefa_policy.PolicyrulenfsclientpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleNfsClientPost")
    def test_create_nfs_policy_with_nfs_version(
        self, mock_rule_post, mock_rules, mock_nfs_patch, mock_post, mock_lv
    ):
        """Test create NFS policy with nfs_version"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "client": "192.168.1.0/24",
            "user_mapping": True,
            "nfs_version": ["nfsv3", "nfsv4"],
            "security": None,
            "nfs_access": "root-squash",
            "nfs_permission": "rw",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_nfs.return_value = Mock(status_code=200)
        mock_array.patch_policies_nfs.return_value = Mock(status_code=200)
        mock_array.post_policies_nfs_client_rules.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_nfs.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyNfsPatch")
    def test_create_nfs_policy_with_security(self, mock_nfs_patch, mock_post, mock_lv):
        """Test create NFS policy with security"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "client": None,
            "user_mapping": True,
            "nfs_version": None,
            "security": ["sys", "krb5"],
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_nfs.return_value = Mock(status_code=200)
        mock_array.patch_policies_nfs.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_nfs.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateSmbPolicyWithClient:
    """Tests for create_policy SMB with client rules"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicySmbPatch")
    @patch("plugins.modules.purefa_policy.PolicyrulesmbclientpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleSmbClientPost")
    def test_create_smb_policy_with_client(
        self, mock_rule_post, mock_rules, mock_smb_patch, mock_post, mock_lv
    ):
        """Test create SMB policy with client rule"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "enabled": True,
            "context": "",
            "client": "client1",
            "smb_anon_allowed": False,
            "smb_encrypt": True,
            "access_based_enumeration": True,
            "continuous_availability": False,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.43"
        mock_array.post_policies_smb.return_value = Mock(status_code=200)
        mock_array.patch_policies_smb.return_value = Mock(status_code=200)
        mock_array.post_policies_smb_client_rules.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_smb.assert_called_once()
        mock_array.post_policies_smb_client_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicySmbPatch")
    def test_create_smb_policy_with_ca(self, mock_smb_patch, mock_post, mock_lv):
        """Test create SMB policy with continuous availability"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "enabled": True,
            "context": "",
            "client": None,
            "smb_anon_allowed": False,
            "smb_encrypt": False,
            "access_based_enumeration": True,
            "continuous_availability": True,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.43"
        mock_array.post_policies_smb.return_value = Mock(status_code=200)
        mock_array.patch_policies_smb.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_smb.assert_called_once()
        mock_array.patch_policies_smb.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateSnapshotPolicyWithRules:
    """Tests for create_policy snapshot with rules"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyrulesnapshotpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleSnapshotPost")
    @patch("plugins.modules.purefa_policy.convert_to_millisecs")
    def test_create_snapshot_policy_with_snap_at(
        self, mock_convert, mock_rule_post, mock_rules, mock_post, mock_lv
    ):
        """Test create snapshot policy with snap_at"""
        from plugins.modules.purefa_policy import create_policy

        mock_convert.return_value = 28800000  # 8:00 AM

        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "snap_client_name": "snap_client",
            "snap_at": "08:00",
            "snap_every": 1440,
            "snap_keep_for": 2880,
            "snap_suffix": ".snap",
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_snapshot.return_value = Mock(status_code=200)
        mock_array.post_policies_snapshot_rules.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_snapshot.assert_called_once()
        mock_array.post_policies_snapshot_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyrulesnapshotpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleSnapshotPost")
    def test_create_snapshot_policy_without_snap_at(
        self, mock_rule_post, mock_rules, mock_post, mock_lv
    ):
        """Test create snapshot policy without snap_at"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "snap_client_name": "snap_client",
            "snap_at": None,
            "snap_every": 60,
            "snap_keep_for": 120,
            "snap_suffix": ".snap",
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_snapshot.return_value = Mock(status_code=200)
        mock_array.post_policies_snapshot_rules.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_snapshot.assert_called_once()
        mock_array.post_policies_snapshot_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.DirectoryPolicyPost")
    @patch("plugins.modules.purefa_policy.DirectorypolicypostPolicies")
    @patch("plugins.modules.purefa_policy.Reference")
    def test_create_snapshot_policy_with_directory(
        self, mock_ref, mock_dir_policies, mock_dir_post, mock_post, mock_lv
    ):
        """Test create snapshot policy with directory"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "snap_client_name": None,
            "snap_at": None,
            "snap_every": 60,
            "snap_keep_for": 120,
            "snap_suffix": ".snap",
            "directory": ["/dir1", "/dir2"],
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_snapshot.return_value = Mock(status_code=200)
        mock_array.post_directories_policies_snapshot.return_value = Mock(
            status_code=200
        )

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_snapshot.assert_called_once()
        mock_array.post_directories_policies_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateQuotaPolicyWithDirectory:
    """Tests for create_policy quota with directory"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyrulequotapostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleQuotaPost")
    @patch("plugins.modules.purefa_policy.PolicyMemberPost")
    @patch("plugins.modules.purefa_policy.PolicymemberpostMembers")
    @patch("plugins.modules.purefa_policy.ReferenceWithType")
    @patch("plugins.modules.purefa_policy.human_to_bytes")
    def test_create_quota_policy_with_directory(
        self,
        mock_human,
        mock_ref,
        mock_members,
        mock_member_post,
        mock_rule_post,
        mock_rules,
        mock_post,
        mock_lv,
    ):
        """Test create quota policy with directory members"""
        from plugins.modules.purefa_policy import create_policy

        mock_human.return_value = 1073741824  # 1GB

        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy1",
            "policy": "quota",
            "enabled": True,
            "context": "",
            "quota_limit": "1G",
            "quota_enforced": True,
            "quota_notifications": ["warning"],
            "ignore_usage": False,
            "directory": ["/dir1", "/dir2"],
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_quota.return_value = Mock(status_code=200)
        mock_array.post_policies_quota_rules.return_value = Mock(status_code=200)
        mock_array.post_policies_quota_members.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_quota.assert_called_once()
        mock_array.post_policies_quota_members.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyrulequotapostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleQuotaPost")
    @patch("plugins.modules.purefa_policy.human_to_bytes")
    def test_create_quota_policy_with_limit(
        self, mock_human, mock_rule_post, mock_rules, mock_post, mock_lv
    ):
        """Test create quota policy with quota_limit"""
        from plugins.modules.purefa_policy import create_policy

        mock_human.return_value = 1073741824  # 1GB

        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy1",
            "policy": "quota",
            "enabled": True,
            "context": "",
            "quota_limit": "1G",
            "quota_enforced": True,
            "quota_notifications": ["warning"],
            "ignore_usage": False,
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_quota.return_value = Mock(status_code=200)
        mock_array.post_policies_quota_rules.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_quota.assert_called_once()
        mock_array.post_policies_quota_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteAutodirPolicyWithDirectory:
    """Tests for delete_policy autodir with directory"""

    @patch("plugins.modules.purefa_policy.delete_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_autodir_policy_with_directory(self, mock_lv, mock_get, mock_delete):
        """Test delete autodir policy with directory"""
        from plugins.modules.purefa_policy import delete_policy

        mock_dir = Mock()
        mock_dir.member = Mock()
        mock_dir.member.name = "/dir1"

        mock_get.return_value = Mock(status_code=200, items=[mock_dir])
        mock_delete.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy1",
            "policy": "autodir",
            "context": "",
            "directory": ["/dir1"],
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        delete_policy(mock_module, mock_array)

        mock_delete.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.delete_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_autodir_policy_directory_not_in_list(
        self, mock_lv, mock_get, mock_delete
    ):
        """Test delete autodir policy where directory is not in current list"""
        from plugins.modules.purefa_policy import delete_policy

        mock_dir = Mock()
        mock_dir.member = Mock()
        mock_dir.member.name = "/other_dir"

        mock_get.return_value = Mock(status_code=200, items=[mock_dir])

        mock_module = Mock()
        mock_module.params = {
            "name": "autodir_policy1",
            "policy": "autodir",
            "context": "",
            "directory": ["/dir1"],
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        delete_policy(mock_module, mock_array)

        mock_delete.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestDeleteQuotaPolicyWithRules:
    """Tests for delete_policy quota with quota_limit"""

    @patch("plugins.modules.purefa_policy.delete_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.human_to_bytes")
    def test_delete_quota_policy_with_quota_limit(
        self, mock_human, mock_lv, mock_get, mock_delete
    ):
        """Test delete quota policy with quota_limit"""
        from plugins.modules.purefa_policy import delete_policy

        mock_human.return_value = 1073741824  # 1GB

        mock_rule = Mock()
        mock_rule.name = "rule1"
        mock_rule.quota_limit = 1073741824
        mock_rule.enforced = True
        mock_rule.notifications = "warning"

        mock_get.return_value = Mock(status_code=200, items=[mock_rule])
        mock_delete.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy1",
            "policy": "quota",
            "context": "",
            "quota_limit": "1G",
            "quota_enforced": True,
            "quota_notifications": ["warning"],
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        delete_policy(mock_module, mock_array)

        mock_delete.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.delete_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_quota_policy_with_directory(self, mock_lv, mock_get, mock_delete):
        """Test delete quota policy with directory members"""
        from plugins.modules.purefa_policy import delete_policy

        mock_member = Mock()
        mock_member.member = Mock()
        mock_member.member.name = "/dir1"

        mock_get.return_value = Mock(status_code=200, items=[mock_member])
        mock_delete.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy1",
            "policy": "quota",
            "context": "",
            "quota_limit": None,
            "quota_enforced": True,
            "quota_notifications": ["warning"],
            "directory": ["/dir1"],
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        delete_policy(mock_module, mock_array)

        mock_delete.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateNfsPolicyWithClientRulesNew:
    """Tests for update_policy NFS with client rules - new tests"""

    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_nfs_policy_change_nfs_version(self, mock_lv, mock_get, mock_patch):
        """Test update NFS policy with nfs_version change"""
        from plugins.modules.purefa_policy import update_policy

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.nfs_version = ["nfsv3"]

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])
        mock_patch.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "nfs_version": ["nfsv3", "nfsv4"],
            "user_mapping": True,
            "client": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        update_policy(mock_module, mock_array, "2.38", False)

        mock_patch.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_nfs_policy_change_user_mapping(self, mock_lv, mock_get, mock_patch):
        """Test update NFS policy with user_mapping change"""
        from plugins.modules.purefa_policy import update_policy

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.nfs_version = []
        mock_policy.user_mapping_enabled = False

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])
        mock_patch.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "nfs_version": None,
            "user_mapping": True,
            "client": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        update_policy(mock_module, mock_array, "2.38", False)

        mock_patch.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateNfsPolicyAddClientRule:
    """Tests for update_policy NFS adding new client rules"""

    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyrulenfsclientpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleNfsClientPost")
    def test_update_nfs_policy_add_client_rule(
        self, mock_rule_post, mock_rules, mock_lv, mock_get, mock_patch, mock_post
    ):
        """Test update NFS policy adding new client rule"""
        from plugins.modules.purefa_policy import update_policy

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.nfs_version = []
        mock_policy.user_mapping_enabled = True

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_nfs
            Mock(
                status_code=200, items=[mock_policy]
            ),  # get_policies_nfs (user_mapping)
            Mock(
                status_code=200, items=[]
            ),  # get_policies_nfs_client_rules - empty rules
        ]
        mock_post.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "nfs_policy1",
            "policy": "nfs",
            "enabled": True,
            "context": "",
            "nfs_version": None,
            "user_mapping": True,
            "client": "192.168.1.0/24",
            "nfs_access": "root-squash",
            "nfs_permission": "rw",
            "security": None,
            "anongid": None,
            "anonuid": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"

        update_policy(mock_module, mock_array, "2.30", False)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateSnapshotPolicyValidation:
    """Tests for create_policy snapshot validation"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    def test_create_snapshot_policy_keep_for_less_than_every(self, mock_post, mock_lv):
        """Test create snapshot policy fails when keep_for < every"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "snap_client_name": "snap_client",
            "snap_at": None,
            "snap_every": 120,
            "snap_keep_for": 60,  # Less than snap_every
            "snap_suffix": ".snap",
            "directory": None,
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_snapshot.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            create_policy(mock_module, mock_array, False)

        mock_module.fail_json.assert_called_once()
        assert "Retention period" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.convert_to_millisecs")
    def test_create_snapshot_policy_snap_at_invalid_every(
        self, mock_convert, mock_post, mock_lv
    ):
        """Test create snapshot policy fails when snap_at set but every not multiple of 1440"""
        from plugins.modules.purefa_policy import create_policy

        mock_convert.return_value = 28800000

        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "snap_client_name": "snap_client",
            "snap_at": "08:00",
            "snap_every": 120,  # Not a multiple of 1440
            "snap_keep_for": 240,
            "snap_suffix": ".snap",
            "directory": None,
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_policies_snapshot.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            create_policy(mock_module, mock_array, False)

        mock_module.fail_json.assert_called_once()
        assert "snap_at" in str(mock_module.fail_json.call_args)


class TestCreatePasswordPolicy:
    """Tests for create_policy password policy"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_create_password_policy_fails(self, mock_lv):
        """Test create password policy fails with not supported message"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "password_policy1",
            "policy": "password",
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        create_policy(mock_module, mock_array, False)

        mock_module.fail_json.assert_called_once()
        assert "not yet supported" in str(mock_module.fail_json.call_args)


class TestCreateSnapshotPolicyOldApi:
    """Tests for create_policy snapshot with older API (no suffix)"""

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyrulesnapshotpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleSnapshotPost")
    @patch("plugins.modules.purefa_policy.convert_to_millisecs")
    def test_create_snapshot_policy_old_api_with_snap_at(
        self, mock_convert, mock_rule_post, mock_rules, mock_post, mock_lv
    ):
        """Test create snapshot policy with old API (no suffix) with snap_at"""
        from plugins.modules.purefa_policy import create_policy

        mock_convert.return_value = 28800000

        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "snap_client_name": "snap_client",
            "snap_at": "08:00",
            "snap_every": 1440,
            "snap_keep_for": 2880,
            "snap_suffix": ".snap",
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        # Use old API version that doesn't support suffix
        mock_array.get_rest_version.return_value = "2.8"
        mock_array.post_policies_snapshot.return_value = Mock(status_code=200)
        mock_array.post_policies_snapshot_rules.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_snapshot.assert_called_once()
        mock_array.post_policies_snapshot_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPost")
    @patch("plugins.modules.purefa_policy.PolicyrulesnapshotpostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleSnapshotPost")
    def test_create_snapshot_policy_old_api_without_snap_at(
        self, mock_rule_post, mock_rules, mock_post, mock_lv
    ):
        """Test create snapshot policy with old API (no suffix) without snap_at"""
        from plugins.modules.purefa_policy import create_policy

        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "snap_client_name": "snap_client",
            "snap_at": None,
            "snap_every": 60,
            "snap_keep_for": 120,
            "snap_suffix": ".snap",
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        # Use old API version that doesn't support suffix
        mock_array.get_rest_version.return_value = "2.8"
        mock_array.post_policies_snapshot.return_value = Mock(status_code=200)
        mock_array.post_policies_snapshot_rules.return_value = Mock(status_code=200)

        create_policy(mock_module, mock_array, False)

        mock_array.post_policies_snapshot.assert_called_once()
        mock_array.post_policies_snapshot_rules.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSmbPolicyAccessEnumeration:
    """Tests for update_policy SMB with access_based_enumeration"""

    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_smb_policy_change_abe(self, mock_lv, mock_get, mock_patch):
        """Test update SMB policy changing access_based_enumeration"""
        from plugins.modules.purefa_policy import update_policy

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.access_based_enumeration_enabled = False
        mock_policy.continuous_availability_enabled = False

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_smb
            Mock(status_code=200, items=[]),  # get_policies_smb_client_rules
        ]
        mock_patch.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "enabled": True,
            "context": "",
            "access_based_enumeration": True,
            "continuous_availability": False,
            "client": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.43"

        update_policy(mock_module, mock_array, "2.43", False)

        mock_patch.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_update_smb_policy_change_ca(self, mock_lv, mock_get, mock_patch):
        """Test update SMB policy changing continuous_availability"""
        from plugins.modules.purefa_policy import update_policy

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.access_based_enumeration_enabled = True
        mock_policy.continuous_availability_enabled = False

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_smb
            Mock(status_code=200, items=[]),  # get_policies_smb_client_rules
        ]
        mock_patch.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "smb_policy1",
            "policy": "smb",
            "enabled": True,
            "context": "",
            "access_based_enumeration": True,
            "continuous_availability": True,
            "client": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.43"

        update_policy(mock_module, mock_array, "2.43", False)

        mock_patch.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSnapshotPolicyWithDirectory:
    """Tests for update_policy snapshot with directory"""

    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.DirectoryPolicyPost")
    @patch("plugins.modules.purefa_policy.DirectorypolicypostPolicies")
    @patch("plugins.modules.purefa_policy.Reference")
    def test_update_snapshot_policy_add_directory(
        self,
        mock_ref,
        mock_dir_policies,
        mock_dir_post,
        mock_lv,
        mock_get,
        mock_patch,
        mock_post,
    ):
        """Test update snapshot policy adding new directory"""
        from plugins.modules.purefa_policy import update_policy

        mock_policy = Mock()
        mock_policy.enabled = True

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_snapshot
            Mock(
                status_code=200, items=[]
            ),  # get_directories_policies_snapshot - empty
            Mock(status_code=200, items=[]),  # get_policies_snapshot_rules
        ]
        mock_post.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "snap_policy1",
            "policy": "snapshot",
            "enabled": True,
            "context": "",
            "directory": ["/dir1", "/dir2"],
            "snap_client_name": None,
            "snap_at": None,
            "snap_every": 60,
            "snap_keep_for": 120,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        update_policy(mock_module, mock_array, "2.38", False)

        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteQuotaPolicyNoRulesNoDirectory:
    """Tests for delete_policy quota without rules or directory"""

    @patch("plugins.modules.purefa_policy.delete_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_delete_quota_policy_full(self, mock_lv, mock_get, mock_delete):
        """Test delete quota policy fully (no rules, no directory)"""
        from plugins.modules.purefa_policy import delete_policy

        mock_member = Mock()
        mock_member.member = Mock()
        mock_member.member.name = "/dir1"

        mock_get.return_value = Mock(status_code=200, items=[mock_member])
        mock_delete.return_value = Mock(status_code=200)

        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy1",
            "policy": "quota",
            "context": "",
            "quota_limit": None,
            "quota_enforced": True,
            "quota_notifications": ["warning"],
            "directory": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        delete_policy(mock_module, mock_array)

        mock_delete.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePasswordPolicyBugFixes:
    """Test cases for password policy bug fixes - lockout_duration and None checks"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPassword")
    def test_update_lockout_duration_only(
        self, mock_pwd, mock_lv, mock_get, mock_patch, mock_check
    ):
        """Test updating only lockout_duration doesn't set other params to None.
        Bug fix: lockout_duration was updating current_pwd_policy instead of new_pwd_policy
        """
        mock_module = Mock()
        mock_module.params = {
            "name": "password_policy",
            "policy": "password",
            "enabled": True,
            # Only lockout_duration provided, others are None
            "enforce_dictionary_check": None,
            "enforce_username_check": None,
            "min_character_groups": None,
            "min_characters_per_group": None,
            "min_password_length": None,
            "min_password_age": None,
            "max_password_age": None,
            "max_login_attempts": None,
            "lockout_duration": 1200,  # User wants to change this from 600 to 1200
            "password_history": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current password policy
        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.enforce_dictionary_check = True  # Current value
        mock_policy.enforce_username_check = True
        mock_policy.min_character_groups = 2
        mock_policy.min_characters_per_group = 1
        mock_policy.min_password_length = 12
        mock_policy.min_password_age = 0
        mock_policy.max_password_age = 0
        mock_policy.max_login_attempts = 5
        mock_policy.lockout_duration = 600000  # 600 seconds in ms
        mock_policy.password_history = 0

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        # Verify patch was called with the new lockout_duration value
        mock_patch.assert_called()
        # Verify PolicyPassword was constructed with correct values
        mock_pwd.assert_called_once()
        call_kwargs = mock_pwd.call_args[1]
        # lockout_duration should be 1200 * 1000 = 1200000 ms
        assert call_kwargs["lockout_duration"] == 1200000
        # Other params should retain current values (not None)
        assert call_kwargs["enforce_dictionary_check"] is True
        assert call_kwargs["enforce_username_check"] is True
        assert call_kwargs["min_character_groups"] == 2
        assert call_kwargs["min_characters_per_group"] == 1
        assert call_kwargs["min_password_length"] == 12
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPassword")
    def test_update_enforce_dictionary_check_false(
        self, mock_pwd, mock_lv, mock_get, mock_patch, mock_check
    ):
        """Test explicitly setting enforce_dictionary_check to False works correctly.
        Bug fix: params without None check could be set to None unintentionally
        """
        mock_module = Mock()
        mock_module.params = {
            "name": "password_policy",
            "policy": "password",
            "enabled": True,
            "enforce_dictionary_check": False,  # Explicitly setting to False
            "enforce_username_check": None,
            "min_character_groups": None,
            "min_characters_per_group": None,
            "min_password_length": None,
            "min_password_age": None,
            "max_password_age": None,
            "max_login_attempts": None,
            "lockout_duration": None,
            "password_history": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.enforce_dictionary_check = True  # Currently True
        mock_policy.enforce_username_check = True
        mock_policy.min_character_groups = 2
        mock_policy.min_characters_per_group = 1
        mock_policy.min_password_length = 12
        mock_policy.min_password_age = 0
        mock_policy.max_password_age = 0
        mock_policy.max_login_attempts = 5
        mock_policy.lockout_duration = 600000
        mock_policy.password_history = 0

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_pwd.assert_called_once()
        call_kwargs = mock_pwd.call_args[1]
        # enforce_dictionary_check should be False (changed)
        assert call_kwargs["enforce_dictionary_check"] is False
        # Other params should retain current values
        assert call_kwargs["enforce_username_check"] is True
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPassword")
    def test_update_min_password_length_only(
        self, mock_pwd, mock_lv, mock_get, mock_patch, mock_check
    ):
        """Test updating only min_password_length preserves other params.
        Bug fix: min_password_length didn't have None check
        """
        mock_module = Mock()
        mock_module.params = {
            "name": "password_policy",
            "policy": "password",
            "enabled": True,
            "enforce_dictionary_check": None,
            "enforce_username_check": None,
            "min_character_groups": None,
            "min_characters_per_group": None,
            "min_password_length": 16,  # Changing from 12 to 16
            "min_password_age": None,
            "max_password_age": None,
            "max_login_attempts": None,
            "lockout_duration": None,
            "password_history": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.enforce_dictionary_check = True
        mock_policy.enforce_username_check = True
        mock_policy.min_character_groups = 2
        mock_policy.min_characters_per_group = 1
        mock_policy.min_password_length = 12  # Current value
        mock_policy.min_password_age = 0
        mock_policy.max_password_age = 0
        mock_policy.max_login_attempts = 5
        mock_policy.lockout_duration = 600000
        mock_policy.password_history = 0

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_pwd.assert_called_once()
        call_kwargs = mock_pwd.call_args[1]
        assert call_kwargs["min_password_length"] == 16
        # Other params should retain current values
        assert call_kwargs["enforce_dictionary_check"] is True
        assert call_kwargs["min_character_groups"] == 2
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyPassword")
    def test_update_password_policy_null_fields(
        self, mock_pwd, mock_lv, mock_get, mock_patch, mock_check
    ):
        """Null password-policy fields must not raise AttributeError (issue #1030).

        A management policy can return null for fields such as lockout_duration.
        The pydantic models in newer py-pure-client raise AttributeError on
        direct access to an unset field, so the module must use getattr and
        treat null as "not configured".
        """
        mock_module = Mock()
        mock_module.params = {
            "name": "management",
            "policy": "password",
            "enabled": True,
            "enforce_dictionary_check": True,
            "enforce_username_check": True,
            "min_character_groups": 4,
            "min_characters_per_group": 1,
            "min_password_length": 14,
            "min_password_age": None,
            "max_password_age": None,
            "max_login_attempts": 5,
            "lockout_duration": 900,
            "password_history": 24,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # spec omits the six nullable fields, so direct attribute access on
        # them raises AttributeError - mirroring the pydantic SDK returning
        # null - and getattr(..., None) is the only safe way to read them.
        mock_policy = Mock(
            spec=[
                "enabled",
                "min_password_age",
                "max_password_age",
                "max_login_attempts",
                "password_history",
            ]
        )
        mock_policy.enabled = True
        mock_policy.min_password_age = 0
        mock_policy.max_password_age = 0
        mock_policy.max_login_attempts = 5
        mock_policy.password_history = 0

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        mock_pwd.assert_called_once()
        call_kwargs = mock_pwd.call_args[1]
        # Requested values are applied over the null (unconfigured) current ones
        assert call_kwargs["lockout_duration"] == 900000
        assert call_kwargs["min_password_length"] == 14
        assert call_kwargs["min_character_groups"] == 4
        assert call_kwargs["min_characters_per_group"] == 1
        assert call_kwargs["enforce_dictionary_check"] is True
        assert call_kwargs["enforce_username_check"] is True
        assert call_kwargs["password_history"] == 24
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_no_change_when_all_params_none(self, mock_lv, mock_get):
        """Test no change is made when all password params are None.
        Bug fix: ensure None params don't trigger changes
        """
        mock_module = Mock()
        mock_module.params = {
            "name": "password_policy",
            "policy": "password",
            "enabled": True,  # Same as current
            # All password params are None
            "enforce_dictionary_check": None,
            "enforce_username_check": None,
            "min_character_groups": None,
            "min_characters_per_group": None,
            "min_password_length": None,
            "min_password_age": None,
            "max_password_age": None,
            "max_login_attempts": None,
            "lockout_duration": None,
            "password_history": None,
            "directory": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True
        mock_policy.enforce_dictionary_check = True
        mock_policy.enforce_username_check = True
        mock_policy.min_character_groups = 2
        mock_policy.min_characters_per_group = 1
        mock_policy.min_password_length = 12
        mock_policy.min_password_age = 0
        mock_policy.max_password_age = 0
        mock_policy.max_login_attempts = 5
        mock_policy.lockout_duration = 600000
        mock_policy.password_history = 0

        mock_get.return_value = Mock(status_code=200, items=[mock_policy])

        update_policy(mock_module, mock_array, "2.38", False)

        # No patch should be called - no changes
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdateQuotaPolicyBugFixes:
    """Test cases for quota policy bug fixes - quota_notifications assignment"""

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.patch_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyRuleQuotaPatch")
    @patch("plugins.modules.purefa_policy.PolicyrulequotapatchRules")
    @patch("plugins.modules.purefa_policy.human_to_bytes")
    def test_update_quota_notifications_with_none_value(
        self,
        mock_human,
        mock_rules,
        mock_rule_patch,
        mock_lv,
        mock_get,
        mock_patch,
        mock_check,
    ):
        """Test quota_notifications with 'none' in list normalizes to ['none'].
        Bug fix: code used == instead of = for assignment
        """
        mock_human.return_value = 100 * 1024 * 1024 * 1024  # 100GB

        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_limit": "100G",
            "quota_enforced": True,
            "quota_notifications": ["none", "warning"],  # Contains 'none'
            "directory": None,
            "ignore_usage": False,
            "rule_name": "rule1",  # Required for rule update path
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True

        mock_rule_item = Mock()
        mock_rule_item.name = "rule1"
        mock_rule_item.quota_limit = 100 * 1024 * 1024 * 1024  # 100GB
        mock_rule_item.enforced = True
        mock_rule_item.notifications = "warning"  # Different from 'none'

        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_quota
            Mock(
                status_code=200, items=[mock_rule_item]
            ),  # get_policies_quota_rules (for current_rules)
            Mock(
                status_code=200, items=[mock_rule_item]
            ),  # get_policies_quota_rules (for rule_name filter)
        ]
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        # After the fix, quota_notifications should be normalized to ['none']
        # The patch should be called to update the rule
        mock_patch.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_policy.check_response")
    @patch("plugins.modules.purefa_policy.post_with_context")
    @patch("plugins.modules.purefa_policy.get_with_context")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_policy.PolicyrulequotapostRules")
    @patch("plugins.modules.purefa_policy.PolicyRuleQuotaPost")
    def test_create_quota_rule_with_none_notification(
        self, mock_rule_post, mock_rules, mock_lv, mock_get, mock_post, mock_check
    ):
        """Test creating quota rule with 'none' in notifications.
        Bug fix: code used == instead of = when creating new rule
        """
        mock_module = Mock()
        mock_module.params = {
            "name": "quota_policy",
            "policy": "quota",
            "enabled": True,
            "quota_limit": "100G",
            "quota_enforced": True,
            "quota_notifications": ["none"],  # 'none' notification
            "directory": None,
            "ignore_usage": False,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_policy = Mock()
        mock_policy.enabled = True

        # No existing rule
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_policy]),  # get_policies_quota
            Mock(status_code=200, items=[]),  # get_directories_policies_quota
            Mock(status_code=200, items=[]),  # get_policies_quota_rules (empty)
        ]
        mock_post.return_value = Mock(status_code=200)

        update_policy(mock_module, mock_array, "2.38", False)

        # Should create a new rule with 'none' notification
        mock_post.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestPasswordPolicyVersionGates:
    """Version gating for password-policy parameters (issue #1030 / PR #1031)"""

    @patch("plugins.modules.purefa_policy.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_policy.get_array")
    @patch("plugins.modules.purefa_policy.AnsibleModule")
    @patch("plugins.modules.purefa_policy.LooseVersion", side_effect=LooseVersion)
    def test_max_password_age_requires_2_39(self, mock_lv, mock_am, mock_get_array):
        """max_password_age on a pre-2.39 array fails with a clear version error"""
        mock_module = Mock()
        mock_module.params = {
            "policy": "password",
            "max_password_age": "90d",
            "min_password_age": None,
            "lockout_duration": None,
            "state": "present",
            "quota_notifications": None,
        }
        mock_module.fail_json.side_effect = SystemExit
        mock_am.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        try:
            main()
        except SystemExit:
            pass

        msgs = [c.kwargs.get("msg", "") for c in mock_module.fail_json.call_args_list]
        assert any("max_password_age" in m and "2.39" in m for m in msgs)
