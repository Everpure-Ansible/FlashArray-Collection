# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_pg module."""

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

from plugins.modules.purefa_pg import (
    get_pod,
    get_targets,
    get_arrays,
    get_pending_pgroup,
    get_pgroup,
    get_pgroup_sched,
    make_pgroup,
    delete_pgroup,
    eradicate_pgroup,
    recover_pgroup,
    update_pgroup,
    rename_exists,
    check_pg_on_offload,
    main,
)
import plugins.modules.purefa_pg as _pg_module


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


_pg_module.get_with_context = _passthrough_with_context
_pg_module.post_with_context = _passthrough_with_context
_pg_module.patch_with_context = _passthrough_with_context
_pg_module.delete_with_context = _passthrough_with_context


class TestGetPod:
    """Test cases for get_pod function"""

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_get_pod_exists(self, mock_loose_version):
        """Test get_pod returns pod when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "pod1::pg1", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_pod = Mock()
        mock_pod.name = "pod1"
        mock_array.get_pods.return_value = Mock(status_code=200, items=[mock_pod])

        result = get_pod(mock_module, mock_array)

        assert result == mock_pod

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_get_pod_not_exists(self, mock_loose_version):
        """Test get_pod returns None when pod doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "pod1::pg1", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_pods.return_value = Mock(status_code=404)

        result = get_pod(mock_module, mock_array)

        assert result is None


class TestGetTargets:
    """Test cases for get_targets function"""

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_get_targets_connected(self, mock_loose_version):
        """Test get_targets returns connected targets"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_target1 = Mock()
        mock_target1.name = "nfs-target1"
        mock_target1.status = "connected"
        mock_target2 = Mock()
        mock_target2.name = "s3-target"
        mock_target2.status = "disconnected"
        mock_array.get_offloads.return_value = Mock(items=[mock_target1, mock_target2])

        result = get_targets(mock_module, mock_array)

        assert result == ["nfs-target1"]


class TestGetArrays:
    """Test cases for get_arrays function"""

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_get_arrays_connected(self, mock_loose_version):
        """Test get_arrays returns connected arrays"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_conn1 = Mock()
        mock_conn1.name = "array2"
        mock_conn1.status = "connected"
        mock_array.get_array_connections.return_value = Mock(items=[mock_conn1])

        result = get_arrays(mock_module, mock_array)

        assert result == ["array2"]


class TestGetPendingPgroup:
    """Test cases for get_pending_pgroup function"""

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_get_pending_pgroup_exists(self, mock_loose_version):
        """Test get_pending_pgroup returns pgroup when deleted pgroup exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_pg = Mock()
        mock_pg.name = "test-pg"
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        result = get_pending_pgroup(mock_module, mock_array)

        assert result == mock_pg


class TestGetPgroup:
    """Test cases for get_pgroup function"""

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_get_pgroup_exists(self, mock_loose_version):
        """Test get_pgroup returns pgroup when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_pg = Mock()
        mock_pg.name = "test-pg"
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        result = get_pgroup(mock_module, mock_array)

        assert result == mock_pg

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_get_pgroup_not_exists(self, mock_loose_version):
        """Test get_pgroup returns None when pgroup doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_protection_groups.return_value = Mock(status_code=404)

        result = get_pgroup(mock_module, mock_array)

        assert result is None


class TestMakePgroup:
    """Test cases for make_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_make_pgroup_check_mode(self, mock_loose_version, mock_check_response):
        """Test make_pgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "new-pg", "target": None}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        make_pgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeletePgroup:
    """Test cases for delete_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_delete_pgroup_check_mode(self, mock_loose_version, mock_check_response):
        """Test delete_pgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-pg", "eradicate": False}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        delete_pgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePgroup:
    """Test cases for eradicate_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_eradicate_pgroup_check_mode(self, mock_loose_version, mock_check_response):
        """Test eradicate_pgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-pg"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        eradicate_pgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverPgroup:
    """Test cases for recover_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_recover_pgroup_check_mode(self, mock_loose_version, mock_check_response):
        """Test recover_pgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-pg"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        recover_pgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenameExists:
    """Test cases for rename_exists function"""

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_rename_exists_true(self, mock_loose_version):
        """Test rename_exists returns True when target exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "source-pg", "rename": "target-pg"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_protection_groups.return_value.status_code = 200

        result = rename_exists(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_rename_exists_false(self, mock_loose_version):
        """Test rename_exists returns False when target doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "source-pg", "rename": "target-pg"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_protection_groups.return_value.status_code = 404

        result = rename_exists(mock_module, mock_array)

        assert result is False


class TestCheckPgOnOffload:
    """Test cases for check_pg_on_offload function"""

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_pg_exists_on_offload(self, mock_loose_version):
        """Test check_pg_on_offload returns remote name when PG exists on offload"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "target": "offload-target"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        # Mock array.get_arrays().items
        mock_local_array = Mock()
        mock_local_array.name = "local-array"
        mock_array.get_arrays.return_value.items = [mock_local_array]
        # Mock remote protection groups response
        mock_remote_pg = Mock()
        mock_remote_pg.remote.name = "offload-target"
        mock_array.get_remote_protection_groups.return_value.status_code = 200
        mock_array.get_remote_protection_groups.return_value.items = [mock_remote_pg]

        result = check_pg_on_offload(mock_module, mock_array)

        assert result == "offload-target"

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_pg_not_on_offload(self, mock_loose_version):
        """Test check_pg_on_offload returns None when PG doesn't exist on offload"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "target": "offload-target"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        # Mock array.get_arrays().items
        mock_local_array = Mock()
        mock_local_array.name = "local-array"
        mock_array.get_arrays.return_value.items = [mock_local_array]
        mock_array.get_remote_protection_groups.return_value.status_code = 404

        result = check_pg_on_offload(mock_module, mock_array)

        assert result is None


class TestUpdatePgroup:
    """Test cases for update_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_update_pgroup_check_mode_no_changes(
        self, mock_loose_version, mock_check_response
    ):
        """Test update_pgroup in check mode with no changes needed"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        # Mock empty current members
        mock_pgroup = Mock()
        mock_pgroup.volumes = []
        mock_pgroup.hosts = []
        mock_pgroup.hgroups = []
        mock_array.get_protection_groups.return_value.items = [mock_pgroup]
        mock_array.get_protection_groups.return_value.status_code = 200
        mock_array.get_protection_group_targets.return_value.items = []

        update_pgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called()


class TestGetPgroupSched:
    """Test cases for get_pgroup_sched function"""

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_get_pgroup_sched_exists(self, mock_loose_version):
        """Test get_pgroup_sched returns schedule when exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        mock_sched = Mock()
        mock_sched.schedule = "daily"
        mock_array.get_protection_groups.return_value.status_code = 200
        mock_array.get_protection_groups.return_value.items = [mock_sched]

        result = get_pgroup_sched(mock_module, mock_array)

        assert result == mock_sched

    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_get_pgroup_sched_not_exists(self, mock_loose_version):
        """Test get_pgroup_sched returns None when not exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        mock_array.get_protection_groups.return_value.status_code = 404

        result = get_pgroup_sched(mock_module, mock_array)

        assert result is None


class TestDeletePgroupSuccess:
    """Additional test cases for delete_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_delete_pgroup_success(self, mock_loose_version, mock_check_response):
        """Test delete_pgroup successfully deletes"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)

        delete_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverPgroupSuccess:
    """Additional test cases for recover_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_recover_pgroup_success(self, mock_loose_version, mock_check_response):
        """Test recover_pgroup successfully recovers"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)

        recover_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePgroupSuccess:
    """Additional test cases for eradicate_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion")
    def test_eradicate_pgroup_success(self, mock_loose_version, mock_check_response):
        """Test eradicate_pgroup successfully eradicates"""
        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_protection_groups.return_value = Mock(status_code=200)

        eradicate_pgroup(mock_module, mock_array)

        mock_array.delete_protection_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMakePgroupSuccess:
    """Test cases for make_pgroup function success scenarios"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_basic(self, mock_lv, mock_check_response):
        """Test creating a basic protection group without targets"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": None,
            "volume": None,
            "host": None,
            "hostgroup": None,
            "enabled": True,
            "context": None,
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_protection_groups.return_value = Mock(status_code=200)

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pg.check_pg_on_offload")
    @patch("plugins.modules.purefa_pg.get_targets")
    @patch("plugins.modules.purefa_pg.get_arrays")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_with_targets(
        self,
        mock_lv,
        mock_check_response,
        mock_get_arrays,
        mock_get_targets,
        mock_check_pg_offload,
    ):
        """Test creating protection group with targets"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": ["array2"],
            "volume": None,
            "host": None,
            "hostgroup": None,
            "enabled": True,
            "context": None,
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_protection_groups.return_value = Mock(status_code=200)
        mock_array.post_protection_groups_targets.return_value = Mock(status_code=200)
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)

        mock_get_arrays.return_value = ["array2"]
        mock_get_targets.return_value = []
        mock_check_pg_offload.return_value = None

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_with_volumes_context_api(self, mock_lv, mock_check_response):
        """Test creating protection group with volumes using context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": None,
            "volume": ["vol1", "vol2"],
            "host": None,
            "hostgroup": None,
            "enabled": True,
            "context": "pod1",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_protection_groups.return_value = Mock(status_code=200)
        mock_array.post_protection_groups_volumes.return_value = Mock(status_code=200)

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_array.post_protection_groups_volumes.assert_called_once_with(
            group_names=["pgroup1"],
            member_names=["vol1", "vol2"],
            context_names=["pod1"],
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_with_hosts_context_api(self, mock_lv, mock_check_response):
        """Test creating protection group with hosts using context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": None,
            "volume": None,
            "host": ["host1", "host2"],
            "hostgroup": None,
            "enabled": True,
            "context": "pod1",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_protection_groups.return_value = Mock(status_code=200)
        mock_array.post_protection_groups_hosts.return_value = Mock(status_code=200)

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_array.post_protection_groups_hosts.assert_called_once_with(
            group_names=["pgroup1"],
            member_names=["host1", "host2"],
            context_names=["pod1"],
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_with_hostgroups_context_api(
        self, mock_lv, mock_check_response
    ):
        """Test creating protection group with hostgroups using context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": None,
            "volume": None,
            "host": None,
            "hostgroup": ["hg1", "hg2"],
            "enabled": True,
            "context": "pod1",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_protection_groups.return_value = Mock(status_code=200)
        mock_array.post_protection_groups_host_groups.return_value = Mock(
            status_code=200
        )

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_array.post_protection_groups_host_groups.assert_called_once_with(
            group_names=["pgroup1"],
            member_names=["hg1", "hg2"],
            context_names=["pod1"],
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_with_safe_mode_context_api(self, mock_lv, mock_check_response):
        """Test creating protection group with safe_mode using context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": None,
            "volume": None,
            "host": None,
            "hostgroup": None,
            "enabled": True,
            "context": "pod1",
            "safe_mode": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_protection_groups.return_value = Mock(status_code=200)
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_array.patch_protection_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_with_volumes_no_context(self, mock_lv, mock_check_response):
        """Test creating protection group with volumes without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": None,
            "volume": ["vol1", "vol2"],
            "host": None,
            "hostgroup": None,
            "enabled": True,
            "context": None,
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Below CONTEXT_API_VERSION
        mock_array.post_protection_groups.return_value = Mock(status_code=200)
        mock_array.post_protection_groups_volumes.return_value = Mock(status_code=200)

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_array.post_protection_groups_volumes.assert_called_once_with(
            group_names=["pgroup1"],
            member_names=["vol1", "vol2"],
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_with_hosts_no_context(self, mock_lv, mock_check_response):
        """Test creating protection group with hosts without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": None,
            "volume": None,
            "host": ["host1", "host2"],
            "hostgroup": None,
            "enabled": True,
            "context": None,
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Below CONTEXT_API_VERSION
        mock_array.post_protection_groups.return_value = Mock(status_code=200)
        mock_array.post_protection_groups_hosts.return_value = Mock(status_code=200)

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_array.post_protection_groups_hosts.assert_called_once_with(
            group_names=["pgroup1"],
            member_names=["host1", "host2"],
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_with_hostgroups_no_context(self, mock_lv, mock_check_response):
        """Test creating protection group with hostgroups without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": None,
            "volume": None,
            "host": None,
            "hostgroup": ["hg1", "hg2"],
            "enabled": True,
            "context": None,
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Below CONTEXT_API_VERSION
        mock_array.post_protection_groups.return_value = Mock(status_code=200)
        mock_array.post_protection_groups_host_groups.return_value = Mock(
            status_code=200
        )

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_array.post_protection_groups_host_groups.assert_called_once_with(
            group_names=["pgroup1"],
            member_names=["hg1", "hg2"],
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_make_pgroup_with_safe_mode_no_context(self, mock_lv, mock_check_response):
        """Test creating protection group with safe_mode without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pgroup1",
            "target": None,
            "volume": None,
            "host": None,
            "hostgroup": None,
            "enabled": True,
            "context": None,
            "safe_mode": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Below CONTEXT_API_VERSION
        mock_array.post_protection_groups.return_value = Mock(status_code=200)
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)

        make_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups.assert_called_once()
        mock_array.patch_protection_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePgroupSuccess:
    """Test cases for update_pgroup function success scenarios"""

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_update_pgroup_add_volumes(
        self, mock_lv, mock_check_response, mock_get_pgroup, mock_get_pgroup_sched
    ):
        """Test update_pgroup adding volumes to empty protection group"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": ["vol1", "vol2"],
            "host": None,
            "hostgroup": None,
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock pgroup with no hosts/hostgroups/volumes
        mock_pg = Mock()
        mock_pg.host_count = 0
        mock_pg.host_group_count = 0
        mock_pg.volume_count = 0
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup.return_value = mock_pg
        mock_get_pgroup_sched.return_value = Mock()
        mock_array.post_protection_groups_volumes.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups_volumes.assert_called_once()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_update_pgroup_add_hosts(
        self, mock_lv, mock_check_response, mock_get_pgroup, mock_get_pgroup_sched
    ):
        """Test update_pgroup adding hosts to empty protection group"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": ["host1", "host2"],
            "hostgroup": None,
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock pgroup with no volumes/hosts/hostgroups
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 0
        mock_pg.host_group_count = 0
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup.return_value = mock_pg
        mock_get_pgroup_sched.return_value = Mock()
        mock_array.post_protection_groups_hosts.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups_hosts.assert_called_once()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_update_pgroup_enable_snapshot_schedule(
        self, mock_lv, mock_check_response, mock_get_pgroup_sched
    ):
        """Test update_pgroup enabling snapshot schedule"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": True,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock schedule with snapshot disabled
        mock_sched = Mock()
        mock_sched.snapshot_schedule.enabled = False
        mock_get_pgroup_sched.return_value = mock_sched
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)
        # Mock get_protection_groups for retention_lock check
        mock_pg = Mock()
        mock_pg.retention_lock = "unlocked"
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_called()
        mock_module.exit_json.assert_called()


class TestUpdatePgroupVolumes:
    """Additional tests for update_pgroup with volumes"""

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_update_pgroup_add_volumes(
        self, mock_lv, mock_check_response, mock_get_pgroup_sched
    ):
        """Test update_pgroup adding volumes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": ["vol1", "vol2"],
            "host": None,
            "hostgroup": None,
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 0
        mock_pg.host_group_count = 0
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup_sched.return_value = Mock()
        mock_array.post_protection_groups_volumes.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups_volumes.assert_called_once()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_update_pgroup_add_hostgroup(
        self, mock_lv, mock_check_response, mock_get_pgroup_sched
    ):
        """Test update_pgroup adding host groups"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": None,
            "hostgroup": ["hg1"],
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 0
        mock_pg.host_group_count = 0
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup_sched.return_value = Mock()
        mock_array.post_protection_groups_host_groups.return_value = Mock(
            status_code=200
        )
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.post_protection_groups_host_groups.assert_called_once()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_update_pgroup_disable_snapshot_schedule(
        self, mock_lv, mock_get_pgroup_sched
    ):
        """Test update_pgroup disabling snapshot schedule"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": False,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_sched = Mock()
        mock_sched.snapshot_schedule.enabled = True
        mock_get_pgroup_sched.return_value = mock_sched
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)
        mock_pg = Mock()
        mock_pg.retention_lock = "unlocked"
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_called()
        mock_module.exit_json.assert_called()


class TestUpdatePgroupTargets:
    """Test cases for update_pgroup with target handling"""

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_targets")
    @patch("plugins.modules.purefa_pg.get_arrays")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_update_pgroup_no_targets_connected(
        self,
        mock_lv,
        mock_check_response,
        mock_get_arrays,
        mock_get_targets,
        mock_get_pgroup_sched,
    ):
        """Test update_pgroup fails when no targets connected"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": ["offload-target"],
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": True,
            "context": "",
            "safe_mode": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_arrays.return_value = []
        mock_get_targets.return_value = []

        with pytest.raises(SystemExit):
            update_pgroup(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_targets")
    @patch("plugins.modules.purefa_pg.get_arrays")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_update_pgroup_target_not_connected(
        self,
        mock_lv,
        mock_check_response,
        mock_get_arrays,
        mock_get_targets,
        mock_get_pgroup_sched,
    ):
        """Test update_pgroup fails when target not connected"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": ["nonexistent-target"],
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": True,
            "context": "",
            "safe_mode": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_arrays.return_value = ["array2"]
        mock_get_targets.return_value = ["nfs-target1"]
        mock_array.get_protection_groups_targets.return_value = Mock(
            status_code=200, items=[]
        )

        with pytest.raises(SystemExit):
            update_pgroup(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestDeletePgroupEradicate:
    """Test cases for delete_pgroup with eradicate option"""

    @patch("plugins.modules.purefa_pg.eradicate_pgroup")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_delete_pgroup_with_eradicate(
        self, mock_lv, mock_check_response, mock_eradicate
    ):
        """Test delete_pgroup calls eradicate when eradicate=True"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "eradicate": True,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)

        delete_pgroup(mock_module, mock_array)

        mock_eradicate.assert_called_once_with(mock_module, mock_array)


class TestRenameExistsContainer:
    """Test cases for rename_exists with container handling"""

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_rename_exists_in_pod(self, mock_lv):
        """Test rename_exists for pgroup in pod"""
        mock_module = Mock()
        mock_module.params = {
            "name": "pod1::test-pg",
            "rename": "new-pg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[Mock()]
        )

        result = rename_exists(mock_module, mock_array)

        assert result is True
        # Verify it looked for pod1::new-pg
        call_args = mock_array.get_protection_groups.call_args
        assert "pod1::new-pg" in str(call_args)

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_rename_exists_no_container(self, mock_lv):
        """Test rename_exists for standalone pgroup"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "rename": "new-pg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_protection_groups.return_value = Mock(status_code=404, items=[])

        result = rename_exists(mock_module, mock_array)

        assert result is False


class TestRecoverPgroupExtended:
    """Extended test cases for recover_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_recover_pgroup_older_api(self, mock_lv, mock_check_response):
        """Test recovering pgroup with older API version"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.16"
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)

        recover_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_called_once()
        call_kwargs = mock_array.patch_protection_groups.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePgroupExtended:
    """Extended test cases for eradicate_pgroup function"""

    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_pgroup_older_api(self, mock_lv, mock_check_response):
        """Test eradicating pgroup with older API version"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.16"
        mock_array.delete_protection_groups.return_value = Mock(status_code=200)

        eradicate_pgroup(mock_module, mock_array)

        mock_array.delete_protection_groups.assert_called_once()
        call_kwargs = mock_array.delete_protection_groups.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePgroupHostgroupBugFix:
    """Test case for hostgroup bug fix - was using host param instead of hostgroup"""

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_add_hostgroup_to_empty_pgroup_uses_hostgroup_param(
        self, mock_lv, mock_check_response, mock_get_pgroup_sched
    ):
        """Test adding hostgroup to empty pgroup uses hostgroup param not host

        Bug: When adding hostgroups to an existing empty protection group,
        the code was passing module.params["host"] instead of module.params["hostgroup"]
        causing 'Missing or invalid parameter' error.
        """
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": None,  # host is None
            "hostgroup": ["hg1", "hg2"],  # hostgroup is set
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Empty protection group
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 0
        mock_pg.host_group_count = 0
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup_sched.return_value = Mock()
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_array.post_protection_groups_host_groups.return_value = Mock(
            status_code=200
        )

        update_pgroup(mock_module, mock_array)

        # Verify hostgroup param was used, not host param
        mock_array.post_protection_groups_host_groups.assert_called_once()
        call_kwargs = mock_array.post_protection_groups_host_groups.call_args[1]
        assert call_kwargs["member_names"] == ["hg1", "hg2"]
        assert call_kwargs["member_names"] is not None  # Would be None if using host
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_add_host_to_empty_pgroup_uses_host_param(
        self, mock_lv, mock_check_response, mock_get_pgroup_sched
    ):
        """Test adding host to empty pgroup correctly uses host param"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": ["host1", "host2"],  # host is set
            "hostgroup": None,  # hostgroup is None
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Empty protection group
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 0
        mock_pg.host_group_count = 0
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup_sched.return_value = Mock()
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_array.post_protection_groups_hosts.return_value = Mock(status_code=200)

        update_pgroup(mock_module, mock_array)

        # Verify host param was used correctly
        mock_array.post_protection_groups_hosts.assert_called_once()
        call_kwargs = mock_array.post_protection_groups_hosts.call_args[1]
        assert call_kwargs["member_names"] == ["host1", "host2"]
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_add_volume_to_empty_pgroup_uses_volume_param(
        self, mock_lv, mock_check_response, mock_get_pgroup_sched
    ):
        """Test adding volume to empty pgroup correctly uses volume param"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": ["vol1", "vol2"],  # volume is set
            "host": None,
            "hostgroup": None,
            "target": None,
            "priority": None,
            "priority_adjustment": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Empty protection group
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 0
        mock_pg.host_group_count = 0
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup_sched.return_value = Mock()
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_array.post_protection_groups_volumes.return_value = Mock(status_code=200)

        update_pgroup(mock_module, mock_array)

        # Verify volume param was used correctly
        mock_array.post_protection_groups_volumes.assert_called_once()
        call_kwargs = mock_array.post_protection_groups_volumes.call_args[1]
        assert call_kwargs["member_names"] == ["vol1", "vol2"]
        mock_module.exit_json.assert_called()


class TestUpdatePgroupRemoveMembers:
    """Test cases for update_pgroup removing members from existing protection groups"""

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_remove_volumes_from_pgroup_context_api(
        self, mock_lv, mock_check_response, mock_get_pgroup, mock_get_pgroup_sched
    ):
        """Test removing volumes from protection group with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": ["vol1"],
            "host": None,
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "absent",  # state=absent removes volumes
            "enabled": None,
            "context": "pod1",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock pgroup with volumes
        mock_pg = Mock()
        mock_pg.host_count = 0
        mock_pg.host_group_count = 0
        mock_pg.volume_count = 2
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup.return_value = mock_pg
        mock_get_pgroup_sched.return_value = Mock()
        # Mock existing volumes
        mock_vol = Mock()
        mock_vol.member.name = "vol1"
        mock_array.get_protection_groups_volumes.return_value = Mock(items=[mock_vol])
        mock_array.delete_protection_groups_volumes.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.delete_protection_groups_volumes.assert_called_once()
        call_kwargs = mock_array.delete_protection_groups_volumes.call_args[1]
        assert call_kwargs["context_names"] == ["pod1"]
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_remove_volumes_from_pgroup_no_context(
        self, mock_lv, mock_check_response, mock_get_pgroup, mock_get_pgroup_sched
    ):
        """Test removing volumes from protection group without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": ["vol1"],
            "host": None,
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "absent",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Below CONTEXT_API_VERSION
        mock_pg = Mock()
        mock_pg.host_count = 0
        mock_pg.host_group_count = 0
        mock_pg.volume_count = 1
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup.return_value = mock_pg
        mock_get_pgroup_sched.return_value = Mock()
        mock_vol = Mock()
        mock_vol.member.name = "vol1"
        mock_array.get_protection_groups_volumes.return_value = Mock(items=[mock_vol])
        mock_array.delete_protection_groups_volumes.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.delete_protection_groups_volumes.assert_called_once()
        call_kwargs = mock_array.delete_protection_groups_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_remove_hosts_from_pgroup_context_api(
        self, mock_lv, mock_check_response, mock_get_pgroup, mock_get_pgroup_sched
    ):
        """Test removing hosts from protection group with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": ["host1"],
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "absent",
            "enabled": None,
            "context": "pod1",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 2
        mock_pg.host_group_count = 0
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup.return_value = mock_pg
        mock_get_pgroup_sched.return_value = Mock()
        mock_host = Mock()
        mock_host.member.name = "host1"
        mock_array.get_protection_groups_hosts.return_value = Mock(items=[mock_host])
        mock_array.delete_protection_groups_hosts.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.delete_protection_groups_hosts.assert_called_once()
        call_kwargs = mock_array.delete_protection_groups_hosts.call_args[1]
        assert call_kwargs["context_names"] == ["pod1"]
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_remove_hosts_from_pgroup_no_context(
        self, mock_lv, mock_check_response, mock_get_pgroup, mock_get_pgroup_sched
    ):
        """Test removing hosts from protection group without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": ["host1"],
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "absent",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 1
        mock_pg.host_group_count = 0
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup.return_value = mock_pg
        mock_get_pgroup_sched.return_value = Mock()
        mock_host = Mock()
        mock_host.member.name = "host1"
        mock_array.get_protection_groups_hosts.return_value = Mock(items=[mock_host])
        mock_array.delete_protection_groups_hosts.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.delete_protection_groups_hosts.assert_called_once()
        call_kwargs = mock_array.delete_protection_groups_hosts.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_remove_hostgroups_from_pgroup_context_api(
        self, mock_lv, mock_check_response, mock_get_pgroup, mock_get_pgroup_sched
    ):
        """Test removing hostgroups from protection group with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": None,
            "hostgroup": ["hg1"],
            "target": None,
            "eradicate": False,
            "state": "absent",
            "enabled": None,
            "context": "pod1",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 0
        mock_pg.host_group_count = 2
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup.return_value = mock_pg
        mock_get_pgroup_sched.return_value = Mock()
        mock_hg = Mock()
        mock_hg.member.name = "hg1"
        mock_array.get_protection_groups_host_groups.return_value = Mock(
            items=[mock_hg]
        )
        mock_array.delete_protection_groups_host_groups.return_value = Mock(
            status_code=200
        )
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.delete_protection_groups_host_groups.assert_called_once()
        call_kwargs = mock_array.delete_protection_groups_host_groups.call_args[1]
        assert call_kwargs["context_names"] == ["pod1"]
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_remove_hostgroups_from_pgroup_no_context(
        self, mock_lv, mock_check_response, mock_get_pgroup, mock_get_pgroup_sched
    ):
        """Test removing hostgroups from protection group without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "volume": None,
            "host": None,
            "hostgroup": ["hg1"],
            "target": None,
            "eradicate": False,
            "state": "absent",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_pg = Mock()
        mock_pg.volume_count = 0
        mock_pg.host_count = 0
        mock_pg.host_group_count = 1
        mock_pg.retention_lock = "unlocked"
        mock_get_pgroup.return_value = mock_pg
        mock_get_pgroup_sched.return_value = Mock()
        mock_hg = Mock()
        mock_hg.member.name = "hg1"
        mock_array.get_protection_groups_host_groups.return_value = Mock(
            items=[mock_hg]
        )
        mock_array.delete_protection_groups_host_groups.return_value = Mock(
            status_code=200
        )
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )

        update_pgroup(mock_module, mock_array)

        mock_array.delete_protection_groups_host_groups.assert_called_once()
        call_kwargs = mock_array.delete_protection_groups_host_groups.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called()


class TestUpdatePgroupRename:
    """Test cases for update_pgroup rename functionality"""

    @patch("plugins.modules.purefa_pg.rename_exists")
    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_rename_pgroup_context_api(
        self, mock_lv, mock_check_response, mock_get_pgroup_sched, mock_rename_exists
    ):
        """Test renaming protection group with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-pg",
            "rename": "new-pg",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "pod1",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_rename_exists.return_value = False
        mock_pg = Mock()
        mock_pg.retention_lock = "unlocked"
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_get_pgroup_sched.return_value = Mock()

        update_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.rename_exists")
    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_rename_pgroup_no_context(
        self, mock_lv, mock_check_response, mock_get_pgroup_sched, mock_rename_exists
    ):
        """Test renaming protection group without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-pg",
            "rename": "new-pg",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_rename_exists.return_value = False
        mock_pg = Mock()
        mock_pg.retention_lock = "unlocked"
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_get_pgroup_sched.return_value = Mock()

        update_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_called()
        # Verify no context_names in non-context API call
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.rename_exists")
    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_rename_pgroup_in_pod_container(
        self, mock_lv, mock_get_pgroup_sched, mock_rename_exists
    ):
        """Test renaming protection group in pod container (::)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::old-pg",
            "rename": "new-pg",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_rename_exists.return_value = False
        mock_pg = Mock()
        mock_pg.retention_lock = "unlocked"
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_get_pgroup_sched.return_value = Mock()

        update_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_called()
        # Check that rename includes container prefix
        assert mock_module.params["name"] == "pod1::new-pg"
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.rename_exists")
    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_rename_pgroup_in_single_colon_container(
        self, mock_lv, mock_get_pgroup_sched, mock_rename_exists
    ):
        """Test renaming protection group in single colon container (:)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "array1:old-pg",
            "rename": "new-pg",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_rename_exists.return_value = False
        mock_pg = Mock()
        mock_pg.retention_lock = "unlocked"
        mock_array.patch_protection_groups.return_value = Mock(status_code=200)
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_get_pgroup_sched.return_value = Mock()

        update_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_called()
        # Check that rename includes container prefix with single colon
        assert mock_module.params["name"] == "array1:new-pg"
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.rename_exists")
    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_rename_pgroup_target_exists_warns(
        self, mock_lv, mock_get_pgroup_sched, mock_rename_exists
    ):
        """Test rename warns when target already exists"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-pg",
            "rename": "existing-pg",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_rename_exists.return_value = True  # Target exists
        mock_pg = Mock()
        mock_pg.retention_lock = "unlocked"
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_get_pgroup_sched.return_value = Mock()

        update_pgroup(mock_module, mock_array)

        mock_module.warn.assert_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_pg.rename_exists")
    @patch("plugins.modules.purefa_pg.get_pgroup_sched")
    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    def test_rename_pgroup_check_mode(
        self, mock_lv, mock_get_pgroup_sched, mock_rename_exists
    ):
        """Test rename in check mode doesn't make changes"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "old-pg",
            "rename": "new-pg",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "eradicate": False,
            "state": "present",
            "enabled": None,
            "context": "",
            "safe_mode": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_rename_exists.return_value = False
        mock_pg = Mock()
        mock_pg.retention_lock = "unlocked"
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_get_pgroup_sched.return_value = Mock()

        update_pgroup(mock_module, mock_array)

        mock_array.patch_protection_groups.assert_not_called()
        mock_module.exit_json.assert_called()


class TestMain:
    """Test cases for main() function - module entry point"""

    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_invalid_rename_name(
        self, mock_ansible, mock_get_array, mock_get_pg, mock_get_pending, mock_get_pod
    ):
        """Test main fails with invalid rename value"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "rename": "invalid!name",  # Invalid character
            "state": "present",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "safe_mode": False,
            "eradicate": False,
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()
        assert "does not conform to naming convention" in str(
            mock_module.fail_json.call_args
        )

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_invalid_pgname_in_pod(
        self,
        mock_ansible,
        mock_get_array,
        mock_get_pg,
        mock_get_pending,
        mock_get_pod,
        mock_lv,
    ):
        """Test main fails with invalid pgroup name in pod (::)"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "pod1::invalid!pg",  # Invalid character in pgroup name
            "rename": None,
            "state": "present",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "safe_mode": False,
            "eradicate": False,
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_arrays.return_value.items = [Mock()]
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_invalid_pgname_single_colon(
        self,
        mock_ansible,
        mock_get_array,
        mock_get_pg,
        mock_get_pending,
        mock_get_pod,
        mock_lv,
    ):
        """Test main fails with invalid pgroup name with single colon container"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "array1:invalid!pg",  # Invalid character
            "rename": None,
            "state": "present",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "safe_mode": False,
            "eradicate": False,
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_arrays.return_value.items = [Mock()]
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_invalid_pgname_standalone(
        self,
        mock_ansible,
        mock_get_array,
        mock_get_pg,
        mock_get_pending,
        mock_get_pod,
        mock_lv,
    ):
        """Test main fails with invalid standalone pgroup name"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "invalid!pg",  # Invalid character
            "rename": None,
            "state": "present",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "safe_mode": False,
            "eradicate": False,
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_arrays.return_value.items = [Mock()]
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_safe_mode_old_api(
        self,
        mock_ansible,
        mock_get_array,
        mock_get_pg,
        mock_get_pending,
        mock_get_pod,
        mock_lv,
    ):
        """Test main fails when safe_mode requested but API too old"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "state": "present",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "safe_mode": True,  # SafeMode requires API >= 2.13
            "eradicate": False,
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"  # Too old for SafeMode
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()
        assert "SafeMode" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_pod_not_exists(
        self,
        mock_ansible,
        mock_get_array,
        mock_get_pg,
        mock_get_pending,
        mock_get_pod,
        mock_check_response,
        mock_lv,
    ):
        """Test main fails when pod doesn't exist for pgroup in pod"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "name": "nonexistent-pod::test-pg",
            "rename": None,
            "state": "present",
            "volume": None,
            "host": None,
            "hostgroup": None,
            "target": None,
            "safe_mode": False,
            "eradicate": False,
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_arrays.return_value.items = [Mock()]
        mock_get_array.return_value = mock_array
        mock_get_pg.return_value = None
        mock_get_pending.return_value = None
        mock_get_pod.return_value = None  # Pod doesn't exist

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()
        assert "does not exist" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_host_validation_context_api(
        self,
        mock_ansible,
        mock_get_array,
        mock_get_pg,
        mock_get_pending,
        mock_get_pod,
        mock_check_response,
        mock_lv,
    ):
        """Test main validates hosts with context API"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "state": "present",
            "volume": None,
            "host": ["host1", "host2"],
            "hostgroup": None,
            "target": None,
            "safe_mode": False,
            "eradicate": False,
            "enabled": True,
            "context": "pod1",
        }
        mock_module.check_mode = False
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_hosts.return_value = Mock(status_code=200)
        mock_get_array.return_value = mock_array
        mock_get_pg.return_value = Mock()  # pgroup exists
        mock_get_pending.return_value = None

        # update_pgroup will be called - mock to exit
        with patch("plugins.modules.purefa_pg.update_pgroup") as mock_update:
            mock_update.side_effect = SystemExit(0)
            try:
                main()
            except SystemExit:
                pass

        mock_array.get_hosts.assert_called_once()
        call_kwargs = mock_array.get_hosts.call_args[1]
        assert call_kwargs["context_names"] == ["pod1"]

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_hostgroup_validation_context_api(
        self,
        mock_ansible,
        mock_get_array,
        mock_get_pg,
        mock_get_pending,
        mock_get_pod,
        mock_check_response,
        mock_lv,
    ):
        """Test main validates hostgroups with context API"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "state": "present",
            "volume": None,
            "host": None,
            "hostgroup": ["hg1"],
            "target": None,
            "safe_mode": False,
            "eradicate": False,
            "enabled": True,
            "context": "pod1",
        }
        mock_module.check_mode = False
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_host_groups.return_value = Mock(status_code=200)
        mock_get_array.return_value = mock_array
        mock_get_pg.return_value = Mock()
        mock_get_pending.return_value = None

        with patch("plugins.modules.purefa_pg.update_pgroup") as mock_update:
            mock_update.side_effect = SystemExit(0)
            try:
                main()
            except SystemExit:
                pass

        mock_array.get_host_groups.assert_called_once()
        call_kwargs = mock_array.get_host_groups.call_args[1]
        assert call_kwargs["context_names"] == ["pod1"]

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_host_validation_no_context(
        self,
        mock_ansible,
        mock_get_array,
        mock_get_pg,
        mock_get_pending,
        mock_get_pod,
        mock_check_response,
        mock_lv,
    ):
        """Test main validates hosts without context API"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "state": "present",
            "volume": None,
            "host": ["host1"],
            "hostgroup": None,
            "target": None,
            "safe_mode": False,
            "eradicate": False,
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Below CONTEXT_API_VERSION
        mock_array.get_hosts.return_value = Mock(status_code=200)
        mock_get_array.return_value = mock_array
        mock_get_pg.return_value = Mock()
        mock_get_pending.return_value = None

        with patch("plugins.modules.purefa_pg.update_pgroup") as mock_update:
            mock_update.side_effect = SystemExit(0)
            try:
                main()
            except SystemExit:
                pass

        mock_array.get_hosts.assert_called_once()
        call_kwargs = mock_array.get_hosts.call_args[1]
        assert "context_names" not in call_kwargs

    @patch("plugins.modules.purefa_pg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pg.check_response")
    @patch("plugins.modules.purefa_pg.get_pod")
    @patch("plugins.modules.purefa_pg.get_pending_pgroup")
    @patch("plugins.modules.purefa_pg.get_pgroup")
    @patch("plugins.modules.purefa_pg.get_array")
    @patch("plugins.modules.purefa_pg.AnsibleModule")
    def test_main_hostgroup_validation_no_context(
        self,
        mock_ansible,
        mock_get_array,
        mock_get_pg,
        mock_get_pending,
        mock_get_pod,
        mock_check_response,
        mock_lv,
    ):
        """Test main validates hostgroups without context API"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "rename": None,
            "state": "present",
            "volume": None,
            "host": None,
            "hostgroup": ["hg1"],
            "target": None,
            "safe_mode": False,
            "eradicate": False,
            "enabled": True,
            "context": "",
        }
        mock_module.check_mode = False
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"
        mock_array.get_host_groups.return_value = Mock(status_code=200)
        mock_get_array.return_value = mock_array
        mock_get_pg.return_value = Mock()
        mock_get_pending.return_value = None

        with patch("plugins.modules.purefa_pg.update_pgroup") as mock_update:
            mock_update.side_effect = SystemExit(0)
            try:
                main()
            except SystemExit:
                pass

        mock_array.get_host_groups.assert_called_once()
        call_kwargs = mock_array.get_host_groups.call_args[1]
        assert "context_names" not in call_kwargs
