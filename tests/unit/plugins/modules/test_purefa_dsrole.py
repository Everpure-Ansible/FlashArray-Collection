# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_dsrole module."""

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

from plugins.modules.purefa_dsrole import (
    delete_role,
    create_role,
    update_role,
)


class TestDeleteRole:
    """Tests for delete_role function"""

    def test_delete_role_check_mode(self):
        """Test delete_role in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "role1", "context": ""}
        mock_module.check_mode = True
        mock_array = Mock()

        delete_role(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateRole:
    """Tests for create_role function"""

    def test_create_role_check_mode(self):
        """Test create_role in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "role1",
            "context": "",
            "group": "admins",
            "group_base": "ou=groups,dc=example,dc=com",
            "role": "array_admin",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        create_role(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_role_no_change(self):
        """Test create_role when group and group_base are empty"""
        mock_module = Mock()
        mock_module.params = {
            "name": "role1",
            "context": "",
            "group": "",
            "group_base": "",
            "role": "array_admin",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        create_role(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.post_with_context")
    def test_create_role_success(self, mock_post_with_context, mock_check_response):
        """Test create_role successfully creates"""
        mock_module = Mock()
        mock_module.params = {
            "name": "role1",
            "context": "",
            "group": "admins",
            "group_base": "ou=groups,dc=example,dc=com",
            "role": "array_admin",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_post_with_context.return_value = Mock(status_code=200)

        create_role(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateRole:
    """Tests for update_role function"""

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.patch_with_context")
    def test_update_role_delete_system_defined(
        self, mock_patch_with_context, mock_check_response
    ):
        """Test update_role deletes system-defined role"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "array_admin",
            "context": "",
            "state": "absent",
        }
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_role(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_role_delete_check_mode(self):
        """Test update_role delete in check mode"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "array_admin",
            "context": "",
            "state": "absent",
        }
        mock_module.check_mode = True
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_array = Mock()

        with pytest.raises(SystemExit):
            update_role(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dsrole.get_with_context")
    def test_update_role_system_role_no_change(self, mock_get_with_context):
        """Test update_role for system role when no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "array_admin",
            "context": "",
            "state": "present",
            "group": "admins",
            "group_base": "ou=groups,dc=example,dc=com",
            "role": "array_admin",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Mock current role with same values
        mock_role = Mock()
        mock_role.group = "admins"
        mock_role.group_base = "ou=groups,dc=example,dc=com"
        mock_get_with_context.return_value = Mock(items=[mock_role])

        update_role(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.patch_with_context")
    @patch("plugins.modules.purefa_dsrole.get_with_context")
    def test_update_role_custom_role_with_changes(
        self, mock_get_with_context, mock_patch_with_context, mock_check_response
    ):
        """Test update_role for custom role when changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "custom_role",
            "context": "",
            "state": "present",
            "group": "new-admins",
            "group_base": "ou=new-groups,dc=example,dc=com",
            "role": "storage_admin",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        # Mock current role with different values
        mock_role = Mock()
        mock_role.group = "old-admins"
        mock_role.group_base = "ou=old-groups,dc=example,dc=com"
        mock_role_ref = Mock()
        mock_role_ref.name = "array_admin"
        mock_role.role = mock_role_ref
        mock_get_with_context.return_value = Mock(items=[mock_role])

        update_role(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteRoleSuccess:
    """Tests for delete_role success paths"""

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.delete_with_context")
    def test_delete_role_success(self, mock_delete_with_context, mock_check_response):
        """Test delete_role successfully deletes"""
        mock_module = Mock()
        mock_module.params = {"name": "custom_role", "context": ""}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        delete_role(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.delete_with_context")
    def test_delete_role_older_api(self, mock_delete_with_context, mock_check_response):
        """Test delete_role with older API version"""
        mock_module = Mock()
        mock_module.params = {"name": "custom_role", "context": ""}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        delete_role(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateRoleSuccess:
    """Tests for create_role additional paths"""

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.post_with_context")
    @patch("plugins.modules.purefa_dsrole.DirectoryServiceRole")
    def test_create_role_older_policy_api(
        self, mock_ds_role, mock_post_with_context, mock_check_response
    ):
        """Test create_role with older policy API version"""
        mock_module = Mock()
        mock_module.params = {
            "name": "custom_role",
            "context": "",
            "group": "admins",
            "group_base": "ou=groups,dc=example,dc=com",
            "role": "array_admin",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = (
            "2.4"  # Older than POLICY_API_VERSION
        )
        mock_post_with_context.return_value = Mock(status_code=200)

        create_role(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateRoleWithContext:
    """Tests for create_role with context API"""

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.post_with_context")
    def test_create_role_with_context(
        self, mock_post_with_context, mock_check_response
    ):
        """Test create_role with context API version"""
        mock_module = Mock()
        mock_module.params = {
            "name": "custom_role",
            "context": "fleet-member",
            "group": "admins",
            "group_base": "ou=groups,dc=example,dc=com",
            "role": "array_admin",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.43"  # CONTEXT_VERSION or higher
        mock_post_with_context.return_value = Mock(status_code=200)

        create_role(mock_module, mock_array)

        # post_with_context is called, verify it was called
        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteRoleWithContext:
    """Tests for delete_role with context API"""

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.delete_with_context")
    def test_delete_role_with_context(
        self, mock_delete_with_context, mock_check_response
    ):
        """Test delete_role with context API version"""
        mock_module = Mock()
        mock_module.params = {"name": "custom_role", "context": "fleet-member"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        delete_role(mock_module, mock_array)

        # delete_with_context is called, verify it was called
        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateRoleSystemDefined:
    """Tests for update_role with system-defined roles"""

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.patch_with_context")
    @patch("plugins.modules.purefa_dsrole.get_with_context")
    def test_update_system_role_with_changes(
        self, mock_get_with_context, mock_patch_with_context, mock_check_response
    ):
        """Test update_role for system role when changes are needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "storage_admin",
            "context": "",
            "state": "present",
            "group": "new-storage-admins",
            "group_base": "ou=new-storage,dc=example,dc=com",
            "role": "storage_admin",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        # Mock current role with different values
        mock_role = Mock()
        mock_role.group = "old-storage-admins"
        mock_role.group_base = "ou=old-storage,dc=example,dc=com"
        mock_get_with_context.return_value = Mock(items=[mock_role])

        update_role(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dsrole.get_with_context")
    def test_update_custom_role_no_changes(self, mock_get_with_context):
        """Test update_role for custom role when no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "my_custom_role",
            "context": "",
            "state": "present",
            "group": "admins",
            "group_base": "ou=groups,dc=example,dc=com",
            "role": "readonly",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Mock current role with same values
        mock_role = Mock()
        mock_role.group = "admins"
        mock_role.group_base = "ou=groups,dc=example,dc=com"
        mock_role_ref = Mock()
        mock_role_ref.name = "readonly"
        mock_role.role = mock_role_ref
        mock_get_with_context.return_value = Mock(items=[mock_role])

        update_role(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.patch_with_context")
    @patch("plugins.modules.purefa_dsrole.get_with_context")
    def test_update_role_with_context_api(
        self, mock_get_with_context, mock_patch_with_context, mock_check_response
    ):
        """Test update_role with context API version"""
        mock_module = Mock()
        mock_module.params = {
            "name": "ops_admin",
            "context": "fleet-member",
            "state": "present",
            "group": "new-ops-admins",
            "group_base": "ou=new-ops,dc=example,dc=com",
            "role": "ops_admin",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        # Mock current role with different values
        mock_role = Mock()
        mock_role.group = "old-ops-admins"
        mock_role.group_base = "ou=old-ops,dc=example,dc=com"
        mock_get_with_context.return_value = Mock(items=[mock_role])

        update_role(mock_module, mock_array)

        # patch_with_context is called, verify it was called
        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestAccessPolicy:
    """Tests for binding a role to a custom management access policy"""

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.post_with_context")
    @patch("plugins.modules.purefa_dsrole.DirectoryServiceRolePost")
    def test_create_role_with_access_policy(
        self, mock_post_model, mock_post_with_context, mock_check_response
    ):
        """create_role uses management_access_policies (not role) for access_policy"""
        mock_module = Mock()
        mock_module.params = {
            "name": "realm-admins",
            "context": "",
            "group": "realmadmins",
            "group_base": "OU=PureGroups,OU=RealmAdmins",
            "role": None,
            "access_policy": "my-realm-policy",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.39"
        mock_post_with_context.return_value = Mock(status_code=200)

        create_role(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        model_kwargs = mock_post_model.call_args.kwargs
        assert "management_access_policies" in model_kwargs
        assert "role" not in model_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dsrole.check_response")
    @patch("plugins.modules.purefa_dsrole.patch_with_context")
    @patch("plugins.modules.purefa_dsrole.get_with_context")
    @patch("plugins.modules.purefa_dsrole.DirectoryServiceRole")
    def test_update_role_access_policy_change(
        self, mock_ds_model, mock_get, mock_patch, mock_check_response
    ):
        """update_role patches management_access_policies when the policy changes"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "realm-admins",
            "context": "",
            "state": "present",
            "group": "realmadmins",
            "group_base": "OU=PureGroups,OU=RealmAdmins",
            "role": None,
            "access_policy": "my-realm-policy",
        }
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_array = Mock()
        existing = Mock()
        existing.group = "realmadmins"
        existing.group_base = "OU=PureGroups,OU=RealmAdmins"
        old_policy = Mock()
        old_policy.name = "old-policy"
        existing.management_access_policies = [old_policy]
        mock_get.return_value = Mock(items=[existing])
        mock_patch.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_role(mock_module, mock_array)

        mock_patch.assert_called_once()
        model_kwargs = mock_ds_model.call_args.kwargs
        assert "management_access_policies" in model_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dsrole.patch_with_context")
    @patch("plugins.modules.purefa_dsrole.get_with_context")
    def test_update_role_access_policy_no_change(self, mock_get, mock_patch):
        """update_role is idempotent when the policy already matches"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "realm-admins",
            "context": "",
            "state": "present",
            "group": "realmadmins",
            "group_base": "OU=PureGroups,OU=RealmAdmins",
            "role": None,
            "access_policy": "my-realm-policy",
        }
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_array = Mock()
        existing = Mock()
        existing.group = "realmadmins"
        existing.group_base = "OU=PureGroups,OU=RealmAdmins"
        current_policy = Mock()
        current_policy.name = "my-realm-policy"
        existing.management_access_policies = [current_policy]
        mock_get.return_value = Mock(items=[existing])

        with pytest.raises(SystemExit):
            update_role(mock_module, mock_array)

        mock_patch.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)
