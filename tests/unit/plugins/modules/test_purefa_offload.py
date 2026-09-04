# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_offload module."""

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

from plugins.modules.purefa_offload import (
    get_target,
    delete_offload,
    create_offload,
    update_offload,
)


class TestGetTarget:
    """Tests for get_target function"""

    @patch("plugins.modules.purefa_offload.get_with_context")
    def test_get_target_exists(self, mock_get_with_context):
        """Test get_target returns target when it exists"""
        mock_module = Mock()
        mock_module.params = {"name": "offload1", "context": ""}
        mock_array = Mock()
        mock_target = Mock()
        mock_target.name = "offload1"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_target])

        result = get_target(mock_module, mock_array)

        assert result == mock_target

    @patch("plugins.modules.purefa_offload.get_with_context")
    def test_get_target_not_exists(self, mock_get_with_context):
        """Test get_target returns None when target doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=400, items=[])

        result = get_target(mock_module, mock_array)

        assert result is None


class TestDeleteOffload:
    """Tests for delete_offload function"""

    @patch("plugins.modules.purefa_offload.get_with_context")
    def test_delete_offload_check_mode(self, mock_get_with_context):
        """Test delete_offload in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "offload1", "context": ""}
        mock_module.check_mode = True
        mock_array = Mock()

        delete_offload(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_get_with_context.assert_not_called()

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    def test_delete_offload_success(self, mock_get_with_context, mock_check_response):
        """Test delete_offload successfully deletes"""
        mock_module = Mock()
        mock_module.params = {"name": "offload1", "context": ""}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_offload(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_with(changed=True)


class TestCreateOffload:
    """Tests for create_offload function"""

    def test_create_offload_check_mode(self):
        """Test create_offload in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "offload1", "protocol": "s3"}
        mock_module.check_mode = True
        mock_array = Mock()

        create_offload(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    @patch("plugins.modules.purefa_offload.OffloadS3")
    @patch("plugins.modules.purefa_offload.OffloadPost")
    def test_create_offload_s3(
        self, mock_offload_post, mock_offload_s3, mock_get_with_context, mock_check
    ):
        """Test create_offload with S3 protocol"""
        mock_module = Mock()
        mock_module.params = {
            "name": "offload1",
            "protocol": "s3",
            "access_key": "access123",
            "bucket": "mybucket",
            "secret": "secret123",
            "profile": None,
            "uri": "https://s3.example.com",
            "initialize": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_with_context.return_value = Mock(status_code=200)

        create_offload(mock_module, mock_array)

        mock_offload_s3.assert_called_once()
        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateOffload:
    """Tests for update_offload function"""

    def test_update_offload_no_changes(self):
        """Test update_offload with no changes needed"""
        mock_module = Mock()
        mock_module.params = {"name": "offload1"}
        mock_array = Mock()

        update_offload(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestCreateOffloadProtocols:
    """Test cases for create_offload with different protocols"""

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    @patch("plugins.modules.purefa_offload.OffloadGoogleCloud")
    @patch("plugins.modules.purefa_offload.OffloadPost")
    def test_create_offload_gcp(
        self, mock_offload_post, mock_offload_gcp, mock_get_with_context, mock_check
    ):
        """Test create_offload with GCP protocol"""
        mock_module = Mock()
        mock_module.params = {
            "name": "gcp-offload",
            "protocol": "gcp",
            "access_key": "access123",
            "bucket": "mybucket",
            "secret": "secret123",
            "profile": None,
            "initialize": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_with_context.return_value = Mock(status_code=200)

        create_offload(mock_module, mock_array)

        mock_offload_gcp.assert_called_once()
        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    @patch("plugins.modules.purefa_offload.OffloadAzure")
    @patch("plugins.modules.purefa_offload.OffloadPost")
    def test_create_offload_azure(
        self, mock_offload_post, mock_offload_azure, mock_get_with_context, mock_check
    ):
        """Test create_offload with Azure protocol"""
        mock_module = Mock()
        mock_module.params = {
            "name": "azure-offload",
            "protocol": "azure",
            "container": "mycontainer",
            "bucket": "mybucket",
            "secret": "secret123",
            "profile": None,
            "initialize": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_with_context.return_value = Mock(status_code=200)

        create_offload(mock_module, mock_array)

        mock_offload_azure.assert_called_once()
        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    @patch("plugins.modules.purefa_offload.OffloadNfs")
    @patch("plugins.modules.purefa_offload.OffloadPost")
    def test_create_offload_nfs(
        self, mock_offload_post, mock_offload_nfs, mock_get_with_context, mock_check
    ):
        """Test create_offload with NFS protocol"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs-offload",
            "protocol": "nfs",
            "share": "/mnt/share",
            "address": "nfs.example.com",
            "options": "rw,no_root_squash",
            "profile": None,
            "initialize": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_with_context.return_value = Mock(status_code=200)

        create_offload(mock_module, mock_array)

        mock_offload_nfs.assert_called_once()
        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    @patch("plugins.modules.purefa_offload.OffloadS3")
    @patch("plugins.modules.purefa_offload.OffloadPost")
    def test_create_offload_s3_with_profile(
        self, mock_offload_post, mock_offload_s3, mock_get_with_context, mock_check
    ):
        """Test create_offload with S3 protocol and profile"""
        mock_module = Mock()
        mock_module.params = {
            "name": "s3-offload",
            "protocol": "s3",
            "access_key": "access123",
            "bucket": "mybucket",
            "secret": "secret123",
            "profile": "my-profile",
            "uri": "https://s3.example.com",
            "auth_region": None,
            "initialize": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.25"
        mock_get_with_context.return_value = Mock(status_code=200)

        create_offload(mock_module, mock_array)

        mock_offload_s3.assert_called_once()
        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteOffloadSuccess:
    """Test cases for delete_offload success paths"""

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    def test_delete_offload_success(self, mock_get_with_context, mock_check_response):
        """Test successful offload deletion"""
        mock_module = Mock()
        mock_module.params = {"name": "offload1", "context": ""}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_offload(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateOffloadWithProfiles:
    """Test create_offload with different profiles"""

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    @patch("plugins.modules.purefa_offload.OffloadGoogleCloud")
    @patch("plugins.modules.purefa_offload.OffloadPost")
    def test_create_offload_gcp_with_profile(
        self, mock_offload_post, mock_offload_gcp, mock_get_with_context, mock_check
    ):
        """Test create_offload with GCP protocol and profile"""
        mock_module = Mock()
        mock_module.params = {
            "name": "gcp-offload",
            "protocol": "gcp",
            "access_key": "access123",
            "bucket": "mybucket",
            "secret": "secret123",
            "profile": "gcp",
            "initialize": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.25"
        mock_get_with_context.return_value = Mock(status_code=200)

        create_offload(mock_module, mock_array)

        mock_offload_gcp.assert_called_once()
        # Verify profile was passed
        call_kwargs = mock_offload_gcp.call_args
        assert "profile" in str(call_kwargs)

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    @patch("plugins.modules.purefa_offload.OffloadAzure")
    @patch("plugins.modules.purefa_offload.OffloadPost")
    def test_create_offload_azure_with_profile(
        self, mock_offload_post, mock_offload_azure, mock_get_with_context, mock_check
    ):
        """Test create_offload with Azure protocol and profile"""
        mock_module = Mock()
        mock_module.params = {
            "name": "azure-offload",
            "protocol": "azure",
            "container": "mycontainer",
            ".bucket": "mybucket",  # Note: module has a typo using .bucket
            "bucket": "mybucket",
            "secret": "secret123",
            "profile": "azure",
            "initialize": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.25"
        mock_get_with_context.return_value = Mock(status_code=200)

        create_offload(mock_module, mock_array)

        mock_offload_azure.assert_called_once()

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    @patch("plugins.modules.purefa_offload.OffloadS3")
    @patch("plugins.modules.purefa_offload.OffloadPost")
    def test_create_offload_s3_with_profile_and_auth_region(
        self, mock_offload_post, mock_offload_s3, mock_get_with_context, mock_check
    ):
        """Test create_offload with S3 protocol, profile and auth_region"""
        mock_module = Mock()
        mock_module.params = {
            "name": "s3-offload",
            "protocol": "s3",
            "access_key": "access123",
            "bucket": "mybucket",
            "secret": "secret123",
            "profile": "s3-aws",
            "uri": "https://s3.example.com",
            "auth_region": "us-east-1",
            "initialize": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.25"
        mock_get_with_context.return_value = Mock(status_code=200)

        create_offload(mock_module, mock_array)

        mock_offload_s3.assert_called_once()
        # Verify auth_region was passed
        call_kwargs = mock_offload_s3.call_args
        assert "auth_region" in str(call_kwargs)

    @patch("plugins.modules.purefa_offload.check_response")
    @patch("plugins.modules.purefa_offload.get_with_context")
    @patch("plugins.modules.purefa_offload.OffloadNfs")
    @patch("plugins.modules.purefa_offload.OffloadPost")
    def test_create_offload_nfs_with_profile(
        self, mock_offload_post, mock_offload_nfs, mock_get_with_context, mock_check
    ):
        """Test create_offload with NFS protocol and profile"""
        mock_module = Mock()
        mock_module.params = {
            "name": "nfs-offload",
            "protocol": "nfs",
            "share": "/mnt/share",
            "address": "nfs.example.com",
            "options": "rw,no_root_squash",
            "profile": "nfs-flashblade",
            "initialize": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.25"
        mock_get_with_context.return_value = Mock(status_code=200)

        create_offload(mock_module, mock_array)

        mock_offload_nfs.assert_called_once()


class TestMainFunction:
    """Tests for main function"""

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    @patch("plugins.modules.purefa_offload.get_target")
    @patch("plugins.modules.purefa_offload.create_offload")
    def test_main_create_offload(
        self, mock_create, mock_get_target, mock_get_array, mock_ansible_module
    ):
        """Test main() creates offload when target doesn't exist"""
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "test-offload",
            "state": "present",
            "protocol": "s3",
            "access_key": "access123",
            "secret": "secret123",
            "bucket": "mybucket",
            "account": "myaccount",
            "address": "10.0.0.1",
            "share": "/share",
            "profile": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_array.get_offloads.return_value = Mock(items=[])
        mock_get_array.return_value = mock_array
        mock_get_target.return_value = None

        main()

        mock_create.assert_called_once()

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    @patch("plugins.modules.purefa_offload.get_target")
    @patch("plugins.modules.purefa_offload.update_offload")
    def test_main_update_offload(
        self, mock_update, mock_get_target, mock_get_array, mock_ansible_module
    ):
        """Test main() updates offload when target exists"""
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "test-offload",
            "state": "present",
            "protocol": "s3",
            "access_key": "access123",
            "secret": "secret123",
            "bucket": "mybucket",
            "account": "myaccount",
            "address": "10.0.0.1",
            "share": "/share",
            "profile": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array
        mock_target = Mock()
        mock_get_target.return_value = mock_target

        main()

        mock_update.assert_called_once()

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    @patch("plugins.modules.purefa_offload.get_target")
    @patch("plugins.modules.purefa_offload.delete_offload")
    def test_main_delete_offload(
        self, mock_delete, mock_get_target, mock_get_array, mock_ansible_module
    ):
        """Test main() deletes offload when state=absent and target exists"""
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "test-offload",
            "state": "absent",
            "protocol": "s3",
            "bucket": "mybucket",
            "profile": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array
        mock_target = Mock()
        mock_get_target.return_value = mock_target

        main()

        mock_delete.assert_called_once()

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    @patch("plugins.modules.purefa_offload.get_target")
    def test_main_absent_not_exists(
        self, mock_get_target, mock_get_array, mock_ansible_module
    ):
        """Test main() does nothing when state=absent and target doesn't exist"""
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "test-offload",
            "state": "absent",
            "protocol": "s3",
            "bucket": "mybucket",
            "profile": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array
        mock_get_target.return_value = None

        main()

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_offload.HAS_PURESTORAGE", False)
    @patch("plugins.modules.purefa_offload.AnsibleModule")
    def test_main_no_purestorage(self, mock_ansible_module):
        """Test main() fails when py-pure-client is not installed"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    def test_main_nfs_missing_params(self, mock_ansible_module):
        """Test main() fails when NFS protocol missing required params"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "nfs-offload",
            "state": "present",
            "protocol": "nfs",
            "address": None,
            "share": None,
            "profile": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "address and share are required" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    def test_main_s3_missing_params(self, mock_ansible_module):
        """Test main() fails when S3 protocol missing required params"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "s3-offload",
            "state": "present",
            "protocol": "s3",
            "access_key": None,
            "secret": None,
            "bucket": None,
            "profile": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "access_key, secret, and bucket are required" in str(
            mock_module.fail_json.call_args
        )

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    def test_main_gcp_missing_params(self, mock_ansible_module):
        """Test main() fails when GCP protocol missing required params"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "gcp-offload",
            "state": "present",
            "protocol": "gcp",
            "access_key": None,
            "secret": None,
            "bucket": None,
            "profile": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "access_key, secret, and bucket are required" in str(
            mock_module.fail_json.call_args
        )

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    def test_main_azure_missing_params(self, mock_ansible_module):
        """Test main() fails when Azure protocol missing required params"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "azure-offload",
            "state": "present",
            "protocol": "azure",
            "account": None,
            "secret": None,
            "profile": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "account and secret are required" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    @patch("plugins.modules.purefa_offload.get_target")
    @patch("plugins.modules.purefa_offload.delete_offload")
    def test_main_absent_no_validation(
        self, mock_delete, mock_get_target, mock_get_array, mock_ansible_module
    ):
        """Test main() skips param validation when state=absent"""
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "nfs-offload",
            "state": "absent",
            "protocol": "nfs",
            "address": None,  # Missing but shouldn't matter for absent
            "share": None,
            "profile": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_get_array.return_value = mock_array
        mock_target = Mock()
        mock_get_target.return_value = mock_target

        main()

        # Should not fail - validation is skipped for state=absent
        mock_delete.assert_called_once()

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    def test_main_nfs_not_supported_66(self, mock_get_array, mock_ansible_module):
        """Test main() fails when NFS protocol used with FA 6.6+"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "nfs-offload",
            "state": "present",
            "protocol": "nfs",
            "address": "10.0.0.1",
            "share": "/share",
            "access_key": "access123",
            "secret": "secret123",
            "bucket": "mybucket",
            "account": "myaccount",
            "profile": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.27"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    def test_main_invalid_target_name(self, mock_get_array, mock_ansible_module):
        """Test main() fails with invalid target name"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "!!invalid!!",
            "state": "present",
            "protocol": "s3",
            "access_key": "access123",
            "secret": "secret123",
            "bucket": "mybucket",
            "account": "myaccount",
            "address": "10.0.0.1",
            "share": "/share",
            "profile": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    def test_main_invalid_bucket_name(self, mock_get_array, mock_ansible_module):
        """Test main() fails with invalid bucket name for S3"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "s3-offload",
            "state": "present",
            "protocol": "s3",
            "access_key": "access123",
            "secret": "secret123",
            "bucket": "!!INVALID!!",
            "account": "myaccount",
            "address": "10.0.0.1",
            "share": "/share",
            "profile": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    @patch("plugins.modules.purefa_offload.get_target")
    @patch("plugins.modules.purefa_offload.update_offload")
    def test_main_warns_invalid_profile(
        self, mock_update, mock_get_target, mock_get_array, mock_ansible_module
    ):
        """Test main() warns when profile doesn't match protocol"""
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "s3-offload",
            "state": "present",
            "protocol": "s3",
            "access_key": "access123",
            "secret": "secret123",
            "bucket": "mybucket",
            "account": "myaccount",
            "address": "10.0.0.1",
            "share": "/share",
            "profile": "azure",  # Wrong profile for s3
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array
        mock_target = Mock()
        mock_get_target.return_value = mock_target

        # Will call warn and set profile to None
        main()

        mock_module.warn.assert_called_once()
        assert mock_module.params["profile"] is None

    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    @patch("plugins.modules.purefa_offload.get_target")
    def test_main_offload_limit_exceeded(
        self, mock_get_target, mock_get_array, mock_ansible_module
    ):
        """Test main() fails when offload limit would be exceeded"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "new-offload",
            "state": "present",
            "protocol": "s3",
            "access_key": "access123",
            "secret": "secret123",
            "bucket": "mybucket",
            "account": "myaccount",
            "address": "10.0.0.1",
            "share": "/share",
            "profile": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        # Return one existing offload (limit is 1)
        existing_offload = Mock()
        existing_offload.protocol = "s3"
        mock_array.get_offloads.return_value = Mock(items=[existing_offload])
        mock_get_array.return_value = mock_array
        mock_get_target.return_value = None

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_offload.MULTIOFFLOAD_LIMIT", 2)
    @patch("plugins.modules.purefa_offload.AnsibleModule")
    @patch("plugins.modules.purefa_offload.get_array")
    @patch("plugins.modules.purefa_offload.get_target")
    def test_main_different_protocol_fails(
        self, mock_get_target, mock_get_array, mock_ansible_module
    ):
        """Test main() fails when new offload has different protocol than existing"""
        import pytest
        from plugins.modules.purefa_offload import main

        mock_module = Mock()
        mock_module.params = {
            "name": "new-offload",
            "state": "present",
            "protocol": "azure",
            "access_key": "access123",
            "secret": "secret123",
            "bucket": "mybucket",
            "account": "myaccount",
            "address": "10.0.0.1",
            "share": "/share",
            "profile": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        # Return existing offload with different protocol (need limit > 1)
        existing_offload = Mock()
        existing_offload.protocol = "s3"
        mock_array.get_offloads.return_value = Mock(items=[existing_offload])
        mock_get_array.return_value = mock_array
        mock_get_target.return_value = None

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
