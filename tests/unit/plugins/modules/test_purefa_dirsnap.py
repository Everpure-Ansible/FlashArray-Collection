# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_dirsnap module."""

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

from plugins.modules.purefa_dirsnap import (
    eradicate_snap,
    delete_snap,
    update_snap,
    create_snap,
)


class TestEradicateSnap:
    """Tests for eradicate_snap function"""

    def test_eradicate_snap_check_mode(self):
        """Test eradicate_snap in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap1",
            "filesystem": "fs1",
            "directory": "dir1",
            "context": "",
            "client": "client1",
            "suffix": "snap",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        eradicate_snap(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteSnap:
    """Tests for delete_snap function"""

    def test_delete_snap_check_mode(self):
        """Test delete_snap in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap1",
            "filesystem": "fs1",
            "directory": "dir1",
            "context": "",
            "eradicate": False,
            "client": "client1",
            "suffix": "snap",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        delete_snap(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSnap:
    """Tests for update_snap function"""

    def test_update_snap_check_mode_no_rename(self):
        """Test update_snap in check mode when recovering a destroyed snapshot"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "rename": False,
            "keep_for": None,
            "new_client": None,
            "new_suffix": None,
        }
        mock_module.check_mode = True
        mock_array = Mock()

        snap_detail = Mock()
        snap_detail.destroyed = True

        update_snap(mock_module, mock_array, snap_detail)

        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_snap_check_mode_with_rename(self):
        """Test update_snap in check mode with rename"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "rename": True,
            "keep_for": None,
            "new_client": "new_client",
            "new_suffix": "new_snap",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        snap_detail = Mock()
        snap_detail.destroyed = False

        update_snap(mock_module, mock_array, snap_detail)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateSnap:
    """Tests for create_snap function"""

    def test_create_snap_check_mode(self):
        """Test create_snap in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "snap1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "keep_for": None,
        }
        mock_module.check_mode = True
        mock_array = Mock()

        create_snap(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dirsnap.check_response")
    @patch("plugins.modules.purefa_dirsnap.DirectorySnapshotPost")
    @patch("plugins.modules.purefa_dirsnap.post_with_context")
    def test_create_snap_success(
        self, mock_post_with_context, mock_snap_post, mock_check_response
    ):
        """Test create_snap successfully creates a snapshot"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "keep_for": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_post_with_context.return_value = Mock(status_code=200)

        create_snap(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dirsnap.check_response")
    @patch("plugins.modules.purefa_dirsnap.DirectorySnapshotPost")
    @patch("plugins.modules.purefa_dirsnap.post_with_context")
    def test_create_snap_with_keep_for(
        self, mock_post_with_context, mock_snap_post, mock_check_response
    ):
        """Test create_snap with keep_for retention"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "keep_for": 3600,  # 1 hour in range
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_post_with_context.return_value = Mock(status_code=200)

        create_snap(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicateSnapSuccess:
    """Tests for eradicate_snap function success paths"""

    @patch("plugins.modules.purefa_dirsnap.check_response")
    @patch("plugins.modules.purefa_dirsnap.delete_with_context")
    def test_eradicate_snap_success(
        self, mock_delete_with_context, mock_check_response
    ):
        """Test eradicate_snap successfully eradicates a snapshot"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        eradicate_snap(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dirsnap.check_response")
    @patch("plugins.modules.purefa_dirsnap.delete_with_context")
    def test_eradicate_snap_with_context(
        self, mock_delete_with_context, mock_check_response
    ):
        """Test eradicate_snap with context (API >= 2.42)"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "fleet-member",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        eradicate_snap(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteSnapSuccess:
    """Tests for delete_snap function success paths"""

    @patch("plugins.modules.purefa_dirsnap.check_response")
    @patch("plugins.modules.purefa_dirsnap.DirectorySnapshotPatch")
    @patch("plugins.modules.purefa_dirsnap.patch_with_context")
    def test_delete_snap_success(
        self, mock_patch_with_context, mock_snap_patch, mock_check_response
    ):
        """Test delete_snap successfully deletes a snapshot"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "eradicate": False,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        delete_snap(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dirsnap.eradicate_snap")
    @patch("plugins.modules.purefa_dirsnap.check_response")
    @patch("plugins.modules.purefa_dirsnap.DirectorySnapshotPatch")
    @patch("plugins.modules.purefa_dirsnap.patch_with_context")
    def test_delete_snap_with_eradicate(
        self,
        mock_patch_with_context,
        mock_snap_patch,
        mock_check_response,
        mock_eradicate_snap,
    ):
        """Test delete_snap with eradicate=True calls eradicate_snap"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "eradicate": True,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        delete_snap(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_eradicate_snap.assert_called_once_with(mock_module, mock_array)


class TestUpdateSnapSuccess:
    """Tests for update_snap function success paths"""

    @patch("plugins.modules.purefa_dirsnap.check_response")
    @patch("plugins.modules.purefa_dirsnap.DirectorySnapshotPatch")
    @patch("plugins.modules.purefa_dirsnap.patch_with_context")
    def test_update_snap_recover_destroyed(
        self, mock_patch_with_context, mock_snap_patch, mock_check_response
    ):
        """Test update_snap recovers a destroyed snapshot"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "rename": False,
            "keep_for": None,
            "new_client": None,
            "new_suffix": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        snap_detail = Mock()
        snap_detail.destroyed = True

        update_snap(mock_module, mock_array, snap_detail)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dirsnap.check_response")
    @patch("plugins.modules.purefa_dirsnap.DirectorySnapshotPatch")
    @patch("plugins.modules.purefa_dirsnap.patch_with_context")
    def test_update_snap_rename_success(
        self, mock_patch_with_context, mock_snap_patch, mock_check_response
    ):
        """Test update_snap renames a snapshot"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "rename": True,
            "keep_for": None,
            "new_client": "newclient",
            "new_suffix": "newsnap",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        snap_detail = Mock()
        snap_detail.destroyed = False

        update_snap(mock_module, mock_array, snap_detail)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dirsnap.check_response")
    @patch("plugins.modules.purefa_dirsnap.DirectorySnapshotPatch")
    @patch("plugins.modules.purefa_dirsnap.patch_with_context")
    def test_update_snap_set_keep_for(
        self, mock_patch_with_context, mock_snap_patch, mock_check_response
    ):
        """Test update_snap sets keep_for retention time"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "rename": False,
            "keep_for": 3600,  # 1 hour
            "new_client": None,
            "new_suffix": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        snap_detail = Mock()
        snap_detail.destroyed = False

        update_snap(mock_module, mock_array, snap_detail)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_snap_keep_for_out_of_range(self):
        """Test update_snap fails when keep_for is out of range"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "rename": False,
            "keep_for": 100,  # Too small, must be >= 300
            "new_client": None,
            "new_suffix": None,
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()

        snap_detail = Mock()
        snap_detail.destroyed = False

        with pytest.raises(SystemExit):
            update_snap(mock_module, mock_array, snap_detail)

        mock_module.fail_json.assert_called_once_with(
            msg="keep_for not in range of 300 - 31536000"
        )

    def test_update_snap_no_changes(self):
        """Test update_snap with no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "rename": False,
            "keep_for": None,
            "new_client": None,
            "new_suffix": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()

        snap_detail = Mock()
        snap_detail.destroyed = False  # Not destroyed, no rename, no keep_for

        update_snap(mock_module, mock_array, snap_detail)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdateSnapRenameVariations:
    """Test update_snap rename with different client/suffix combinations"""

    def test_update_snap_rename_new_client_only(self):
        """Test update_snap rename with only new_client"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "rename": True,
            "keep_for": None,
            "new_client": "newclient",
            "new_suffix": None,  # Keep original suffix
        }
        mock_module.check_mode = True
        mock_array = Mock()

        snap_detail = Mock()
        snap_detail.destroyed = False

        update_snap(mock_module, mock_array, snap_detail)

        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_snap_rename_new_suffix_only(self):
        """Test update_snap rename with only new_suffix"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "client": "client1",
            "suffix": "snap",
            "context": "",
            "rename": True,
            "keep_for": None,
            "new_client": None,  # Keep original client
            "new_suffix": "newsuffix",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        snap_detail = Mock()
        snap_detail.destroyed = False

        update_snap(mock_module, mock_array, snap_detail)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for main() function"""

    @patch("plugins.modules.purefa_dirsnap.LooseVersion")
    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_no_purestorage_sdk(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails when purestorage SDK not available"""
        import pytest
        from plugins.modules.purefa_dirsnap import main

        with patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", False):
            mock_module = Mock()
            mock_module.params = {"rename": False}
            mock_module.fail_json.side_effect = SystemExit(1)
            mock_ansible_module.return_value = mock_module

            with pytest.raises(SystemExit):
                main()

            mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_dirsnap.LooseVersion")
    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_rename_without_new_values(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails when rename is True but no new_client or new_suffix"""
        import pytest
        from plugins.modules.purefa_dirsnap import main

        mock_module = Mock()
        mock_module.params = {
            "rename": True,
            "new_client": None,
            "new_suffix": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_dirsnap.LooseVersion")
    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_api_version_too_old(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails when API version is too old"""
        import pytest
        from plugins.modules.purefa_dirsnap import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = {
            "rename": False,
            "suffix": "test",
            "new_suffix": None,
            "client": "client1",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Too old
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_rename_api_version_too_old(self, mock_ansible_module, mock_get_array):
        """Test main() fails when rename is requested but API version too old"""
        import pytest
        from plugins.modules.purefa_dirsnap import main

        mock_module = Mock()
        mock_module.params = {
            "rename": True,
            "new_client": "newclient",
            "new_suffix": None,
            "suffix": "test-suffix",
            "client": "client1",
            "state": "present",
            "filesystem": "fs1",
            "name": "dir1",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = (
            "2.9"  # Good for base (>=2.2), but <2.10 for rename
        )
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_dirsnap.LooseVersion")
    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_invalid_suffix_pattern(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails with invalid suffix pattern"""
        import pytest
        from plugins.modules.purefa_dirsnap import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = {
            "rename": False,
            "suffix": "12345",  # Invalid - must contain letters
            "new_suffix": None,
            "client": "client1",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_dirsnap.LooseVersion")
    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_invalid_new_suffix_pattern(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails with invalid new_suffix pattern"""
        import pytest
        from plugins.modules.purefa_dirsnap import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = {
            "rename": False,
            "suffix": "valid-suffix",
            "new_suffix": "12345",  # Invalid - must contain letters
            "client": "client1",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_dirsnap.LooseVersion")
    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_invalid_client_pattern(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails with invalid client pattern"""
        import pytest
        from plugins.modules.purefa_dirsnap import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = {
            "rename": False,
            "suffix": None,
            "new_suffix": None,
            "client": "12345",  # Invalid - must contain letters
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_dirsnap.get_with_context")
    @patch("plugins.modules.purefa_dirsnap.LooseVersion")
    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_directory_not_found(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_get_with_context,
    ):
        """Test main() fails when directory does not exist"""
        import pytest
        from plugins.modules.purefa_dirsnap import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = {
            "rename": False,
            "suffix": None,
            "new_suffix": None,
            "client": "client1",
            "filesystem": "fs1",
            "name": "nonexistent-dir",
            "state": "present",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_get_array.return_value = mock_array

        # Directory doesn't exist
        mock_get_with_context.return_value = Mock(total_item_count=0)

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_dirsnap.create_snap")
    @patch("plugins.modules.purefa_dirsnap.get_with_context")
    @patch("plugins.modules.purefa_dirsnap.LooseVersion")
    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_create_snap(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_get_with_context,
        mock_create_snap,
    ):
        """Test main() calls create_snap when state=present and snapshot doesn't exist"""
        from plugins.modules.purefa_dirsnap import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = {
            "rename": False,
            "suffix": None,
            "new_suffix": None,
            "client": "client1",
            "filesystem": "fs1",
            "name": "dir1",
            "state": "present",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_get_array.return_value = mock_array

        # Directory exists
        mock_get_with_context.return_value = Mock(total_item_count=1)

        main()

        mock_create_snap.assert_called_once()

    @patch("plugins.modules.purefa_dirsnap.LooseVersion")
    @patch("plugins.modules.purefa_dirsnap.get_array")
    @patch("plugins.modules.purefa_dirsnap.AnsibleModule")
    @patch("plugins.modules.purefa_dirsnap.HAS_PURESTORAGE", True)
    def test_main_no_change(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() exits with no change when no action needed"""
        from plugins.modules.purefa_dirsnap import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.params = {
            "rename": False,
            "suffix": "snap",
            "new_suffix": None,
            "client": "client1",
            "filesystem": "fs1",
            "name": "dir1",
            "state": "absent",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        # Directory exists
        mock_array.get_directories.return_value = Mock(
            status_code=200, total_item_count=1
        )
        # Snapshot doesn't exist - nothing to delete
        mock_array.get_directory_snapshots.return_value = Mock(
            status_code=200, total_item_count=0
        )
        mock_get_array.return_value = mock_array

        main()

        mock_module.exit_json.assert_called_with(changed=False)
