# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_directory module."""

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
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.error_handlers"
] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    MagicMock()
)

from plugins.modules.purefa_directory import (
    delete_dir,
    rename_dir,
    rename_target,
    check_renamed_dir,
    create_dir,
)


class TestDeleteDir:
    """Tests for delete_dir function"""

    @patch("plugins.modules.purefa_directory.delete_with_context")
    def test_delete_dir_check_mode(self, mock_delete):
        """Test delete_dir in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "dir1", "filesystem": "fs1", "context": ""}
        mock_module.check_mode = True
        mock_array = Mock()

        delete_dir(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_delete.assert_not_called()

    @patch("plugins.modules.purefa_directory.check_response")
    @patch("plugins.modules.purefa_directory.delete_with_context")
    def test_delete_dir_success(self, mock_delete, mock_check):
        """Test delete_dir successfully deletes directory"""
        mock_module = Mock()
        mock_module.params = {"name": "dir1", "filesystem": "fs1", "context": ""}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_delete.return_value = Mock(status_code=200)

        delete_dir(mock_module, mock_array)

        mock_delete.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenameDir:
    """Tests for rename_dir function"""

    @patch("plugins.modules.purefa_directory.check_response")
    @patch("plugins.modules.purefa_directory.patch_with_context")
    @patch("plugins.modules.purefa_directory.get_with_context")
    def test_rename_dir_success(self, mock_get, mock_patch, mock_check):
        """Test rename_dir successfully renames directory"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "rename": "dir2",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=400)  # Target not exists
        mock_patch.return_value = Mock(status_code=200)

        rename_dir(mock_module, mock_array)

        mock_patch.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_directory.get_with_context")
    def test_rename_dir_target_exists(self, mock_get):
        """Test rename_dir fails when target exists"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "rename": "dir2",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=200)  # Target exists

        rename_dir(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestCreateDir:
    """Tests for create_dir function"""

    @patch("plugins.modules.purefa_directory.post_with_context")
    @patch("plugins.modules.purefa_directory.get_with_context")
    def test_create_dir_check_mode(self, mock_get, mock_post):
        """Test create_dir in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "path": None,
            "context": "",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_get.return_value = Mock(items=[])

        create_dir(mock_module, mock_array)

        mock_post.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_directory.check_response")
    @patch("plugins.modules.purefa_directory.post_with_context")
    @patch("plugins.modules.purefa_directory.get_with_context")
    def test_create_dir_success(self, mock_get, mock_post, mock_check):
        """Test create_dir successfully creates directory"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "path": "/dir1",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get.return_value = Mock(items=[])
        mock_post.return_value = Mock(status_code=200)

        create_dir(mock_module, mock_array)

        mock_post.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_directory.get_with_context")
    def test_create_dir_path_exists(self, mock_get):
        """Test create_dir fails when path exists"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "path": "dir1",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Mock existing directory with same path
        mock_existing_dir = Mock()
        mock_existing_dir.path = "/dir1"
        mock_get.return_value = Mock(items=[mock_existing_dir])

        create_dir(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestMain:
    """Tests for main function"""

    @patch("plugins.modules.purefa_directory.HAS_PURESTORAGE", False)
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_missing_purestorage(self, mock_ansible_module):
        """Test main fails when pypureclient is not installed"""
        from plugins.modules.purefa_directory import main

        mock_module = Mock()
        mock_module.params = {}
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        import plugins.modules.purefa_directory as dir_module

        original_has = dir_module.HAS_PURESTORAGE
        dir_module.HAS_PURESTORAGE = False

        try:
            with pytest.raises(SystemExit):
                main()
            mock_module.fail_json.assert_called_once_with(
                msg="py-pure-client sdk is required for this module"
            )
        finally:
            dir_module.HAS_PURESTORAGE = original_has

    @patch("plugins.modules.purefa_directory.create_dir")
    @patch("plugins.modules.purefa_directory.get_with_context")
    @patch("plugins.modules.purefa_directory.get_array")
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_create_directory(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_create_dir,
    ):
        """Test main creates directory when it doesn't exist"""
        from plugins.modules.purefa_directory import main

        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "filesystem": "fs1",
            "name": "dir1",
            "path": "/dir1",
            "rename": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        # First call: get_file_systems returns success
        fs_response = Mock()
        fs_response.status_code = 200
        fs_mock = Mock()
        fs_mock.destroyed = False
        fs_response.items = [fs_mock]

        # Second call: get_directories returns 404 (dir doesn't exist)
        dir_response = Mock()
        dir_response.status_code = 404

        mock_get_with_context.side_effect = [fs_response, dir_response]

        main()

        mock_create_dir.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_directory.get_with_context")
    @patch("plugins.modules.purefa_directory.get_array")
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_filesystem_not_found(
        self, mock_ansible_module, mock_get_array, mock_get_with_context
    ):
        """Test main fails when filesystem doesn't exist"""
        from plugins.modules.purefa_directory import main

        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "filesystem": "fs1",
            "name": "dir1",
            "path": "/dir1",
            "rename": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        # Filesystem not found
        fs_response = Mock()
        fs_response.status_code = 404
        mock_get_with_context.return_value = fs_response

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_directory.rename_dir")
    @patch("plugins.modules.purefa_directory.get_with_context")
    @patch("plugins.modules.purefa_directory.get_array")
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_rename_directory(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_rename_dir,
    ):
        """Test main renames directory when it exists and rename param is set"""
        from plugins.modules.purefa_directory import main

        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "filesystem": "fs1",
            "name": "dir1",
            "path": "/dir1",
            "rename": "dir2",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        # Filesystem exists and not destroyed
        fs_response = Mock()
        fs_response.status_code = 200
        fs_mock = Mock()
        fs_mock.destroyed = False
        fs_response.items = [fs_mock]

        # Directory exists
        dir_response = Mock()
        dir_response.status_code = 200

        mock_get_with_context.side_effect = [fs_response, dir_response]

        main()

        mock_rename_dir.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_directory.delete_dir")
    @patch("plugins.modules.purefa_directory.get_with_context")
    @patch("plugins.modules.purefa_directory.get_array")
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_delete_directory(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_delete_dir,
    ):
        """Test main deletes directory when state=absent and dir exists"""
        from plugins.modules.purefa_directory import main

        mock_module = Mock()
        mock_module.params = {
            "state": "absent",
            "filesystem": "fs1",
            "name": "dir1",
            "path": "/dir1",
            "rename": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        # Filesystem exists
        fs_response = Mock()
        fs_response.status_code = 200
        fs_mock = Mock()
        fs_mock.destroyed = False
        fs_response.items = [fs_mock]

        # Directory exists
        dir_response = Mock()
        dir_response.status_code = 200

        mock_get_with_context.side_effect = [fs_response, dir_response]

        main()

        mock_delete_dir.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_directory.get_with_context")
    @patch("plugins.modules.purefa_directory.get_array")
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_no_change_absent_not_exists(
        self, mock_ansible_module, mock_get_array, mock_get_with_context
    ):
        """Test main reports no change when state=absent and dir doesn't exist"""
        from plugins.modules.purefa_directory import main

        mock_module = Mock()
        mock_module.params = {
            "state": "absent",
            "filesystem": "fs1",
            "name": "dir1",
            "path": "/dir1",
            "rename": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        # Filesystem exists
        fs_response = Mock()
        fs_response.status_code = 200
        fs_mock = Mock()
        fs_mock.destroyed = False
        fs_response.items = [fs_mock]

        # Directory doesn't exist
        dir_response = Mock()
        dir_response.status_code = 404

        mock_get_with_context.side_effect = [fs_response, dir_response]

        main()

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_directory.get_with_context")
    @patch("plugins.modules.purefa_directory.get_array")
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_no_change_present_exists_no_rename(
        self, mock_ansible_module, mock_get_array, mock_get_with_context
    ):
        """Test main reports no change when dir exists and no rename specified"""
        from plugins.modules.purefa_directory import main

        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "filesystem": "fs1",
            "name": "dir1",
            "path": "/dir1",
            "rename": None,  # No rename
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_get_array.return_value = mock_array

        # Filesystem exists
        fs_response = Mock()
        fs_response.status_code = 200
        fs_mock = Mock()
        fs_mock.destroyed = False
        fs_response.items = [fs_mock]

        # Directory exists
        dir_response = Mock()
        dir_response.status_code = 200

        mock_get_with_context.side_effect = [fs_response, dir_response]

        main()

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestRenameCheckMode:
    """Tests for rename_dir in check mode"""

    @patch("plugins.modules.purefa_directory.get_with_context")
    def test_rename_dir_check_mode(self, mock_get):
        """Test rename_dir in check mode reports changed=True without making API call"""
        mock_module = Mock()
        mock_module.params = {
            "name": "dir1",
            "filesystem": "fs1",
            "rename": "dir2",
            "context": "",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=400)  # Target not exists

        rename_dir(mock_module, mock_array)

        # In check mode, should report changed=True but not make the patch call
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenameTarget:
    """Test cases for rename_target function"""

    def test_rename_target_qualifies_with_filesystem(self):
        """Test rename_target prefixes the target with the file system"""
        mock_module = Mock()
        mock_module.params = {"filesystem": "fs1", "name": "dir1", "rename": "dir2"}

        assert rename_target(mock_module) == "fs1:dir2"


class TestCheckRenamedDir:
    """Test cases for check_renamed_dir function

    This is the second run of a rename task, when the source directory has
    already gone.
    """

    @patch("plugins.modules.purefa_directory.get_with_context")
    def test_check_renamed_dir_already_renamed(self, mock_get):
        """Test check_renamed_dir reports no change once the target is there"""
        mock_module = Mock()
        mock_module.params = {
            "filesystem": "fs1",
            "name": "dir1",
            "rename": "dir2",
            "context": "",
        }
        mock_array = Mock()
        mock_target = Mock()
        mock_target.destroyed = False
        mock_get.return_value = Mock(status_code=200, items=[mock_target])

        check_renamed_dir(mock_module, mock_array)

        assert mock_get.call_args[1]["names"] == ["fs1:dir2"]
        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_module.fail_json.assert_not_called()

    @patch("plugins.modules.purefa_directory.get_with_context")
    def test_check_renamed_dir_neither_exists_fails(self, mock_get):
        """Test check_renamed_dir fails rather than creating the source"""
        mock_module = Mock()
        mock_module.params = {
            "filesystem": "fs1",
            "name": "dir1",
            "rename": "dir2",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=404)

        with pytest.raises(SystemExit):
            check_renamed_dir(mock_module, mock_array)

        assert "not found to rename" in mock_module.fail_json.call_args[1]["msg"]
        mock_module.exit_json.assert_not_called()

    @patch("plugins.modules.purefa_directory.get_with_context")
    def test_check_renamed_dir_target_destroyed_fails(self, mock_get):
        """Test check_renamed_dir fails when the target is in the trash"""
        mock_module = Mock()
        mock_module.params = {
            "filesystem": "fs1",
            "name": "dir1",
            "rename": "dir2",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_target = Mock()
        mock_target.destroyed = True
        mock_get.return_value = Mock(status_code=200, items=[mock_target])

        with pytest.raises(SystemExit):
            check_renamed_dir(mock_module, mock_array)

        assert "destroyed state" in mock_module.fail_json.call_args[1]["msg"]
        mock_module.exit_json.assert_not_called()


class TestMainRenameIdempotency:
    """Test that a rename task run twice changes once and then reports no change"""

    @staticmethod
    def _module(mock_ansible_module, rename="dir2"):
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "filesystem": "fs1",
            "name": "dir1",
            "path": None,
            "rename": rename,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        return mock_module

    @staticmethod
    def _responses(dir_status):
        fs_response = Mock(status_code=200)
        fs_mock = Mock()
        fs_mock.destroyed = False
        fs_response.items = [fs_mock]
        return [fs_response, Mock(status_code=dir_status)]

    @patch("plugins.modules.purefa_directory.check_renamed_dir")
    @patch("plugins.modules.purefa_directory.create_dir")
    @patch("plugins.modules.purefa_directory.rename_dir")
    @patch("plugins.modules.purefa_directory.get_with_context")
    @patch("plugins.modules.purefa_directory.get_array")
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_rename_first_run_renames(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_rename_dir,
        mock_create_dir,
        mock_check_renamed_dir,
    ):
        """First run: the source is there, so the rename happens"""
        from plugins.modules.purefa_directory import main

        mock_module = self._module(mock_ansible_module)
        mock_array = Mock()
        mock_get_array.return_value = mock_array
        mock_get_with_context.side_effect = self._responses(200)

        main()

        mock_rename_dir.assert_called_once_with(mock_module, mock_array)
        mock_create_dir.assert_not_called()
        mock_check_renamed_dir.assert_not_called()

    @patch("plugins.modules.purefa_directory.check_renamed_dir")
    @patch("plugins.modules.purefa_directory.create_dir")
    @patch("plugins.modules.purefa_directory.rename_dir")
    @patch("plugins.modules.purefa_directory.get_with_context")
    @patch("plugins.modules.purefa_directory.get_array")
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_rename_second_run_does_not_create(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_rename_dir,
        mock_create_dir,
        mock_check_renamed_dir,
    ):
        """Second run: the source has gone, and must not be created again"""
        from plugins.modules.purefa_directory import main

        mock_module = self._module(mock_ansible_module)
        mock_array = Mock()
        mock_get_array.return_value = mock_array
        mock_get_with_context.side_effect = self._responses(404)

        main()

        mock_check_renamed_dir.assert_called_once_with(mock_module, mock_array)
        mock_create_dir.assert_not_called()
        mock_rename_dir.assert_not_called()

    @patch("plugins.modules.purefa_directory.check_renamed_dir")
    @patch("plugins.modules.purefa_directory.create_dir")
    @patch("plugins.modules.purefa_directory.get_with_context")
    @patch("plugins.modules.purefa_directory.get_array")
    @patch("plugins.modules.purefa_directory.AnsibleModule")
    def test_main_creates_when_no_rename_requested(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_create_dir,
        mock_check_renamed_dir,
    ):
        """A missing directory with no rename asked for is still created"""
        from plugins.modules.purefa_directory import main

        mock_module = self._module(mock_ansible_module, rename=None)
        mock_array = Mock()
        mock_get_array.return_value = mock_array
        mock_get_with_context.side_effect = self._responses(404)

        main()

        mock_create_dir.assert_called_once_with(mock_module, mock_array)
        mock_check_renamed_dir.assert_not_called()
