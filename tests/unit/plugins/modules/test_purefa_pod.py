# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_pod module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, patch, MagicMock
from packaging.version import Version as LooseVersion

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

from plugins.modules.purefa_pod import (
    get_pod,
    get_undo_pod,
    get_target,
    get_destroyed_pod,
    get_destroyed_target,
    check_arrays,
    create_pod,
    clone_pod,
    update_pod,
    stretch_pod,
    delete_pod,
    eradicate_pod,
    recover_pod,
)


class TestGetPod:
    """Test cases for get_pod function"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_pod_exists(self, mock_get_with_context):
        """Test get_pod returns True when pod exists"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        result = get_pod(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_pod_not_exists(self, mock_get_with_context):
        """Test get_pod returns False when pod doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent-pod", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404)

        result = get_pod(mock_module, mock_array)

        assert result is False


class TestGetUndoPod:
    """Test cases for get_undo_pod function"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_undo_pod_exists(self, mock_get_with_context):
        """Test get_undo_pod returns list when undo pods exist"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_undo_pod = Mock()
        mock_undo_pod.name = "test-pod.undo-demote.1"
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[mock_undo_pod]
        )

        result = get_undo_pod(mock_module, mock_array)

        assert result == [mock_undo_pod]

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_undo_pod_not_exists(self, mock_get_with_context):
        """Test get_undo_pod returns None when no undo pods exist"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404)

        result = get_undo_pod(mock_module, mock_array)

        assert result is None


class TestGetTarget:
    """Test cases for get_target function"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_target_exists(self, mock_get_with_context):
        """Test get_target returns True when target exists"""
        mock_module = Mock()
        mock_module.params = {"target": "target-pod", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        result = get_target(mock_module, mock_array)

        assert result is True


class TestGetDestroyedPod:
    """Test cases for get_destroyed_pod function"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_destroyed_pod_exists(self, mock_get_with_context):
        """Test get_destroyed_pod returns True when destroyed pod exists"""
        mock_module = Mock()
        mock_module.params = {"name": "deleted-pod", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        result = get_destroyed_pod(mock_module, mock_array)

        assert result is True


class TestGetDestroyedTarget:
    """Test cases for get_destroyed_target function"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_destroyed_target_exists(self, mock_get_with_context):
        """Test get_destroyed_target returns True when destroyed target exists"""
        mock_module = Mock()
        mock_module.params = {"target": "deleted-target", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        result = get_destroyed_target(mock_module, mock_array)

        assert result is True


class TestCreatePod:
    """Test cases for create_pod function"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.LooseVersion")
    def test_create_pod_check_mode(self, mock_loose_version, mock_check_response):
        """Test create_pod in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "new-pod", "target": None}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        create_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeletePod:
    """Test cases for delete_pod function"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.LooseVersion")
    def test_delete_pod_check_mode(self, mock_loose_version, mock_check_response):
        """Test delete_pod in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-pod", "eradicate": False}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        delete_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePod:
    """Test cases for eradicate_pod function"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.LooseVersion")
    def test_eradicate_pod_check_mode(self, mock_loose_version, mock_check_response):
        """Test eradicate_pod in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-pod", "eradicate": True}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        eradicate_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverPod:
    """Test cases for recover_pod function"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.LooseVersion")
    def test_recover_pod_check_mode(self, mock_loose_version, mock_check_response):
        """Test recover_pod in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-pod"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        recover_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCheckArrays:
    """Test cases for check_arrays function"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_check_arrays_no_stretch_no_failover(self, mock_get_with_context):
        """Test check_arrays returns None when no stretch/failover specified"""
        mock_module = Mock()
        mock_module.params = {"stretch": None, "failover": None, "context": None}
        mock_array = Mock()
        # Mock get_with_context for both get_arrays and get_array_connections
        mock_local = Mock()
        mock_local.name = "local-array"
        # First call: get_arrays, Second call: get_array_connections
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_local]),  # get_arrays
            Mock(status_code=200, items=[]),  # get_array_connections
        ]

        result = check_arrays(mock_module, mock_array)

        assert result is None

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_check_arrays_failover_auto(self, mock_get_with_context):
        """Test check_arrays with failover set to auto"""
        mock_module = Mock()
        mock_module.params = {"stretch": None, "failover": ["auto"], "context": None}
        mock_array = Mock()
        mock_local = Mock()
        mock_local.name = "local-array"
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_local]),
            Mock(status_code=200, items=[]),
        ]

        result = check_arrays(mock_module, mock_array)

        assert result is None

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_check_arrays_failover_valid_array(self, mock_get_with_context):
        """Test check_arrays with valid failover array"""
        mock_module = Mock()
        mock_module.params = {
            "stretch": None,
            "failover": ["remote-array"],
            "context": None,
        }
        mock_array = Mock()
        mock_local = Mock()
        mock_local.name = "local-array"
        mock_remote = Mock()
        mock_remote.name = "remote-array"
        mock_remote.type = "sync-replication"
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_local]),
            Mock(status_code=200, items=[mock_remote]),
        ]

        result = check_arrays(mock_module, mock_array)

        assert result is None

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_check_arrays_failover_invalid_array(self, mock_get_with_context):
        """Test check_arrays fails with invalid failover array"""
        mock_module = Mock()
        mock_module.params = {
            "stretch": None,
            "failover": ["invalid-array"],
            "context": None,
        }
        mock_array = Mock()
        mock_local = Mock()
        mock_local.name = "local-array"
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_local]),
            Mock(status_code=200, items=[]),  # No sync-replication arrays
        ]

        check_arrays(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "invalid-array" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_check_arrays_stretch_valid_array(self, mock_get_with_context):
        """Test check_arrays with valid stretch array"""
        mock_module = Mock()
        mock_module.params = {
            "stretch": "remote-array",
            "failover": None,
            "context": None,
        }
        mock_array = Mock()
        mock_local = Mock()
        mock_local.name = "local-array"
        mock_remote = Mock()
        mock_remote.name = "remote-array"
        mock_remote.type = "sync-replication"
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_local]),
            Mock(status_code=200, items=[mock_remote]),
        ]

        result = check_arrays(mock_module, mock_array)

        assert result is None

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_check_arrays_stretch_invalid_array(self, mock_get_with_context):
        """Test check_arrays fails with invalid stretch array"""
        mock_module = Mock()
        mock_module.params = {
            "stretch": "invalid-array",
            "failover": None,
            "context": None,
        }
        mock_array = Mock()
        mock_local = Mock()
        mock_local.name = "local-array"
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_local]),
            Mock(status_code=200, items=[]),  # No sync-replication arrays
        ]

        check_arrays(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "invalid-array" in str(mock_module.fail_json.call_args)


class TestClonePod:
    """Test cases for clone_pod function"""

    @patch("plugins.modules.purefa_pod.get_destroyed_target")
    @patch("plugins.modules.purefa_pod.get_target")
    def test_clone_pod_target_already_exists(
        self, mock_get_target, mock_get_destroyed_target
    ):
        """Test clone_pod when target already exists"""
        mock_get_target.return_value = True  # Target already exists
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "source-pod", "target": "existing-pod"}
        mock_array = Mock()

        clone_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_pod.get_destroyed_target")
    @patch("plugins.modules.purefa_pod.get_target")
    def test_clone_pod_destroyed_target_exists(
        self, mock_get_target, mock_get_destroyed_target
    ):
        """Test clone_pod when target exists but is destroyed"""
        mock_get_target.return_value = False  # Target doesn't exist as active
        mock_get_destroyed_target.return_value = True  # But exists as destroyed
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "source-pod", "target": "deleted-target"}
        mock_array = Mock()

        clone_pod(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "already exists but deleted" in str(mock_module.fail_json.call_args)


class TestUpdatePod:
    """Test cases for update_pod function"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_update_pod_no_changes(self, mock_get_with_context):
        """Test update_pod when no changes are needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purearray1",
            "stretch": None,
            "quota": None,
            "ignore_usage": False,
            "promote": None,
            "undo": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        # Mock current config
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purearray1"
        mock_config.quota_limit = None
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        update_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_update_pod_check_mode_failover_change(self, mock_get_with_context):
        """Test update_pod in check mode when failover preference changes"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": ["array2"],
            "mediator": "purearray1",
            "stretch": None,
            "quota": None,
            "ignore_usage": False,
            "promote": None,
            "undo": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        # Mock current config with different failover
        mock_config = Mock()
        mock_config.failover_preferences = ["array1"]
        mock_config.mediator = "purearray1"
        mock_config.quota_limit = None
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        update_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.post_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_update_pod_check_mode_default_protection(
        self, mock_get, mock_post, mock_patch, mock_lv
    ):
        """update_pod must not write default protection in check mode.

        The default_protection_pg path previously created a protection group
        and patched container default protections even under --check.
        """
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "stretch": None,
            "quota": None,
            "ignore_usage": False,
            "promote": None,
            "undo": None,
            "default_protection_pg": "myprotect",
            "with_default_protection": True,
            "retention_lock": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.39"

        current_config = Mock()
        current_config.failover_preferences = []
        current_config.mediator = "purestorage"
        current_config.quota_limit = None
        # 1st get: get_pods -> current_config; 2nd get: container default
        # protections with none set, so pgname differs from the desired PG
        mock_get.side_effect = [
            Mock(status_code=200, items=[current_config]),
            Mock(status_code=200, items=[Mock(default_protections=[])]),
        ]

        update_pod(mock_module, mock_array)

        # No writes may happen in check mode
        mock_post.assert_not_called()
        mock_patch.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestStretchPod:
    """Test cases for stretch_pod function"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_stretch_pod_check_mode(self, mock_get_with_context):
        """Test stretch_pod in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "stretch": "remote-array",
            "quota": None,
            "state": "present",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        # Mock current config
        mock_config = Mock()
        mock_config.arrays = [{"name": "local-array"}]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        stretch_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_stretch_pod_no_change_already_stretched(self, mock_get_with_context):
        """Test stretch_pod when pod is already stretched to target"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "stretch": "remote-array",
            "quota": None,
            "state": "present",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        # Mock current config - already stretched to remote-array
        mock_config = Mock()
        mock_config.arrays = [{"name": "local-array"}, {"name": "remote-array"}]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        stretch_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestCreatePodSuccess:
    """Additional test cases for create_pod function"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.LooseVersion")
    def test_create_pod_fail_with_target(self, mock_loose_version, mock_check_response):
        """Test create_pod fails when target is specified"""
        import pytest

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "test-pod",
            "context": "realm1",
            "target": "source-pod",
            "failover": None,
            "mediator": "purestorage",
            "stretch": None,
            "throttle": True,
            "quota": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        with pytest.raises(SystemExit):
            create_pod(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestDeletePodSuccess:
    """Additional test cases for delete_pod function"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.LooseVersion")
    def test_delete_pod_success(self, mock_loose_version, mock_check_response):
        """Test delete_pod successfully deletes a pod"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "eradicate": False,
            "delete_contents": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_pods.return_value = Mock(status_code=200)

        delete_pod(mock_module, mock_array)

        mock_array.patch_pods.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverPodSuccess:
    """Additional test cases for recover_pod function"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.LooseVersion")
    def test_recover_pod_success(self, mock_loose_version, mock_check_response):
        """Test recover_pod successfully recovers a pod"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_pods.return_value = Mock(status_code=200)

        recover_pod(mock_module, mock_array)

        mock_array.patch_pods.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePodSuccess:
    """Additional test cases for eradicate_pod function"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.LooseVersion")
    def test_eradicate_pod_success(self, mock_loose_version, mock_check_response):
        """Test eradicate_pod successfully eradicates a pod"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "eradicate": True,
            "delete_contents": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_pods.return_value = Mock(status_code=200)

        eradicate_pod(mock_module, mock_array)

        mock_array.delete_pods.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePodSuccess:
    """Test cases for create_pod function success scenarios"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.post_with_throttle_and_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_create_pod_basic(self, mock_lv, mock_post, mock_check_response):
        """Test creating a basic pod without options"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "target": None,
            "failover": None,
            "stretch": None,
            "mediator": "purestorage",
            "throttle": True,
            "context": None,
            "quota": None,
            "quota_notification": None,
            "namespace": None,
            "state": "present",
        }
        mock_array = Mock()
        # Use old version to avoid DEFAULT_API_VERSION (2.24) path
        mock_array.get_rest_version.return_value = "2.0"
        mock_post.return_value = Mock(status_code=200)

        create_pod(mock_module, mock_array)

        mock_post.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.post_with_throttle_and_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_create_pod_with_failover(self, mock_lv, mock_post, mock_check_response):
        """Test creating a pod with failover preferences"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "target": None,
            "failover": ["array2"],
            "stretch": None,
            "mediator": "purestorage",
            "throttle": True,
            "context": None,
            "quota": None,
            "quota_notification": None,
            "namespace": None,
            "state": "present",
        }
        mock_array = Mock()
        # Use old version to avoid DEFAULT_API_VERSION (2.24) path
        mock_array.get_rest_version.return_value = "2.0"
        mock_post.return_value = Mock(status_code=200)

        create_pod(mock_module, mock_array)

        mock_post.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestClonePodSuccess:
    """Test cases for clone_pod function success scenarios"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.post_with_throttle_and_context")
    def test_clone_pod_basic(self, mock_post, mock_check_response):
        """Test cloning a pod"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "target": "new-pod",
            "context": None,
            "throttle": True,
        }
        mock_array = Mock()
        mock_array.get_pods.return_value = Mock(status_code=400)  # Target doesn't exist
        mock_post.return_value = Mock(status_code=200)

        clone_pod(mock_module, mock_array)

        mock_post.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestStretchPodSuccess:
    """Test cases for stretch_pod function success scenarios"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.post_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_stretch_pod_success(
        self,
        mock_lv,
        mock_get_with_context,
        mock_post_with_context,
        mock_check_response,
    ):
        """Test successfully stretching a pod to another array"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "stretch": "remote-array",
            "state": "present",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current config - not yet stretched to remote
        mock_config = Mock()
        mock_config.arrays = [{"name": "local-array"}]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_post_with_context.return_value = Mock(status_code=200)

        stretch_pod(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.delete_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_unstretch_pod_success(
        self,
        mock_lv,
        mock_get_with_context,
        mock_delete_with_context,
        mock_check_response,
    ):
        """Test successfully unstretching a pod from an array"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "stretch": "remote-array",
            "state": "absent",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current config - stretched to remote-array
        mock_config = Mock()
        mock_config.arrays = [{"name": "local-array"}, {"name": "remote-array"}]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_delete_with_context.return_value = Mock(status_code=200)

        stretch_pod(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_unstretch_pod_no_change(self, mock_get_with_context):
        """Test unstretch when pod is not stretched to target"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "stretch": "nonexistent-array",
            "state": "absent",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock current config - only local array
        mock_config = Mock()
        mock_config.arrays = [{"name": "local-array"}]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        stretch_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_stretch_pod_old_api(
        self,
        mock_lv,
        mock_get_with_context,
        mock_check_response,
    ):
        """Test stretching a pod with old API version (pre-2.36)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "stretch": "remote-array",
            "state": "present",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Pre-MEMBERS_VERSION
        mock_array.post_pods_arrays.return_value = Mock(status_code=200)

        # Mock current config - not yet stretched to remote
        mock_config = Mock()
        mock_config.arrays = [{"name": "local-array"}]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        stretch_pod(mock_module, mock_array)

        mock_array.post_pods_arrays.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_unstretch_pod_old_api(
        self,
        mock_lv,
        mock_get_with_context,
        mock_check_response,
    ):
        """Test unstretching a pod with old API version (pre-2.36)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "stretch": "remote-array",
            "state": "absent",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Pre-MEMBERS_VERSION
        mock_array.delete_pods_arrays.return_value = Mock(status_code=200)

        # Mock current config - stretched to remote-array
        mock_config = Mock()
        mock_config.arrays = [{"name": "local-array"}, {"name": "remote-array"}]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        stretch_pod(mock_module, mock_array)

        mock_array.delete_pods_arrays.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePodSuccess:
    """Test cases for update_pod function success scenarios"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_update_pod_change_failover(
        self,
        mock_lv,
        mock_get_with_context,
        mock_patch_with_context,
        mock_check_response,
    ):
        """Test update_pod changing failover preferences"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": ["array1", "array2"],
            "mediator": "mediator.example.com",
            "promote": None,
            "quiesce": None,
            "undo": None,
            "priority_adjustment": None,
            "rename": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current config with different failover
        mock_config = Mock()
        mock_config.failover_preferences = ["old-array"]
        mock_config.mediator = "mediator.example.com"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_update_pod_clear_failover_auto(
        self,
        mock_lv,
        mock_get_with_context,
        mock_patch_with_context,
        mock_check_response,
    ):
        """Test update_pod clearing failover with auto"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": ["auto"],
            "mediator": "mediator.example.com",
            "promote": None,
            "quiesce": None,
            "undo": None,
            "priority_adjustment": None,
            "rename": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current config with failover set
        mock_config = Mock()
        mock_config.failover_preferences = ["array1"]
        mock_config.mediator = "mediator.example.com"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_update_pod_no_changes(self, mock_get_with_context):
        """Test update_pod when no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "mediator.example.com",
            "promote": None,
            "quiesce": None,
            "undo": None,
            "priority_adjustment": None,
            "rename": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current config matching params
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "mediator.example.com"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        update_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestClonePodEdgeCases:
    """Test cases for clone_pod edge cases"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.post_with_throttle_and_context")
    def test_clone_pod_success(self, mock_post, mock_check_response):
        """Test clone_pod successfully clones"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "new-pod",
            "context": "",
            "target": "source-pod",
            "throttle": True,
            "quota": None,
        }
        mock_array = Mock()
        mock_array.get_pods.return_value = Mock(status_code=400)  # Target doesn't exist
        mock_post.return_value = Mock(status_code=200)

        clone_pod(mock_module, mock_array)

        mock_post.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.get_target")
    def test_clone_pod_target_already_exists(self, mock_get_target):
        """Test clone_pod when target already exists"""
        mock_get_target.return_value = True  # Target pod exists
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-pod",
            "context": "",
            "target": "existing-pod",
            "throttle": True,
            "quota": None,
        }
        mock_array = Mock()

        clone_pod(mock_module, mock_array)

        mock_array.post_pods.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestRecoverPodSuccess:
    """Test cases for recover_pod success paths"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    def test_recover_pod_success(self, mock_patch_with_context, mock_check_response):
        """Test recover_pod successfully recovers"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        recover_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_recover_pod_check_mode(self):
        """Test recover_pod in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()

        recover_pod(mock_module, mock_array)

        mock_array.patch_pods.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePodSuccess:
    """Test cases for eradicate_pod success paths"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.delete_with_context")
    def test_eradicate_pod_success(self, mock_delete_with_context, mock_check_response):
        """Test eradicate_pod successfully eradicates"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "eradicate": True,
            "delete_contents": False,
        }
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        eradicate_pod(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_eradicate_pod_check_mode(self):
        """Test eradicate_pod in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "eradicate": True,
            "delete_contents": False,
        }
        mock_array = Mock()

        eradicate_pod(mock_module, mock_array)

        mock_array.delete_pods.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.delete_with_context")
    def test_eradicate_pod_with_delete_contents(
        self, mock_delete_with_context, mock_check_response
    ):
        """Test eradicate_pod with delete_contents option"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "eradicate": True,
            "delete_contents": True,
        }
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        eradicate_pod(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.delete_with_context")
    def test_eradicate_pod_older_api_version(
        self, mock_delete_with_context, mock_check_response
    ):
        """Test eradicate_pod with older API version"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "eradicate": True,
            "delete_contents": False,
        }
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        eradicate_pod(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePodPromotion:
    """Test cases for update_pod promotion scenarios"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_update_pod_promote_fails_when_stretched(self, mock_get_with_context):
        """Test update_pod promotion fails when pod is stretched"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "quiesce": None,
            "undo": None,
            "priority_adjustment": None,
            "rename": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current config with array_count > 1 (stretched)
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 2  # Stretched pod
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        update_pod(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_update_pod_change_mediator(
        self, mock_get_with_context, mock_patch_with_context
    ):
        """Test update_pod changing mediator"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "new-mediator.example.com",
            "promote": None,
            "quiesce": None,
            "undo": None,
            "priority_adjustment": None,
            "rename": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current config with different mediator
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "old-mediator.example.com"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_update_pod_mediator_change_fails(
        self, mock_get_with_context, mock_patch_with_context
    ):
        """Test update_pod when mediator change fails"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "unreachable-mediator.example.com",
            "promote": None,
            "quiesce": None,
            "undo": None,
            "priority_adjustment": None,
            "rename": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "old-mediator.example.com"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_error = Mock()
        mock_error.message = "Connection failed"
        mock_patch_with_context.return_value = Mock(
            status_code=400, errors=[mock_error]
        )

        update_pod(mock_module, mock_array)

        mock_module.warn.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePodPromoteDemote:
    """Test cases for update_pod promote/demote paths"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_demoted_pod_with_single_undo(
        self,
        mock_lv,
        mock_get_with_context,
        mock_patch_with_context,
        mock_get_undo_pod,
        mock_check_response,
    ):
        """Test promoting a demoted pod with single undo-demote pod"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": True,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "demoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_undo = Mock()
        mock_undo.name = "test-pod.undo-demote.1"
        mock_get_undo_pod.return_value = [mock_undo]
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_demoted_pod_with_multiple_undo(
        self,
        mock_lv,
        mock_get_with_context,
        mock_patch_with_context,
        mock_get_undo_pod,
        mock_check_response,
    ):
        """Test promoting a demoted pod with multiple undo-demote pods"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": True,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "demoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_undo1 = Mock()
        mock_undo1.name = "test-pod.undo-demote.1"
        mock_undo2 = Mock()
        mock_undo2.name = "test-pod.undo-demote.2"
        mock_get_undo_pod.return_value = [mock_undo1, mock_undo2]
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.warn.assert_called_once()  # Warning about remaining undo pods
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_demoted_pod_missing_undo(
        self,
        mock_lv,
        mock_get_with_context,
        mock_get_undo_pod,
    ):
        """Test promoting a demoted pod with missing undo-demote pod"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": True,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "demoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_get_undo_pod.return_value = None  # No undo pod

        update_pod(mock_module, mock_array)

        mock_module.warn.assert_called_once()  # Warning about missing undo pod
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_demoted_pod_without_undo(
        self,
        mock_lv,
        mock_get_with_context,
        mock_patch_with_context,
        mock_check_response,
    ):
        """Test promoting a demoted pod without using undo"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": False,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "demoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_demote_fails_with_existing_undo_pod(
        self,
        mock_lv,
        mock_get_with_context,
        mock_get_undo_pod,
    ):
        """Test demoting a pod fails when undo-demote pod exists"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": False,  # Demote
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_undo = Mock()
        mock_undo.name = "test-pod.undo-demote.1"
        mock_get_undo_pod.return_value = [mock_undo]

        with pytest.raises(SystemExit):
            update_pod(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "undo-demote" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_demote_pod_no_link_targets(
        self,
        mock_lv,
        mock_get_with_context,
        mock_patch_with_context,
        mock_get_undo_pod,
        mock_check_response,
    ):
        """Test demoting a pod with no link targets"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": False,  # Demote
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"
        mock_config.__getitem__ = lambda self, key: (
            0 if key == "link_target_count" else None
        )
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_get_undo_pod.return_value = None  # No undo pod
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_demote_pod_with_quiesce(
        self,
        mock_lv,
        mock_get_with_context,
        mock_patch_with_context,
        mock_get_undo_pod,
        mock_check_response,
    ):
        """Test demoting a pod with quiesce enabled"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": False,  # Demote
            "undo": None,
            "quiesce": True,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"
        mock_config.__getitem__ = lambda self, key: (
            1 if key == "link_target_count" else None
        )
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_get_undo_pod.return_value = None  # No undo pod
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_demote_pod_skip_quiesce(
        self,
        mock_lv,
        mock_get_with_context,
        mock_patch_with_context,
        mock_get_undo_pod,
        mock_check_response,
    ):
        """Test demoting a pod with skip quiesce"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": False,  # Demote
            "undo": None,
            "quiesce": False,  # Skip quiesce
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"
        mock_config.__getitem__ = lambda self, key: (
            1 if key == "link_target_count" else None
        )
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_get_undo_pod.return_value = None  # No undo pod
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePodQuota:
    """Test cases for update_pod quota path"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.human_to_bytes")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_update_pod_quota_changed(
        self,
        mock_lv,
        mock_human_to_bytes,
        mock_get_with_context,
        mock_patch_with_context,
        mock_check_response,
    ):
        """Test updating pod quota when changed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": None,
            "quiesce": None,
            "undo": None,
            "quota": "10G",
            "ignore_usage": False,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.quota_limit = 1073741824  # 1G
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_human_to_bytes.return_value = 10737418240  # 10G
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.human_to_bytes")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_update_pod_quota_unchanged(
        self,
        mock_lv,
        mock_human_to_bytes,
        mock_get_with_context,
    ):
        """Test updating pod quota when unchanged"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": None,
            "quiesce": None,
            "undo": None,
            "quota": "10G",
            "ignore_usage": False,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.quota_limit = 10737418240  # 10G
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])
        mock_human_to_bytes.return_value = 10737418240  # 10G (same)

        update_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestDeletePodSuccess:
    """Test cases for delete_pod success scenarios"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    def test_delete_pod_success(self, mock_patch_with_context, mock_check_response):
        """Test delete_pod successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "delete_contents": False,
            "eradicate": False,
        }
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        delete_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_delete_pod_check_mode(self):
        """Test delete_pod in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "delete_contents": False,
            "eradicate": False,
        }
        mock_array = Mock()

        delete_pod(mock_module, mock_array)

        mock_array.patch_pods.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    def test_delete_pod_older_api(self, mock_patch_with_context, mock_check_response):
        """Test delete_pod with older API version"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "delete_contents": True,
            "eradicate": False,
        }
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        delete_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.delete_with_context")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    def test_delete_pod_with_eradicate(
        self, mock_patch_with_context, mock_delete_with_context, mock_check_response
    ):
        """Test delete_pod with eradicate option"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "delete_contents": False,
            "eradicate": True,
        }
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)
        mock_delete_with_context.return_value = Mock(status_code=200)

        delete_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestGetUndoPod:
    """Test cases for get_undo_pod function"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_undo_pod_found(self, mock_get_with_context):
        """Test get_undo_pod returns pods when found"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_pod = Mock()
        mock_pod.name = "test-pod.undo-demote.1"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pod])

        result = get_undo_pod(mock_module, mock_array)

        assert result == [mock_pod]

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_undo_pod_empty_list_returns_none(self, mock_get_with_context):
        """Test get_undo_pod returns None when API returns empty list"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        # API returns 200 but with empty items list
        mock_get_with_context.return_value = Mock(status_code=200, items=[])

        result = get_undo_pod(mock_module, mock_array)

        assert result is None

    @patch("plugins.modules.purefa_pod.get_with_context")
    def test_get_undo_pod_not_found(self, mock_get_with_context):
        """Test get_undo_pod returns None when not found"""
        mock_module = Mock()
        mock_module.params = {"name": "test-pod", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404)

        result = get_undo_pod(mock_module, mock_array)

        assert result is None


class TestUpdatePodIdempotency:
    """Test cases for update_pod idempotency with promote/demote"""

    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_already_promoted_pod_is_idempotent(
        self, mock_lv, mock_get_with_context
    ):
        """Test that promoting an already promoted pod doesn't change anything"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"  # Already promoted
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        update_pod(mock_module, mock_array)

        # Should exit without changes since already promoted
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_demote_already_demoted_pod_is_idempotent(
        self, mock_lv, mock_get_with_context
    ):
        """Test that demoting an already demoted pod doesn't change anything"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": False,  # Demote
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "demoted"  # Already demoted
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        update_pod(mock_module, mock_array)

        # Should exit without changes since already demoted
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestPromoteDemotePod:
    """Test promote/demote pod logic with quiesce options"""

    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_demoted_pod_with_undo(
        self, mock_lv, mock_get_with_context, mock_get_undo_pod, mock_patch_with_context
    ):
        """Test promoting a demoted pod with undo-demote pods"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "demoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        # Undo pod exists
        mock_undo = Mock()
        mock_undo.name = "test-pod.undo-demote.1"
        mock_get_undo_pod.return_value = [mock_undo]
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_demoted_pod_multiple_undo_pods(
        self, mock_lv, mock_get_with_context, mock_get_undo_pod, mock_patch_with_context
    ):
        """Test promoting a demoted pod with multiple undo-demote pods"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "demoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        # Multiple undo pods
        mock_undo1 = Mock()
        mock_undo1.name = "test-pod.undo-demote.1"
        mock_undo2 = Mock()
        mock_undo2.name = "test-pod.undo-demote.2"
        mock_get_undo_pod.return_value = [mock_undo1, mock_undo2]
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.warn.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_no_undo_pod_but_undo_true(
        self, mock_lv, mock_get_with_context, mock_get_undo_pod, mock_patch_with_context
    ):
        """Test promoting when undo=True but no undo pods exist"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": True,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "demoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        # No undo pods
        mock_get_undo_pod.return_value = []

        update_pod(mock_module, mock_array)

        mock_module.warn.assert_called()
        # Changed should be False since we can't promote without undo pods
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_without_undo(
        self, mock_lv, mock_get_with_context, mock_get_undo_pod, mock_patch_with_context
    ):
        """Test promoting without undo flag"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": False,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "demoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        mock_get_undo_pod.return_value = []
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_demote_promoted_pod_has_undo_pods_fails(
        self, mock_lv, mock_get_with_context, mock_get_undo_pod, mock_check_response
    ):
        """Test demoting when undo pods exist fails"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": False,
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        # Make fail_json exit
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        # Undo pod exists
        mock_undo = Mock()
        mock_undo.name = "test-pod.undo-demote.1"
        mock_get_undo_pod.return_value = [mock_undo]

        try:
            update_pod(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        assert "undo-demote pod not being eradicated" in str(
            mock_module.fail_json.call_args
        )

    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_demote_pod_with_skip_quiesce(
        self, mock_lv, mock_get_with_context, mock_get_undo_pod, mock_patch_with_context
    ):
        """Test demoting a pod with skip_quiesce (quiesce=False)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": False,
            "undo": None,
            "quiesce": False,  # Skip quiesce
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"
        mock_config.__getitem__ = Mock(return_value=1)  # link_target_count = 1
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        mock_get_undo_pod.return_value = []
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        call_args = mock_patch_with_context.call_args
        # Verify skip_quiesce=True is in the call
        assert call_args[1].get("skip_quiesce") is True
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_demote_pod_with_quiesce(
        self, mock_lv, mock_get_with_context, mock_get_undo_pod, mock_patch_with_context
    ):
        """Test demoting a pod with quiesce=True"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": False,
            "undo": None,
            "quiesce": True,  # Quiesce enabled
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"
        mock_config.__getitem__ = Mock(return_value=1)  # link_target_count = 1
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        mock_get_undo_pod.return_value = []
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        call_args = mock_patch_with_context.call_args
        # Verify quiesce=True is in the call
        assert call_args[1].get("quiesce") is True
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_undo_pod")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_demote_pod_no_link_targets(
        self, mock_lv, mock_get_with_context, mock_get_undo_pod, mock_patch_with_context
    ):
        """Test demoting a pod with no link targets"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": False,
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"
        mock_config.__getitem__ = Mock(return_value=0)  # link_target_count = 0
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        mock_get_undo_pod.return_value = []
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        mock_patch_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_promote_quiescing_pod_fails(
        self, mock_lv, mock_get_with_context, mock_check_response
    ):
        """Test promoting a quiescing pod fails"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": True,
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": None,
        }
        # Make fail_json exit
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "quiescing"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_config])

        try:
            update_pod(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        assert "still quiesing" in str(mock_module.fail_json.call_args)


class TestDefaultProtection:
    """Test default protection group logic"""

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.post_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_update_default_protection_group(
        self,
        mock_lv,
        mock_get_with_context,
        mock_post_with_context,
        mock_patch_with_context,
        mock_check_response,
    ):
        """Test updating default protection group"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": None,
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": "new-pg",
            "retention_lock": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Pod config
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"

        # Default protections response
        mock_dp = Mock()
        mock_dp_item = Mock()
        mock_dp_item.name = "old-pg"
        mock_dp.default_protections = [mock_dp_item]

        def get_side_effect(*args, **kwargs):
            if "get_pods" in args:
                return Mock(status_code=200, items=[mock_config])
            elif "get_container_default_protections" in args:
                return Mock(status_code=200, items=[mock_dp])
            elif "get_protection_groups" in args:
                return Mock(status_code=404)  # PG doesn't exist
            return Mock(status_code=200)

        mock_get_with_context.side_effect = get_side_effect
        mock_post_with_context.return_value = Mock(status_code=200)
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_pod(mock_module, mock_array)

        # Should have created the new PG and updated default protection
        mock_post_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pod.check_response")
    @patch("plugins.modules.purefa_pod.patch_with_context")
    @patch("plugins.modules.purefa_pod.get_with_context")
    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    def test_default_protection_no_change(
        self,
        mock_lv,
        mock_get_with_context,
        mock_patch_with_context,
        mock_check_response,
    ):
        """Test default protection when already set correctly"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pod",
            "context": "",
            "failover": None,
            "mediator": "purestorage",
            "promote": None,
            "undo": None,
            "quiesce": None,
            "quota": None,
            "default_protection_pg": "existing-pg",
            "retention_lock": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Pod config
        mock_config = Mock()
        mock_config.failover_preferences = []
        mock_config.mediator = "purestorage"
        mock_config.array_count = 1
        mock_config.promotion_status = "promoted"

        # Default protections response - already set to correct PG
        mock_dp = Mock()
        mock_dp_item = Mock()
        mock_dp_item.name = "existing-pg"
        mock_dp.default_protections = [mock_dp_item]

        def get_side_effect(*args, **kwargs):
            if "get_pods" in args:
                return Mock(status_code=200, items=[mock_config])
            elif "get_container_default_protections" in args:
                return Mock(status_code=200, items=[mock_dp])
            return Mock(status_code=200)

        mock_get_with_context.side_effect = get_side_effect

        update_pod(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestMain:
    """Test main function branches"""

    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_present_pod_not_exists_creates_pod(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
    ):
        """Test main creates pod when state=present and pod doesn't exist"""
        from plugins.modules.purefa_pod import main, create_pod

        mock_module = Mock()
        mock_module.params = {
            "name": "new-pod",
            "state": "present",
            "stretch": None,
            "target": None,
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_get_array.return_value = Mock()
        mock_get_pod.return_value = False
        mock_get_destroyed_pod.return_value = False

        with patch("plugins.modules.purefa_pod.create_pod") as mock_create:
            main()
            mock_create.assert_called_once()

    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_realm_composes_name(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
        mock_lv,
    ):
        """realm parameter composes the realm::pod name (#pod-realm)"""
        from plugins.modules.purefa_pod import main

        mock_module = Mock()
        mock_module.params = {
            "name": "bar",
            "realm": "myrealm",
            "state": "present",
            "stretch": None,
            "target": None,
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.39"
        mock_get_array.return_value = mock_array
        mock_get_pod.return_value = False
        mock_get_destroyed_pod.return_value = False

        with patch("plugins.modules.purefa_pod.create_pod") as mock_create:
            main()
            mock_create.assert_called_once()

        assert mock_module.params["name"] == "myrealm::bar"

    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_realm_conflicts_with_name_separator(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
        mock_lv,
    ):
        """realm plus a '::' name is rejected (#pod-realm)"""
        import pytest
        from plugins.modules.purefa_pod import main

        mock_module = Mock()
        mock_module.params = {
            "name": "already::there",
            "realm": "myrealm",
            "state": "present",
            "stretch": None,
            "target": None,
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.39"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "not both" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pod.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_realm_requires_supported_api(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
        mock_lv,
    ):
        """realm on a pre-2.36 array is rejected (#pod-realm)"""
        import pytest
        from plugins.modules.purefa_pod import main

        mock_module = Mock()
        mock_module.params = {
            "name": "bar",
            "realm": "myrealm",
            "state": "present",
            "stretch": None,
            "target": None,
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "2.36" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_absent_pod_not_exists_no_change(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
    ):
        """Test main exits unchanged when state=absent and pod doesn't exist"""
        from plugins.modules.purefa_pod import main

        mock_module = Mock()
        mock_module.params = {
            "name": "nonexistent-pod",
            "state": "absent",
            "stretch": None,
            "target": None,
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_get_array.return_value = Mock()
        mock_get_pod.return_value = False
        mock_get_destroyed_pod.return_value = False

        main()

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_present_destroyed_recovers_pod(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
    ):
        """Test main recovers pod when state=present and pod is destroyed"""
        from plugins.modules.purefa_pod import main

        mock_module = Mock()
        mock_module.params = {
            "name": "destroyed-pod",
            "state": "present",
            "stretch": None,
            "target": None,
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_get_array.return_value = Mock()
        mock_get_pod.return_value = False
        mock_get_destroyed_pod.return_value = True

        with patch("plugins.modules.purefa_pod.recover_pod") as mock_recover:
            main()
            mock_recover.assert_called_once()

    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_absent_destroyed_eradicates_pod(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
    ):
        """Test main eradicates pod when state=absent and pod is destroyed"""
        from plugins.modules.purefa_pod import main

        mock_module = Mock()
        mock_module.params = {
            "name": "destroyed-pod",
            "state": "absent",
            "stretch": None,
            "target": None,
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_get_array.return_value = Mock()
        mock_get_pod.return_value = False
        mock_get_destroyed_pod.return_value = True

        with patch("plugins.modules.purefa_pod.eradicate_pod") as mock_eradicate:
            main()
            mock_eradicate.assert_called_once()

    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_present_with_stretch_calls_stretch_pod(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
    ):
        """Test main calls stretch_pod when pod exists with stretch parameter"""
        from plugins.modules.purefa_pod import main

        mock_module = Mock()
        mock_module.params = {
            "name": "existing-pod",
            "state": "present",
            "stretch": "remote-array",
            "target": None,
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_get_array.return_value = Mock()
        mock_get_pod.return_value = True
        mock_get_destroyed_pod.return_value = False

        with patch("plugins.modules.purefa_pod.stretch_pod") as mock_stretch:
            main()
            mock_stretch.assert_called_once()

    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_present_with_target_calls_clone_pod(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
    ):
        """Test main calls clone_pod when pod exists with target parameter"""
        from plugins.modules.purefa_pod import main

        mock_module = Mock()
        mock_module.params = {
            "name": "source-pod",
            "state": "present",
            "stretch": None,
            "target": "clone-pod",
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_get_array.return_value = Mock()
        mock_get_pod.return_value = True
        mock_get_destroyed_pod.return_value = False

        with patch("plugins.modules.purefa_pod.clone_pod") as mock_clone:
            main()
            mock_clone.assert_called_once()

    @patch("plugins.modules.purefa_pod.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pod.get_array")
    @patch("plugins.modules.purefa_pod.get_pod")
    @patch("plugins.modules.purefa_pod.get_destroyed_pod")
    @patch("plugins.modules.purefa_pod.check_arrays")
    @patch("plugins.modules.purefa_pod.AnsibleModule")
    def test_main_absent_pod_exists_deletes_pod(
        self,
        mock_ansible,
        mock_check_arrays,
        mock_get_destroyed_pod,
        mock_get_pod,
        mock_get_array,
    ):
        """Test main deletes pod when state=absent and pod exists"""
        from plugins.modules.purefa_pod import main

        mock_module = Mock()
        mock_module.params = {
            "name": "existing-pod",
            "state": "absent",
            "stretch": None,
            "target": None,
            "failover": None,
            "mediator": "purestorage",
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_get_array.return_value = Mock()
        mock_get_pod.return_value = True
        mock_get_destroyed_pod.return_value = False

        with patch("plugins.modules.purefa_pod.delete_pod") as mock_delete:
            main()
            mock_delete.assert_called_once()
