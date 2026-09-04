# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_snap module."""

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

from plugins.modules.purefa_snap import (
    _check_offload,
    _check_target,
    _check_offload_snapshot,
    get_volume,
    get_target,
    get_snapshot,
    get_deleted_snapshot,
    create_snapshot,
    create_from_snapshot,
    update_snapshot,
    delete_snapshot,
    eradicate_snapshot,
    recover_snapshot,
)
import plugins.modules.purefa_snap as _snap_module


def _passthrough_with_context(client, method_name, context_version, module, **kwargs):
    """Mirror api_helpers.*_with_context for tests (api_helpers is mocked out).

    Adds context_names only when the API version supports it and a context is
    set, matching the real helper so both old-API and context assertions hold.
    """
    api_version = client.get_rest_version()
    if LooseVersion(context_version) <= LooseVersion(api_version) and module.params.get(
        "context"
    ):
        kwargs["context_names"] = [module.params["context"]]
    return getattr(client, method_name)(**kwargs)


_snap_module.get_with_context = _passthrough_with_context
_snap_module.post_with_context = _passthrough_with_context
_snap_module.patch_with_context = _passthrough_with_context
_snap_module.delete_with_context = _passthrough_with_context


class TestCheckOffload:
    """Test cases for _check_offload function"""

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_check_offload_connected(self, mock_loose_version):
        """Test _check_offload returns True when offload is connected"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"offload": "nfs-target", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_offload = Mock()
        mock_offload.status = "connected"
        mock_array.get_offloads.return_value = Mock(
            status_code=200, items=[mock_offload]
        )

        result = _check_offload(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_check_offload_not_connected(self, mock_loose_version):
        """Test _check_offload returns False when offload is not connected"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"offload": "nfs-target", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_offloads.return_value = Mock(status_code=404)

        result = _check_offload(mock_module, mock_array)

        assert result is False

    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_check_offload_with_context_api(self, mock_lv):
        """Test _check_offload with context API version"""
        mock_module = Mock()
        mock_module.params = {"offload": "nfs-target", "context": "pod1"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_offload = Mock()
        mock_offload.status = "connected"
        mock_array.get_offloads.return_value = Mock(
            status_code=200, items=[mock_offload]
        )

        result = _check_offload(mock_module, mock_array)

        assert result is True
        mock_array.get_offloads.assert_called_once_with(
            names=["nfs-target"], context_names=["pod1"]
        )


class TestCheckTarget:
    """Test cases for _check_target function"""

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_check_target_connected(self, mock_loose_version):
        """Test _check_target returns True when target is connected"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"offload": "array-target", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_conn = Mock()
        mock_conn.status = "connected"
        mock_array.get_array_connections.return_value = Mock(
            status_code=200, items=[mock_conn]
        )

        result = _check_target(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_check_target_with_context_api(self, mock_lv):
        """Test _check_target with context API version"""
        mock_module = Mock()
        mock_module.params = {"offload": "array-target", "context": "pod1"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_conn = Mock()
        mock_conn.status = "connected"
        mock_array.get_array_connections.return_value = Mock(
            status_code=200, items=[mock_conn]
        )

        result = _check_target(mock_module, mock_array)

        assert result is True
        mock_array.get_array_connections.assert_called_once_with(
            names=["array-target"], context_names=["pod1"]
        )

    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_check_target_not_connected(self, mock_lv):
        """Test _check_target returns False when target not connected"""
        mock_module = Mock()
        mock_module.params = {"offload": "array-target", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_array_connections.return_value = Mock(status_code=404)

        result = _check_target(mock_module, mock_array)

        assert result is False


class TestGetVolume:
    """Test cases for get_volume function"""

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_get_volume_exists(self, mock_loose_version):
        """Test get_volume returns volume when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-vol", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_vol = Mock()
        mock_vol.name = "test-vol"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])

        result = get_volume(mock_module, mock_array)

        assert result == mock_vol

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_get_volume_not_exists(self, mock_loose_version):
        """Test get_volume returns None when volume doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volumes.return_value = Mock(status_code=404)

        result = get_volume(mock_module, mock_array)

        assert result is None


class TestGetTarget:
    """Test cases for get_target function"""

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_get_target_exists(self, mock_loose_version):
        """Test get_target returns target when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"target": "target-vol", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_vol = Mock()
        mock_vol.name = "target-vol"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])

        result = get_target(mock_module, mock_array)

        assert result == mock_vol


class TestGetSnapshot:
    """Test cases for get_snapshot function"""

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_get_snapshot_exists(self, mock_loose_version):
        """Test get_snapshot returns True when snapshot exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-vol", "suffix": "snap1", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_snapshots.return_value = Mock(status_code=200)

        result = get_snapshot(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_get_snapshot_not_exists(self, mock_loose_version):
        """Test get_snapshot returns False when snapshot doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-vol", "suffix": "snap1", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_snapshots.return_value = Mock(status_code=404)

        result = get_snapshot(mock_module, mock_array)

        assert result is False


class TestCreateSnapshot:
    """Test cases for create_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_create_snapshot_check_mode(self, mock_loose_version, mock_check_response):
        """Test create_snapshot in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-vol", "suffix": "snap1", "offload": None}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        create_snapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True, suffix="snap1")


class TestDeleteSnapshot:
    """Test cases for delete_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_delete_snapshot_check_mode(self, mock_loose_version, mock_check_response):
        """Test delete_snapshot in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "eradicate": False,
            "offload": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        delete_snapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicateSnapshot:
    """Test cases for eradicate_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_eradicate_snapshot_check_mode(
        self, mock_loose_version, mock_check_response
    ):
        """Test eradicate_snapshot in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-vol", "suffix": "snap1"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        eradicate_snapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverSnapshot:
    """Test cases for recover_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_recover_snapshot_check_mode(self, mock_loose_version, mock_check_response):
        """Test recover_snapshot in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "overwrite": False,
            "target": None,
            "offload": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        recover_snapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCheckOffloadSnapshot:
    """Test cases for _check_offload_snapshot function"""

    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_check_offload_snapshot_exists(
        self, mock_loose_version, mock_check_offload
    ):
        """Test _check_offload_snapshot returns snapshot when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "offload-target",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        # Mock array.get_arrays().items
        mock_local_array = Mock()
        mock_local_array.name = "local-array"
        mock_array.get_arrays.return_value.items = [mock_local_array]
        mock_snap = Mock()
        mock_snap.name = "offload-target:test-vol.snap1"
        mock_array.get_remote_volume_snapshots.return_value.status_code = 200
        mock_array.get_remote_volume_snapshots.return_value.items = [mock_snap]

        result = _check_offload_snapshot(mock_module, mock_array)

        assert result is not None

    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_check_offload_snapshot_not_exists(
        self, mock_loose_version, mock_check_offload
    ):
        """Test _check_offload_snapshot returns None when snapshot doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "offload-target",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        # Mock array.get_arrays().items
        mock_local_array = Mock()
        mock_local_array.name = "local-array"
        mock_array.get_arrays.return_value.items = [mock_local_array]
        mock_array.get_remote_volume_snapshots.return_value.status_code = 404

        result = _check_offload_snapshot(mock_module, mock_array)

        assert result is None


class TestGetDeletedSnapshot:
    """Test cases for get_deleted_snapshot function"""

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_get_deleted_snapshot_exists(self, mock_loose_version):
        """Test get_deleted_snapshot returns snapshot when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-vol", "suffix": "snap1", "offload": None}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_snap = Mock()
        mock_array.get_volume_snapshots.return_value.status_code = 200
        mock_array.get_volume_snapshots.return_value.items = [mock_snap]

        result = get_deleted_snapshot(mock_module, mock_array)

        assert result is not None

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_get_deleted_snapshot_not_exists(self, mock_loose_version):
        """Test get_deleted_snapshot returns False when snapshot doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-vol", "suffix": "snap1", "offload": None}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_snapshots.return_value.status_code = 404

        result = get_deleted_snapshot(mock_module, mock_array)

        # get_deleted_snapshot returns bool, not None
        assert result is False

    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_get_deleted_snapshot_offload_remote_context(
        self, mock_lv, mock_check_offload
    ):
        """Test get_deleted_snapshot with offload and context API"""
        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "pod1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_arr_item = Mock()
        mock_arr_item.name = "local-array"
        mock_array.get_arrays.return_value = Mock(items=[mock_arr_item])
        mock_array.get_remote_volume_snapshots.return_value = Mock(status_code=200)

        result = get_deleted_snapshot(mock_module, mock_array)

        assert result is True
        mock_array.get_remote_volume_snapshots.assert_called_once()

    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_get_deleted_snapshot_offload_remote_no_context(
        self, mock_lv, mock_check_offload
    ):
        """Test get_deleted_snapshot with offload, no context API"""
        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_arr_item = Mock()
        mock_arr_item.name = "local-array"
        mock_array.get_arrays.return_value = Mock(items=[mock_arr_item])
        mock_array.get_remote_volume_snapshots.return_value = Mock(status_code=200)

        result = get_deleted_snapshot(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_get_deleted_snapshot_offload_local_context(
        self, mock_lv, mock_check_offload
    ):
        """Test get_deleted_snapshot with offload but local snapshot using context API"""
        mock_check_offload.return_value = False  # Not an offload target
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "pod1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_arr_item = Mock()
        mock_arr_item.name = "local-array"
        mock_array.get_arrays.return_value = Mock(items=[mock_arr_item])
        mock_array.get_volume_snapshots.return_value = Mock(status_code=200)

        result = get_deleted_snapshot(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_get_deleted_snapshot_offload_local_no_context(
        self, mock_lv, mock_check_offload
    ):
        """Test get_deleted_snapshot with offload but local snapshot, no context API"""
        mock_check_offload.return_value = False
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_arr_item = Mock()
        mock_arr_item.name = "local-array"
        mock_array.get_arrays.return_value = Mock(items=[mock_arr_item])
        mock_array.get_volume_snapshots.return_value = Mock(status_code=200)

        result = get_deleted_snapshot(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_get_deleted_snapshot_with_context_api(self, mock_lv):
        """Test get_deleted_snapshot with context API version"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "context": "pod1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volume_snapshots.return_value = Mock(status_code=200)

        result = get_deleted_snapshot(mock_module, mock_array)

        assert result is True
        mock_array.get_volume_snapshots.assert_called_once_with(
            names=["test-vol.snap1"], context_names=["pod1"], destroyed=True
        )


class TestCreateFromSnapshot:
    """Test cases for create_from_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_create_from_snapshot_check_mode(
        self, mock_loose_version, mock_check_response
    ):
        """Test create_from_snapshot in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "target": "new-vol",
            "overwrite": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        create_from_snapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSnapshot:
    """Test cases for update_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_update_snapshot_check_mode(self, mock_loose_version, mock_check_response):
        """Test update_snapshot in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "rename": "new-suffix",
            "target": None,
            "offload": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        update_snapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateSnapshotSuccess:
    """Additional test cases for create_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_create_snapshot_success(self, mock_loose_version, mock_check_response):
        """Test create_snapshot successfully creates"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "throttle": True,
            "context": "pod1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volume_snapshots.return_value = Mock(status_code=200)

        create_snapshot(mock_module, mock_array)

        mock_array.post_volume_snapshots.assert_called_once()
        # exit_json is called with changed=True and suffix
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_create_snapshot_offload_context_api(self, mock_lv, mock_check_response):
        """Test create_snapshot with offload using context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "pod1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_remote_volume_snapshots.return_value = Mock(status_code=200)

        create_snapshot(mock_module, mock_array)

        mock_array.post_remote_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_create_snapshot_offload_no_context_with_suffix(
        self, mock_lv, mock_check_response
    ):
        """Test create_snapshot with offload, no context API, with suffix"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
        }
        mock_array = Mock()
        # Version must be >= SNAPSHOT_SUFFIX_API (2.28) and < CONTEXT_API_VERSION (2.38)
        mock_array.get_rest_version.return_value = "2.30"
        mock_array.post_remote_volume_snapshots.return_value = Mock(status_code=200)

        create_snapshot(mock_module, mock_array)

        mock_array.post_remote_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_create_snapshot_offload_no_context_no_suffix(
        self, mock_lv, mock_check_response
    ):
        """Test create_snapshot with offload, no context API, no suffix (old API)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",  # Will be set to None by the code
            "offload": "nfs-target",
            "context": "",
        }
        mock_array = Mock()
        # Version < SNAPSHOT_SUFFIX_API (2.28) - suffix will be nulled and set from response
        mock_array.get_rest_version.return_value = "2.20"
        mock_snap_item = Mock()
        mock_snap_item.name = "test-vol.auto-suffix"
        mock_array.post_remote_volume_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap_item]
        )

        create_snapshot(mock_module, mock_array)

        mock_array.post_remote_volume_snapshots.assert_called_once()
        # Suffix is extracted from response
        assert mock_module.params["suffix"] == "auto-suffix"
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_create_snapshot_offload_old_api_returns_suffix(
        self, mock_lv, mock_check_response
    ):
        """Test create_snapshot with offload on old API extracting suffix"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
        }
        mock_array = Mock()
        # SNAPSHOT_SUFFIX_API is 2.28, so using 2.20 is older
        mock_array.get_rest_version.return_value = "2.20"
        mock_snap_item = Mock()
        mock_snap_item.name = "test-vol.auto-generated-suffix"
        mock_array.post_remote_volume_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap_item]
        )

        create_snapshot(mock_module, mock_array)

        mock_array.post_remote_volume_snapshots.assert_called_once()
        assert mock_module.params["suffix"] == "auto-generated-suffix"

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_create_snapshot_local_no_throttle_api(self, mock_lv, mock_check_response):
        """Test create_snapshot local when throttle API is not available"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "throttle": False,
            "context": "",
        }
        mock_array = Mock()
        # THROTTLE_API is 2.25, so using 2.20 is older
        mock_array.get_rest_version.return_value = "2.20"
        mock_array.post_volume_snapshots.return_value = Mock(status_code=200)

        create_snapshot(mock_module, mock_array)

        mock_array.post_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_create_snapshot_local_throttle_no_context(
        self, mock_lv, mock_check_response
    ):
        """Test create_snapshot local with throttle API but no context"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "throttle": True,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_array.post_volume_snapshots.return_value = Mock(status_code=200)

        create_snapshot(mock_module, mock_array)

        mock_array.post_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once()


class TestDeleteSnapshotSuccess:
    """Additional test cases for delete_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_delete_snapshot_success(self, mock_loose_version, mock_check_response):
        """Test delete_snapshot successfully deletes"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "target": None,
            "offload": None,
            "context": "",
            "eradicate": False,
            "ignore_repl": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volume_snapshots.return_value = Mock(status_code=200)

        delete_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicateSnapshotSuccess:
    """Test cases for eradicate_snapshot success paths"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_eradicate_snapshot_success(self, mock_loose_version, mock_check_response):
        """Test eradicate_snapshot successfully eradicates"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "context": "",
            "ignore_repl": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_volume_snapshots.return_value = Mock(status_code=200)

        eradicate_snapshot(mock_module, mock_array)

        mock_array.delete_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverSnapshotSuccess:
    """Test cases for recover_snapshot success paths"""

    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_recover_snapshot_success(self, mock_loose_version):
        """Test recover_snapshot successfully recovers"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "target": None,
            "context": "",
            "ignore_repl": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volume_snapshot.return_value = Mock(status_code=200)

        recover_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSnapshotSuccess:
    """Test cases for update_snapshot success paths"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion")
    def test_update_snapshot_success(self, mock_loose_version, mock_check_response):
        """Test update_snapshot successfully updates"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "old-suffix",
            "target": "new-suffix",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volume_snapshots.return_value = Mock(status_code=200)

        update_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateFromSnapshotSuccess:
    """Test cases for create_from_snapshot success paths"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.get_target")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_create_from_snapshot_new_volume(
        self, mock_lv, mock_get_target, mock_check_response
    ):
        """Test creating new volume from snapshot"""
        mock_get_target.return_value = None  # Target doesn't exist
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-vol",
            "suffix": "snap1",
            "target": "new-vol",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = Mock(status_code=200)

        create_from_snapshot(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.get_target")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_create_from_snapshot_overwrite(
        self, mock_lv, mock_get_target, mock_check_response
    ):
        """Test creating volume from snapshot with overwrite"""
        mock_get_target.return_value = Mock()  # Target exists
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-vol",
            "suffix": "snap1",
            "target": "existing-vol",
            "overwrite": True,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = Mock(status_code=200)

        create_from_snapshot(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.get_target")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_create_from_snapshot_no_overwrite(self, mock_lv, mock_get_target):
        """Test creating volume from snapshot when target exists and no overwrite"""
        mock_get_target.return_value = Mock()  # Target exists
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-vol",
            "suffix": "snap1",
            "target": "existing-vol",
            "overwrite": False,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        create_from_snapshot(mock_module, mock_array)

        mock_array.post_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestDeleteSnapshotOffload:
    """Test cases for delete_snapshot with offload scenarios"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_offload_with_eradicate(
        self, mock_lv, mock_check_offload, mock_check_response
    ):
        """Test deleting snapshot from offload with eradicate"""
        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vol1",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
            "eradicate": True,
            "ignore_repl": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_local_array = Mock()
        mock_local_array.name = "local-array"
        mock_array.get_arrays.return_value = Mock(items=[mock_local_array])
        mock_array.patch_remote_volume_snapshots.return_value = Mock(status_code=200)
        mock_array.delete_remote_volume_snapshots.return_value = Mock(status_code=200)

        delete_snapshot(mock_module, mock_array)

        mock_array.patch_remote_volume_snapshots.assert_called_once()
        mock_array.delete_remote_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap._check_target")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_local_with_eradicate(
        self, mock_lv, mock_check_target, mock_check_offload, mock_check_response
    ):
        """Test deleting local snapshot with eradicate"""
        mock_check_offload.return_value = False
        mock_check_target.return_value = False
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vol1",
            "suffix": "snap1",
            "offload": None,
            "context": "",
            "eradicate": True,
            "ignore_repl": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volume_snapshots.return_value = Mock(status_code=200)
        mock_array.delete_volume_snapshots.return_value = Mock(status_code=200)

        delete_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshots.assert_called_once()
        mock_array.delete_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSnapshotExtended:
    """Extended test cases for update_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_update_snapshot_older_api(self, mock_lv, mock_check_response):
        """Test renaming snapshot with older API version"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vol1",
            "suffix": "snap1",
            "target": "snap2",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.16"
        mock_array.patch_volume_snapshots.return_value = Mock(status_code=200)

        update_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshots.assert_called_once()
        call_kwargs = mock_array.patch_volume_snapshots.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverSnapshotExtended:
    """Extended test cases for recover_snapshot function"""

    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_recover_snapshot_local_success(self, mock_lv, mock_check_offload):
        """Test recovering local snapshot"""
        mock_check_offload.return_value = False
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vol1",
            "suffix": "snap1",
            "offload": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volume_snapshot.return_value = Mock(status_code=200)

        recover_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicateSnapshotExtended:
    """Extended test cases for eradicate_snapshot function"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_snapshot_local_success(
        self, mock_lv, mock_check_offload, mock_check_response
    ):
        """Test eradicating local snapshot"""
        mock_check_offload.return_value = False
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vol1",
            "suffix": "snap1",
            "offload": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_volume_snapshots.return_value = Mock(status_code=200)

        eradicate_snapshot(mock_module, mock_array)

        mock_array.delete_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteSnapshotTarget:
    """Test cases for delete_snapshot with target scenarios"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap._check_target")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_target_with_eradicate_context_api(
        self, mock_lv, mock_check_target, mock_check_offload, mock_check_response
    ):
        """Test deleting snapshot via target with eradicate using context API"""
        mock_check_offload.return_value = False
        mock_check_target.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vol1",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "pod1",
            "eradicate": True,
            "ignore_repl": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volume_snapshots.return_value = Mock(status_code=200)
        mock_array.delete_volume_snapshots.return_value = Mock(status_code=200)

        delete_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshots.assert_called_once()
        mock_array.delete_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap._check_target")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_target_without_eradicate_no_context(
        self, mock_lv, mock_check_target, mock_check_offload, mock_check_response
    ):
        """Test deleting snapshot via target without eradicate"""
        mock_check_offload.return_value = False
        mock_check_target.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vol1",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": None,
            "eradicate": False,
            "ignore_repl": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Below context API version
        mock_array.patch_volume_snapshots.return_value = Mock(status_code=200)

        delete_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshots.assert_called_once()
        mock_array.delete_volume_snapshots.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap._check_target")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_delete_snapshot_target_eradicate_no_context(
        self, mock_lv, mock_check_target, mock_check_offload, mock_check_response
    ):
        """Test deleting snapshot via target with eradicate, no context API"""
        mock_check_offload.return_value = False
        mock_check_target.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vol1",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": None,
            "eradicate": True,
            "ignore_repl": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_array.patch_volume_snapshots.return_value = Mock(status_code=200)
        mock_array.delete_volume_snapshots.return_value = Mock(status_code=200)

        delete_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshots.assert_called_once()
        mock_array.delete_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverSnapshotPaths:
    """Test cases for recover_snapshot function with different paths"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_recover_snapshot_offload_context_api(
        self, mock_lv, mock_check_offload, mock_check_response
    ):
        """Test recover_snapshot with offload using context API"""
        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "pod1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_arr_item = Mock()
        mock_arr_item.name = "local-array"
        mock_array.get_arrays.return_value = Mock(items=[mock_arr_item])
        mock_array.patch_remote_volume_snapshots.return_value = Mock(status_code=200)

        recover_snapshot(mock_module, mock_array)

        mock_array.patch_remote_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_recover_snapshot_offload_no_context(
        self, mock_lv, mock_check_offload, mock_check_response
    ):
        """Test recover_snapshot with offload, no context API"""
        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_arr_item = Mock()
        mock_arr_item.name = "local-array"
        mock_array.get_arrays.return_value = Mock(items=[mock_arr_item])
        mock_array.patch_remote_volume_snapshots.return_value = Mock(status_code=200)

        recover_snapshot(mock_module, mock_array)

        mock_array.patch_remote_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_recover_snapshot_local_context_api(self, mock_lv):
        """Test recover_snapshot local with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "context": "pod1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volume_snapshot.return_value = Mock(status_code=200)

        recover_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_recover_snapshot_local_no_context(self, mock_lv):
        """Test recover_snapshot local without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_array.patch_volume_snapshot.return_value = Mock(status_code=200)

        recover_snapshot(mock_module, mock_array)

        mock_array.patch_volume_snapshot.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_recover_snapshot_local_failure(self, mock_lv):
        """Test recover_snapshot local when API returns error"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "context": "",
        }
        mock_module.fail_json = Mock(side_effect=SystemExit(1))
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_error = Mock()
        mock_error.message = "Snapshot not found"
        mock_array.patch_volume_snapshot.return_value = Mock(
            status_code=400, errors=[mock_error]
        )

        import pytest

        with pytest.raises(SystemExit):
            recover_snapshot(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestEradicateSnapshotPaths:
    """Test cases for eradicate_snapshot function with different paths"""

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_snapshot_offload_context_api(
        self, mock_lv, mock_check_offload, mock_check_response
    ):
        """Test eradicate_snapshot with offload using context API"""
        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "pod1",
            "ignore_repl": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_arr_item = Mock()
        mock_arr_item.name = "local-array"
        mock_array.get_arrays.return_value = Mock(items=[mock_arr_item])
        mock_array.delete_remote_volume_snapshots.return_value = Mock(status_code=200)

        eradicate_snapshot(mock_module, mock_array)

        mock_array.delete_remote_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_snapshot_offload_no_context(
        self, mock_lv, mock_check_offload, mock_check_response
    ):
        """Test eradicate_snapshot with offload, no context API"""
        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
            "ignore_repl": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_arr_item = Mock()
        mock_arr_item.name = "local-array"
        mock_array.get_arrays.return_value = Mock(items=[mock_arr_item])
        mock_array.delete_remote_volume_snapshots.return_value = Mock(status_code=200)

        eradicate_snapshot(mock_module, mock_array)

        mock_array.delete_remote_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap._check_target")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_snapshot_target_context_api(
        self, mock_lv, mock_check_target, mock_check_offload, mock_check_response
    ):
        """Test eradicate_snapshot via target with context API"""
        mock_check_offload.return_value = False
        mock_check_target.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "array-target",
            "context": "pod1",
            "ignore_repl": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_volume_snapshots.return_value = Mock(status_code=200)

        eradicate_snapshot(mock_module, mock_array)

        mock_array.delete_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap._check_offload")
    @patch("plugins.modules.purefa_snap._check_target")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_snapshot_target_no_context(
        self, mock_lv, mock_check_target, mock_check_offload, mock_check_response
    ):
        """Test eradicate_snapshot via target without context API"""
        mock_check_offload.return_value = False
        mock_check_target.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": "array-target",
            "context": "",
            "ignore_repl": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_array.delete_volume_snapshots.return_value = Mock(status_code=200)

        eradicate_snapshot(mock_module, mock_array)

        mock_array.delete_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_snapshot_local_context_api(self, mock_lv, mock_check_response):
        """Test eradicate_snapshot local with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "context": "pod1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_volume_snapshots.return_value = Mock(status_code=200)

        eradicate_snapshot(mock_module, mock_array)

        mock_array.delete_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snap.check_response")
    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_snapshot_local_no_context(self, mock_lv, mock_check_response):
        """Test eradicate_snapshot local without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "suffix": "snap1",
            "offload": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_array.delete_volume_snapshots.return_value = Mock(status_code=200)

        eradicate_snapshot(mock_module, mock_array)

        mock_array.delete_volume_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestStateCopySnapshotNotFound:
    """Test cases for state=copy when snapshot does not exist (issue #978)"""

    @patch("plugins.modules.purefa_snap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_snap.get_deleted_snapshot")
    @patch("plugins.modules.purefa_snap.get_snapshot")
    @patch("plugins.modules.purefa_snap.get_volume")
    @patch("plugins.modules.purefa_snap._check_target")
    @patch("plugins.modules.purefa_snap.get_array")
    @patch("plugins.modules.purefa_snap.AnsibleModule")
    def test_state_copy_snapshot_not_found_fails(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_target,
        mock_get_volume,
        mock_get_snapshot,
        mock_get_deleted_snapshot,
        mock_lv,
    ):
        """Test that state=copy fails with error when snapshot doesn't exist"""
        from plugins.modules.purefa_snap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "test-volume",
            "suffix": "snap1",
            "target": "new-volume",
            "state": "copy",
            "offload": None,
            "context": "",
            "overwrite": True,
            "eradicate": False,
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_arrays.return_value.items = [Mock()]
        mock_get_array.return_value = mock_array

        mock_check_target.return_value = True
        mock_get_volume.return_value = Mock()  # Volume exists
        mock_get_snapshot.return_value = False  # Snapshot does NOT exist
        mock_get_deleted_snapshot.return_value = False  # Not in trash either

        main()

        # Should fail with error message about snapshot not found
        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args
        assert "test-volume.snap1" in call_args[1]["msg"]
        assert "not found" in call_args[1]["msg"].lower()
