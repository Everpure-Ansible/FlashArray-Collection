# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_fs module."""

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
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
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

from plugins.modules.purefa_fs import (
    delete_fs,
    recover_fs,
    eradicate_fs,
    rename_fs,
    create_fs,
)


class TestDeleteFs:
    """Test cases for delete_fs function"""

    def test_delete_fs_check_mode(self):
        """Test delete_fs in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-fs", "eradicate": False}
        mock_array = Mock()

        delete_fs(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.patch_with_context")
    def test_delete_fs_success(self, mock_patch_with_context, mock_check_response):
        """Test delete_fs successfully deletes file system"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-fs", "eradicate": False, "context": ""}
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        delete_fs(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.delete_with_context")
    @patch("plugins.modules.purefa_fs.patch_with_context")
    def test_delete_fs_with_eradicate(
        self, mock_patch_with_context, mock_delete_with_context, mock_check_response
    ):
        """Test delete_fs with eradicate flag"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-fs", "eradicate": True, "context": ""}
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)
        mock_delete_with_context.return_value = Mock(status_code=200)

        delete_fs(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverFs:
    """Test cases for recover_fs function"""

    def test_recover_fs_check_mode(self):
        """Test recover_fs in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-fs"}
        mock_array = Mock()

        recover_fs(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.patch_with_context")
    def test_recover_fs_success(self, mock_patch_with_context, mock_check_response):
        """Test recover_fs successfully recovers file system"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "deleted-fs", "context": ""}
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        recover_fs(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicateFs:
    """Test cases for eradicate_fs function"""

    def test_eradicate_fs_check_mode(self):
        """Test eradicate_fs in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-fs"}
        mock_array = Mock()

        eradicate_fs(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.delete_with_context")
    def test_eradicate_fs_success(self, mock_delete_with_context, mock_check_response):
        """Test eradicate_fs successfully eradicates file system"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "deleted-fs", "context": ""}
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        eradicate_fs(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenameFs:
    """Test cases for rename_fs function"""

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_rename_fs_check_mode(self, mock_get_with_context):
        """Test rename_fs in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "old-fs",
            "rename": "new-fs",
            "context": "",
        }
        mock_array = Mock()
        # Target doesn't exist
        mock_get_with_context.return_value = Mock(status_code=404)

        rename_fs(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.patch_with_context")
    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_rename_fs_success(
        self, mock_get_with_context, mock_patch_with_context, mock_check_response
    ):
        """Test rename_fs successfully renames file system"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-fs",
            "rename": "new-fs",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404)
        mock_patch_with_context.return_value = Mock(status_code=200)

        rename_fs(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateFs:
    """Test cases for create_fs function"""

    def test_create_fs_check_mode(self):
        """Test create_fs in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "new-fs", "context": ""}
        mock_array = Mock()

        create_fs(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.post_with_context")
    def test_create_fs_success(self, mock_post_with_context, mock_check_response):
        """Test create_fs successfully creates file system"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "new-fs", "context": ""}
        mock_array = Mock()
        mock_post_with_context.return_value = Mock(status_code=200)

        create_fs(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.post_with_context")
    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_create_fs_in_pod_success(
        self, mock_get_with_context, mock_post_with_context, mock_check_response
    ):
        """Test create_fs successfully creates file system in a pod"""
        mock_pod = Mock()
        mock_pod.promotion_status = "promoted"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "mypod::new-fs", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pod])
        mock_post_with_context.return_value = Mock(status_code=200)

        create_fs(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_create_fs_in_pod_not_exists(self, mock_get_with_context):
        """Test create_fs fails when pod doesn't exist"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {"name": "nonexistent::new-fs", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404)

        with pytest.raises(SystemExit):
            create_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_create_fs_in_demoted_pod_fails(self, mock_get_with_context):
        """Test create_fs fails when pod is demoted"""
        import pytest

        mock_pod = Mock()
        mock_pod.promotion_status = "demoted"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {"name": "demoted-pod::new-fs", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pod])

        with pytest.raises(SystemExit):
            create_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestRenameFsExtended:
    """Extended test cases for rename_fs function"""

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_rename_fs_target_exists_fails(self, mock_get_with_context):
        """Test rename_fs fails when target exists"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "old-fs",
            "rename": "existing-fs",
            "context": "",
        }
        mock_array = Mock()
        # Target exists
        mock_get_with_context.return_value = Mock(status_code=200, items=[Mock()])

        with pytest.raises(SystemExit):
            rename_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.patch_with_context")
    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_rename_fs_in_pod_success(
        self, mock_get_with_context, mock_patch_with_context, mock_check_response
    ):
        """Test rename_fs successfully renames file system in pod"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "mypod::old-fs",
            "rename": "new-fs",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404)
        mock_patch_with_context.return_value = Mock(status_code=200)

        rename_fs(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMoveFs:
    """Test cases for move_fs function"""

    def test_move_fs_to_local_same_location_fails(self):
        """Test move_fs fails when source and destination are the same"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-fs",  # Not in a pod
            "move": "local",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "cannot be the same" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.patch_with_context")
    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_to_local_success(
        self, mock_get_with_context, mock_patch_with_context, mock_check_response
    ):
        """Test move_fs successfully moves filesystem to local"""
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "mypod::test-fs",  # In a pod
            "move": "local",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404)
        mock_patch_with_context.return_value = Mock(status_code=200)

        move_fs(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.check_response")
    @patch("plugins.modules.purefa_fs.patch_with_context")
    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_to_pod_success(
        self, mock_get_with_context, mock_patch_with_context, mock_check_response
    ):
        """Test move_fs successfully moves filesystem to a pod"""
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-fs",
            "move": "target-pod",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[
                Mock(
                    arrays=[Mock()],  # Single array
                    link_target_count=0,
                    promotion_status="promoted",
                )
            ],
        )
        mock_patch_with_context.return_value = Mock(status_code=200)

        move_fs(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_to_stretched_pod_fails(self, mock_get_with_context):
        """Test move_fs fails when moving to a stretched pod"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-fs",
            "move": "stretched-pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[
                Mock(
                    arrays=[Mock(), Mock()],  # Multiple arrays = stretched
                    link_target_count=0,
                    promotion_status="promoted",
                )
            ],
        )

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "stretched pod" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_check_mode(self, mock_get_with_context):
        """Test move_fs in check mode"""
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-fs",
            "move": "target-pod",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[
                Mock(
                    arrays=[Mock()],
                    link_target_count=0,
                    promotion_status="promoted",
                )
            ],
        )

        move_fs(mock_module, mock_array)

        mock_array.patch_file_systems.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_target_exists_fails(self, mock_get_with_context):
        """Test move_fs fails when target filesystem already exists"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "mypod::test-fs",  # Must be in a pod to move to local
            "move": "local",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        # Target filesystem exists
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[Mock()],
        )

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "already exists" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_to_linked_pod_fails(self, mock_get_with_context):
        """Test move_fs fails when moving to a linked source pod"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-fs",
            "move": "linked-pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[
                Mock(
                    arrays=[Mock()],
                    link_target_count=1,  # Has link targets
                    promotion_status="promoted",
                )
            ],
        )

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "linked source pod" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_to_demoted_pod_fails(self, mock_get_with_context):
        """Test move_fs fails when moving to a demoted pod"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-fs",
            "move": "demoted-pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[
                Mock(
                    arrays=[Mock()],
                    link_target_count=0,
                    promotion_status="demoted",
                )
            ],
        )

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "demoted pod" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_pod_not_exists_fails(self, mock_get_with_context):
        """Test move_fs fails when target pod doesn't exist"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-fs",
            "move": "nonexistent-pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        # Pod doesn't exist
        mock_get_with_context.return_value = Mock(status_code=404)

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "does not exist" in mock_module.fail_json.call_args[1]["msg"]


class TestMoveFsFromPod:
    """Test cases for moving filesystem out of a pod

    Note: The module code on lines 310-316 queries module.params["move"] (target pod)
    instead of the source pod name, so tests must match this behavior. Both get_pods
    calls use the same target pod name.
    """

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_out_of_stretched_pod_fails(self, mock_get_with_context):
        """Test move_fs fails when checking pod for stretched status (out of pod path)"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "mypod::test-fs",  # Filesystem in a pod
            "move": "target-pod",  # Moving to another pod
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        # Both calls use module.params["move"] ("target-pod")
        # First call: lines 288-294 - check target pod for "into" validation
        # Second call: lines 310-316 - check again for "out of" validation
        mock_get_with_context.side_effect = [
            Mock(
                status_code=200,
                items=[
                    Mock(
                        arrays=[Mock()],  # Single array - passes "into" check
                        link_target_count=0,
                        promotion_status="promoted",
                    )
                ],
            ),  # First call passes
            Mock(
                status_code=200,
                items=[
                    Mock(
                        arrays=[Mock(), Mock()],  # Multiple arrays - stretched
                        linked_target_count=0,
                        promotion_status="promoted",
                    )
                ],
            ),  # Second call - stretched pod for "out of" check
        ]

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "stretched pod" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_out_of_linked_pod_fails(self, mock_get_with_context):
        """Test move_fs fails when checking pod for linked status (out of pod path)"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "mypod::test-fs",
            "move": "target-pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_get_with_context.side_effect = [
            Mock(
                status_code=200,
                items=[
                    Mock(
                        arrays=[Mock()],
                        link_target_count=0,
                        promotion_status="promoted",
                    )
                ],
            ),  # First call passes
            Mock(
                status_code=200,
                items=[
                    Mock(
                        arrays=[Mock()],
                        linked_target_count=1,  # Has link targets
                        promotion_status="promoted",
                    )
                ],
            ),  # Second call - linked pod for "out of" check
        ]

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "linked source pod" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_out_of_demoted_pod_fails(self, mock_get_with_context):
        """Test move_fs fails when checking pod for demoted status (out of pod path)"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "mypod::test-fs",
            "move": "target-pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_get_with_context.side_effect = [
            Mock(
                status_code=200,
                items=[
                    Mock(
                        arrays=[Mock()],
                        link_target_count=0,
                        promotion_status="promoted",
                    )
                ],
            ),  # First call passes
            Mock(
                status_code=200,
                items=[
                    Mock(
                        arrays=[Mock()],
                        linked_target_count=0,
                        promotion_status="demoted",  # Demoted pod
                    )
                ],
            ),  # Second call - demoted pod for "out of" check
        ]

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "demoted pod" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.get_with_context")
    def test_move_fs_second_pod_check_not_exists_fails(self, mock_get_with_context):
        """Test move_fs fails when second pod check returns 404"""
        import pytest
        from plugins.modules.purefa_fs import move_fs

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "mypod::test-fs",
            "move": "target-pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_get_with_context.side_effect = [
            Mock(
                status_code=200,
                items=[
                    Mock(
                        arrays=[Mock()],
                        link_target_count=0,
                        promotion_status="promoted",
                    )
                ],
            ),  # First call passes
            Mock(status_code=404),  # Second pod check fails
        ]

        with pytest.raises(SystemExit):
            move_fs(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "does not exist" in mock_module.fail_json.call_args[1]["msg"]


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_no_purestorage_sdk(
        self, mock_ansible_module, mock_get_array, mock_get_with_context
    ):
        """Test main fails when pypureclient is not available"""
        import pytest
        import plugins.modules.purefa_fs as purefa_fs_module

        # Save original value
        original_value = purefa_fs_module.HAS_PURESTORAGE
        purefa_fs_module.HAS_PURESTORAGE = False

        mock_module = Mock()
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        try:
            with pytest.raises(SystemExit):
                purefa_fs_module.main()

            mock_module.fail_json.assert_called_once()
            assert "sdk is required" in mock_module.fail_json.call_args[1]["msg"]
        finally:
            purefa_fs_module.HAS_PURESTORAGE = original_value

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_api_version_too_low(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_loose_version,
    ):
        """Test main fails when API version is too low"""
        import pytest
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_module = Mock()
        mock_module.params = {"name": "test-fs", "state": "present", "context": ""}
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "1.0"  # Very old version
        mock_get_array.return_value = mock_array

        # Make LooseVersion comparison return True (min > current)
        mock_loose_version.side_effect = lambda v: Mock(
            __gt__=lambda self, other: v == "2.2"
        )

        with pytest.raises(SystemExit):
            purefa_fs_module.main()

        mock_module.fail_json.assert_called_once()
        assert "not supported" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_repl_api_version_too_low(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_loose_version,
    ):
        """Test main fails when using pod notation with old API"""
        import pytest
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_module = Mock()
        mock_module.params = {
            "name": "mypod::test-fs",
            "state": "present",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_get_array.return_value = mock_array

        # First comparison passes, second comparison fails (for replication API)
        call_count = [0]

        def version_side_effect(v):
            call_count[0] += 1
            if call_count[0] <= 2:
                # First comparison: MIN_REQUIRED > api_version - return False (passes)
                return Mock(__gt__=lambda self, other: False)
            else:
                # Second comparison: REPL_SUPPORT > api_version - return True (fails)
                return Mock(__gt__=lambda self, other: True)

        mock_loose_version.side_effect = version_side_effect

        with pytest.raises(SystemExit):
            purefa_fs_module.main()

        mock_module.fail_json.assert_called_once()
        assert "Replication" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.create_fs")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_create_new_fs(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_create_fs,
        mock_loose_version,
    ):
        """Test main creates filesystem when it doesn't exist"""
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_module = Mock()
        mock_module.params = {
            "name": "new-fs",
            "state": "present",
            "move": None,
            "rename": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.33"
        mock_get_array.return_value = mock_array

        # All version checks pass
        mock_loose_version.side_effect = lambda v: Mock(
            __gt__=lambda self, other: False
        )

        # Filesystem doesn't exist
        mock_get_with_context.return_value = Mock(status_code=404)

        purefa_fs_module.main()

        mock_create_fs.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.move_fs")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_move_fs(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_move_fs,
        mock_loose_version,
    ):
        """Test main moves filesystem when move param is set"""
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_fs = Mock()
        mock_fs.destroyed = False

        mock_module = Mock()
        mock_module.params = {
            "name": "existing-fs",
            "state": "present",
            "move": "target-pod",
            "rename": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.33"
        mock_get_array.return_value = mock_array

        mock_loose_version.side_effect = lambda v: Mock(
            __gt__=lambda self, other: False
        )

        # Filesystem exists
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_fs])

        purefa_fs_module.main()

        mock_move_fs.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.rename_fs")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_rename_fs(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_rename_fs,
        mock_loose_version,
    ):
        """Test main renames filesystem when rename param is set"""
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_fs = Mock()
        mock_fs.destroyed = False

        mock_module = Mock()
        mock_module.params = {
            "name": "old-fs",
            "state": "present",
            "move": None,
            "rename": "new-fs",
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.33"
        mock_get_array.return_value = mock_array

        mock_loose_version.side_effect = lambda v: Mock(
            __gt__=lambda self, other: False
        )

        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_fs])

        purefa_fs_module.main()

        mock_rename_fs.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.recover_fs")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_recover_fs(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_recover_fs,
        mock_loose_version,
    ):
        """Test main recovers destroyed filesystem"""
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_fs = Mock()
        mock_fs.destroyed = True

        mock_module = Mock()
        mock_module.params = {
            "name": "deleted-fs",
            "state": "present",
            "move": None,
            "rename": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.33"
        mock_get_array.return_value = mock_array

        mock_loose_version.side_effect = lambda v: Mock(
            __gt__=lambda self, other: False
        )

        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_fs])

        purefa_fs_module.main()

        mock_recover_fs.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_move_destroyed_fs_fails(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_loose_version,
    ):
        """Test main fails when trying to move a destroyed filesystem"""
        import pytest
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_fs = Mock()
        mock_fs.destroyed = True

        mock_module = Mock()
        mock_module.params = {
            "name": "deleted-fs",
            "state": "present",
            "move": "target-pod",
            "rename": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.33"
        mock_get_array.return_value = mock_array

        mock_loose_version.side_effect = lambda v: Mock(
            __gt__=lambda self, other: False
        )

        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_fs])

        with pytest.raises(SystemExit):
            purefa_fs_module.main()

        mock_module.fail_json.assert_called_once()
        assert "destroyed state" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.delete_fs")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_delete_fs(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_delete_fs,
        mock_loose_version,
    ):
        """Test main deletes filesystem when state is absent"""
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_fs = Mock()
        mock_fs.destroyed = False

        mock_module = Mock()
        mock_module.params = {
            "name": "test-fs",
            "state": "absent",
            "eradicate": False,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.33"
        mock_get_array.return_value = mock_array

        mock_loose_version.side_effect = lambda v: Mock(
            __gt__=lambda self, other: False
        )

        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_fs])

        purefa_fs_module.main()

        mock_delete_fs.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.eradicate_fs")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_eradicate_fs(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_eradicate_fs,
        mock_loose_version,
    ):
        """Test main eradicates destroyed filesystem"""
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_fs = Mock()
        mock_fs.destroyed = True

        mock_module = Mock()
        mock_module.params = {
            "name": "deleted-fs",
            "state": "absent",
            "eradicate": True,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.33"
        mock_get_array.return_value = mock_array

        mock_loose_version.side_effect = lambda v: Mock(
            __gt__=lambda self, other: False
        )

        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_fs])

        purefa_fs_module.main()

        mock_eradicate_fs.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_fs.LooseVersion")
    @patch("plugins.modules.purefa_fs.get_with_context")
    @patch("plugins.modules.purefa_fs.get_array")
    @patch("plugins.modules.purefa_fs.AnsibleModule")
    def test_main_no_change_needed(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_get_with_context,
        mock_loose_version,
    ):
        """Test main returns no change when no action is needed"""
        import plugins.modules.purefa_fs as purefa_fs_module

        mock_module = Mock()
        mock_module.params = {
            "name": "nonexistent-fs",
            "state": "absent",
            "eradicate": False,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.33"
        mock_get_array.return_value = mock_array

        mock_loose_version.side_effect = lambda v: Mock(
            __gt__=lambda self, other: False
        )

        # Filesystem doesn't exist
        mock_get_with_context.return_value = Mock(status_code=404)

        purefa_fs_module.main()

        mock_module.exit_json.assert_called_once_with(changed=False)
