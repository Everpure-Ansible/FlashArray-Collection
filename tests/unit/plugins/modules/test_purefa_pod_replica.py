# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_pod_replica module."""

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
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    MagicMock()
)

from plugins.modules.purefa_pod_replica import (
    get_local_pod,
    get_local_rl,
    delete_rl,
    update_rl,
    create_rl,
)


class TestGetLocalPod:
    """Test cases for get_local_pod function"""

    @patch("plugins.modules.purefa_pod_replica.get_with_context")
    def test_get_local_pod_exists(self, mock_get):
        """Test get_local_pod returns pod when it exists"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_pod = Mock()
        mock_pod.name = "test-pod"
        mock_get.return_value = Mock(status_code=200, items=[mock_pod])

        result = get_local_pod(mock_module, mock_array)

        assert result == mock_pod
        mock_get.assert_called_once()

    @patch("plugins.modules.purefa_pod_replica.get_with_context")
    def test_get_local_pod_not_exists(self, mock_get):
        """Test get_local_pod returns None when pod doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=404, items=[])

        result = get_local_pod(mock_module, mock_array)

        assert result is None


class TestGetLocalRl:
    """Test cases for get_local_rl function"""

    @patch("plugins.modules.purefa_pod_replica.get_with_context")
    def test_get_local_rl_not_exists(self, mock_get):
        """Test get_local_rl returns None when replica link doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_get.return_value = Mock(total_item_count=0, items=[])

        result = get_local_rl(mock_module, mock_array)

        assert result is None


class TestDeleteRl:
    """Test cases for delete_rl function"""

    @patch("plugins.modules.purefa_pod_replica.delete_with_context")
    def test_delete_rl_check_mode(self, mock_delete):
        """Test delete_rl in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_rl = Mock()

        delete_rl(mock_module, mock_array, mock_rl)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_delete.assert_not_called()


class TestUpdateRl:
    """Test cases for update_rl function"""

    @patch("plugins.modules.purefa_pod_replica.patch_with_context")
    def test_update_rl_no_pause_param(self, mock_patch):
        """Test update_rl when pause is None - no change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-pod", "pause": None, "context": ""}
        mock_array = Mock()
        mock_rl = Mock()
        mock_rl.status = "replicating"

        update_rl(mock_module, mock_array, mock_rl)

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_patch.assert_not_called()

    @patch("plugins.modules.purefa_pod_replica.check_response")
    @patch("plugins.modules.purefa_pod_replica.PodReplicaLinkPatch")
    @patch("plugins.modules.purefa_pod_replica.patch_with_context")
    def test_update_rl_pause_success(self, mock_patch, mock_rl_patch, mock_check):
        """Test update_rl pausing a replica link"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-pod", "pause": True, "context": ""}
        mock_array = Mock()
        mock_patch.return_value = Mock(status_code=200)
        mock_rl = Mock()
        mock_rl.status = "replicating"
        mock_rl.__getitem__ = Mock(return_value={"name": "remote-pod"})

        update_rl(mock_module, mock_array, mock_rl)

        mock_patch.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateRl:
    """Test cases for create_rl function"""

    @patch("plugins.modules.purefa_pod_replica.get_with_context")
    def test_create_rl_missing_target_pod(self, mock_get):
        """Test create_rl fails without target_pod"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "target_pod": None,
            "target_array": "array2",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()

        with pytest.raises(SystemExit):
            create_rl(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_pod_replica.get_with_context")
    def test_create_rl_missing_target_array(self, mock_get):
        """Test create_rl fails without target_array"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "target_pod": "remote-pod",
            "target_array": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()

        with pytest.raises(SystemExit):
            create_rl(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_pod_replica.get_with_context")
    def test_create_rl_no_connected_arrays(self, mock_get):
        """Test create_rl fails when no arrays are connected"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "target_pod": "remote-pod",
            "target_array": "array2",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_array_connections.return_value = Mock(total_item_count=0)

        with pytest.raises(SystemExit):
            create_rl(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_pod_replica.check_response")
    @patch("plugins.modules.purefa_pod_replica.post_with_context")
    @patch("plugins.modules.purefa_pod_replica.get_with_context")
    def test_create_rl_success(self, mock_get, mock_post, mock_check):
        """Test create_rl successfully creates replica link"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "target_pod": "remote-pod",
            "target_array": "array2",
            "context": "",
        }
        mock_array = Mock()
        # Direct call for total_item_count check
        mock_array.get_array_connections.return_value = Mock(total_item_count=1)
        # get_with_context returns the actual connection
        mock_get.return_value = Mock(status_code=200, items=[Mock(status="connected")])
        mock_post.return_value = Mock(status_code=200)

        create_rl(mock_module, mock_array)

        mock_post.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod_replica.post_with_context")
    @patch("plugins.modules.purefa_pod_replica.get_with_context")
    def test_create_rl_check_mode(self, mock_get, mock_post):
        """Test create_rl in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pod",
            "target_pod": "remote-pod",
            "target_array": "array2",
            "context": "",
        }
        mock_array = Mock()
        # Direct call for total_item_count check
        mock_array.get_array_connections.return_value = Mock(total_item_count=1)
        # get_with_context returns the actual connection
        mock_get.return_value = Mock(status_code=200, items=[Mock(status="connected")])

        create_rl(mock_module, mock_array)

        mock_post.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod_replica.get_with_context")
    def test_create_rl_bad_status(self, mock_get):
        """Test create_rl fails with bad connection status"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "target_pod": "remote-pod",
            "target_array": "array2",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        # Direct call for total_item_count check
        mock_array.get_array_connections.return_value = Mock(total_item_count=1)
        # get_with_context returns connection with bad status
        mock_get.return_value = Mock(
            status_code=200, items=[Mock(status="disconnected")]
        )

        with pytest.raises(SystemExit):
            create_rl(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "Bad status" in mock_module.fail_json.call_args[1]["msg"]


class TestDeleteRlSuccess:
    """Test cases for delete_rl success paths"""

    @patch("plugins.modules.purefa_pod_replica.check_response")
    @patch("plugins.modules.purefa_pod_replica.delete_with_context")
    def test_delete_rl_success(self, mock_delete, mock_check):
        """Test delete_rl successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_delete.return_value = Mock(status_code=200)
        mock_rl = Mock()
        mock_rl.__getitem__ = Mock(return_value={"name": "remote-pod"})

        delete_rl(mock_module, mock_array, mock_rl)

        mock_delete.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateRlSuccess:
    """Test cases for update_rl success paths"""

    @patch("plugins.modules.purefa_pod_replica.check_response")
    @patch("plugins.modules.purefa_pod_replica.PodReplicaLinkPatch")
    @patch("plugins.modules.purefa_pod_replica.patch_with_context")
    def test_update_rl_resume_success(self, mock_patch, mock_rl_patch, mock_check):
        """Test update_rl resuming a paused replica link"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-pod", "pause": False, "context": ""}
        mock_array = Mock()
        mock_patch.return_value = Mock(status_code=200)
        mock_rl = Mock()
        mock_rl.status = "paused"
        mock_rl.__getitem__ = Mock(return_value={"name": "remote-pod"})

        update_rl(mock_module, mock_array, mock_rl)

        mock_patch.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod_replica.patch_with_context")
    def test_update_rl_already_paused(self, mock_patch):
        """Test update_rl when already paused - no change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-pod", "pause": True, "context": ""}
        mock_array = Mock()
        mock_rl = Mock()
        mock_rl.status = "paused"

        update_rl(mock_module, mock_array, mock_rl)

        mock_patch.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_pod_replica.patch_with_context")
    def test_update_rl_already_running(self, mock_patch):
        """Test update_rl when already running - no change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-pod", "pause": False, "context": ""}
        mock_array = Mock()
        mock_rl = Mock()
        mock_rl.status = "replicating"

        update_rl(mock_module, mock_array, mock_rl)

        mock_patch.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)
