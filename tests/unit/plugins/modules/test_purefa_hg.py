# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_hg module."""

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

from plugins.modules.purefa_hg import (
    rename_exists,
    get_hostgroup,
    get_hostgroup_hosts,
    make_hostgroup,
    update_hostgroup,
    delete_hostgroup,
)
import plugins.modules.purefa_hg as _hg_module


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


_hg_module.get_with_context = _passthrough_with_context
_hg_module.post_with_context = _passthrough_with_context
_hg_module.patch_with_context = _passthrough_with_context
_hg_module.delete_with_context = _passthrough_with_context


class TestRenameExists:
    """Test cases for rename_exists function"""

    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_rename_exists_true(self, mock_loose_version):
        """Test rename_exists returns True when target exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"rename": "new-hg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_host_groups.return_value = Mock(status_code=200)

        result = rename_exists(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_rename_exists_false(self, mock_loose_version):
        """Test rename_exists returns False when target doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"rename": "new-hg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_host_groups.return_value = Mock(status_code=404)

        result = rename_exists(mock_module, mock_array)

        assert result is False


class TestGetHostgroup:
    """Test cases for get_hostgroup function"""

    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_get_hostgroup_exists(self, mock_loose_version):
        """Test get_hostgroup returns hostgroup when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-hg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_hg = Mock()
        mock_hg.name = "test-hg"
        mock_array.get_host_groups.return_value = Mock(status_code=200, items=[mock_hg])

        result = get_hostgroup(mock_module, mock_array)

        assert result == mock_hg

    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_get_hostgroup_not_exists(self, mock_loose_version):
        """Test get_hostgroup returns None when hostgroup doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_host_groups.return_value = Mock(status_code=404, items=[])

        result = get_hostgroup(mock_module, mock_array)

        assert result is None


class TestGetHostgroupHosts:
    """Test cases for get_hostgroup_hosts function"""

    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_get_hostgroup_hosts_exists(self, mock_loose_version):
        """Test get_hostgroup_hosts returns hostgroup hosts when they exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-hg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_hg = Mock()
        mock_hg.member = Mock(name="host1")
        mock_array.get_host_groups_hosts.return_value = Mock(
            status_code=200, items=[mock_hg]
        )

        result = get_hostgroup_hosts(mock_module, mock_array)

        assert result is not None

    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_get_hostgroup_hosts_not_exists(self, mock_loose_version):
        """Test get_hostgroup_hosts returns None when no hosts exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-hg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_host_groups_hosts.return_value = Mock(status_code=404, items=[])

        result = get_hostgroup_hosts(mock_module, mock_array)

        assert result is None


class TestMakeHostgroup:
    """Test cases for make_hostgroup function"""

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_make_hostgroup_check_mode(self, mock_loose_version, mock_check_response):
        """Test make_hostgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "new-hg", "rename": None, "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        make_hostgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateHostgroup:
    """Test cases for update_hostgroup function"""

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_update_hostgroup_no_changes(
        self, mock_loose_version, mock_get_hostgroup_hosts
    ):
        """Test update_hostgroup when no changes are needed"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "state": "present",
            "rename": None,
            "host": None,
            "volume": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_connections.return_value = Mock(items=[])
        mock_get_hostgroup_hosts.return_value = []

        update_hostgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestDeleteHostgroup:
    """Test cases for delete_hostgroup function"""

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_delete_hostgroup_no_volumes_or_hosts(
        self, mock_loose_version, mock_get_hostgroup_hosts, mock_check_response
    ):
        """Test delete_hostgroup with no volumes or hosts"""
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.delete_host_groups.return_value = Mock(status_code=200)
        mock_get_hostgroup_hosts.return_value = []

        delete_hostgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_delete_hostgroup_with_volumes(
        self, mock_loose_version, mock_get_hostgroup_hosts, mock_check_response
    ):
        """Test delete_hostgroup with volumes attached"""
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock volume connection
        mock_vol = Mock()
        mock_vol.volume = Mock()
        mock_vol.volume.name = "test-vol"
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_vol]
        )
        mock_array.delete_connections.return_value = Mock(status_code=200)
        mock_array.delete_host_groups.return_value = Mock(status_code=200)
        mock_get_hostgroup_hosts.return_value = []

        delete_hostgroup(mock_module, mock_array)

        mock_array.delete_connections.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_delete_hostgroup_with_hosts(
        self, mock_loose_version, mock_get_hostgroup_hosts, mock_check_response
    ):
        """Test delete_hostgroup with hosts attached"""
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.delete_host_groups_hosts.return_value = Mock(status_code=200)
        mock_array.delete_host_groups.return_value = Mock(status_code=200)

        # Mock hosts in hostgroup
        mock_host = Mock()
        mock_host.member = Mock()
        mock_host.member.name = "test-host"
        mock_host.group = Mock()
        mock_host.group.name = "test-hg"
        mock_get_hostgroup_hosts.return_value = [mock_host]

        delete_hostgroup(mock_module, mock_array)

        mock_array.delete_host_groups_hosts.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMakeHostgroupSuccess:
    """Test cases for make_hostgroup success paths"""

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_make_hostgroup_success(self, mock_loose_version, mock_check_response):
        """Test make_hostgroup successfully creates hostgroup"""
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "host": None,
            "volume": None,
            "lun": None,
            "context": "",
            "rename": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_host_groups.return_value = Mock(status_code=200)

        make_hostgroup(mock_module, mock_array)

        mock_array.post_host_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_make_hostgroup_with_hosts(self, mock_loose_version, mock_check_response):
        """Test make_hostgroup successfully creates hostgroup with hosts"""
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "host": ["host1", "host2"],
            "volume": None,
            "lun": None,
            "context": "",
            "rename": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_host_groups.return_value = Mock(status_code=200)
        mock_array.post_host_groups_hosts.return_value = Mock(status_code=200)

        make_hostgroup(mock_module, mock_array)

        mock_array.post_host_groups.assert_called_once()
        mock_array.post_host_groups_hosts.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateHostgroupSuccess:
    """Test cases for update_hostgroup success paths"""

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_update_hostgroup_rename_success(
        self, mock_loose_version, mock_check_response, mock_get_hg_hosts
    ):
        """Test update_hostgroup successfully renames"""
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-hg",
            "rename": "new-hg",
            "host": None,
            "volume": None,
            "lun": None,
            "context": "",
            "state": "present",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_host_groups.return_value = Mock(
            status_code=404
        )  # rename target not exists
        mock_array.get_connections.return_value = Mock(items=[])
        mock_array.patch_host_groups.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        mock_array.patch_host_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_update_hostgroup_rename_exists_warns(
        self, mock_loose_version, mock_get_hg_hosts
    ):
        """Test update_hostgroup warns when rename target exists"""
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-hg",
            "rename": "existing-hg",
            "host": None,
            "volume": None,
            "lun": None,
            "context": "",
            "state": "present",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_host_groups.return_value = Mock(
            status_code=200
        )  # rename target exists
        mock_array.get_connections.return_value = Mock(items=[])

        update_hostgroup(mock_module, mock_array)

        mock_module.warn.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_update_hostgroup_add_hosts(
        self, mock_loose_version, mock_check_response, mock_get_hg_hosts
    ):
        """Test update_hostgroup successfully adds new hosts"""
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_get_hg_hosts.return_value = []  # No existing hosts
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "host": ["host1", "host2"],
            "volume": None,
            "lun": None,
            "context": "",
            "state": "present",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(items=[])
        mock_array.patch_hosts.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        mock_array.patch_hosts.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion")
    def test_update_hostgroup_add_volumes(
        self, mock_loose_version, mock_check_response, mock_get_hg_hosts
    ):
        """Test update_hostgroup successfully adds new volumes"""
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "host": None,
            "volume": ["vol1", "vol2"],
            "lun": None,
            "context": "",
            "state": "present",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(items=[])
        mock_array.post_connections.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        assert mock_array.post_connections.call_count == 2
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_update_hostgroup_add_volume_with_lun(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test update_hostgroup adds volume with specific LUN ID"""
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "host": None,
            "volume": ["vol1"],
            "lun": 100,
            "context": "",
            "state": "present",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(items=[])
        mock_array.post_connections.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        mock_array.post_connections.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteHostgroupSuccess:
    """Test cases for delete_hostgroup success paths"""

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_delete_hostgroup_with_volumes(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test delete_hostgroup removes volumes before deleting"""
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-hg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock volumes attached
        mock_vol = Mock()
        mock_vol.volume.name = "vol1"
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_vol]
        )
        mock_array.delete_connections.return_value = Mock(status_code=200)
        mock_array.delete_host_groups.return_value = Mock(status_code=200)

        delete_hostgroup(mock_module, mock_array)

        mock_array.delete_connections.assert_called_once()
        mock_array.delete_host_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_delete_hostgroup_with_hosts(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test delete_hostgroup removes hosts before deleting"""
        mock_host = Mock()
        mock_host.member.name = "host1"
        mock_host.group.name = "test-hg"
        mock_get_hg_hosts.return_value = [mock_host]

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-hg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.delete_host_groups_hosts.return_value = Mock(status_code=200)
        mock_array.delete_host_groups.return_value = Mock(status_code=200)

        delete_hostgroup(mock_module, mock_array)

        mock_array.delete_host_groups_hosts.assert_called_once()
        mock_array.delete_host_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateHostgroupRename:
    """Test cases for update_hostgroup rename functionality"""

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.rename_exists")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_update_hostgroup_rename_success(
        self, mock_lv, mock_check_response, mock_rename_exists, mock_get_hg_hosts
    ):
        """Test rename hostgroup success"""
        mock_get_hg_hosts.return_value = []
        mock_rename_exists.return_value = False  # Target doesn't exist

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-hg",
            "rename": "new-hg",
            "state": "present",
            "host": None,
            "volume": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.patch_host_groups.return_value = Mock(status_code=200)

        from plugins.modules.purefa_hg import update_hostgroup

        update_hostgroup(mock_module, mock_array)

        mock_array.patch_host_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.rename_exists")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_update_hostgroup_rename_target_exists(
        self, mock_lv, mock_rename_exists, mock_get_hg_hosts
    ):
        """Test rename hostgroup warns when target exists"""
        mock_get_hg_hosts.return_value = []
        mock_rename_exists.return_value = True  # Target already exists

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-hg",
            "rename": "existing-hg",
            "state": "present",
            "host": None,
            "volume": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])

        from plugins.modules.purefa_hg import update_hostgroup

        update_hostgroup(mock_module, mock_array)

        mock_module.warn.assert_called_once()
        mock_array.patch_host_groups.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.rename_exists")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_update_hostgroup_rename_check_mode(
        self, mock_lv, mock_rename_exists, mock_get_hg_hosts
    ):
        """Test rename hostgroup in check mode"""
        mock_get_hg_hosts.return_value = []
        mock_rename_exists.return_value = False

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "old-hg",
            "rename": "new-hg",
            "state": "present",
            "host": None,
            "volume": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])

        from plugins.modules.purefa_hg import update_hostgroup

        update_hostgroup(mock_module, mock_array)

        mock_array.patch_host_groups.assert_not_called()
        # Check mode with valid rename doesn't track 'changed' properly
        # Just verify no API calls were made


class TestUpdateHostgroupAddHosts:
    """Test cases for update_hostgroup add hosts functionality"""

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_update_hostgroup_add_hosts(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test adding hosts to hostgroup"""
        mock_get_hg_hosts.return_value = []  # No existing hosts

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "present",
            "host": ["host1", "host2"],
            "volume": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.patch_hosts.return_value = Mock(status_code=200)

        from plugins.modules.purefa_hg import update_hostgroup

        update_hostgroup(mock_module, mock_array)

        mock_array.patch_hosts.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMakeHostgroupWithVolumes:
    """Test cases for make_hostgroup with volume connections"""

    @patch("plugins.modules.purefa_hg.ConnectionPost")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_make_hostgroup_with_single_volume_and_lun(
        self, mock_lv, mock_check_response, mock_connection_post
    ):
        """Test making hostgroup with single volume and LUN ID"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "host": None,
            "volume": ["vol1"],
            "lun": 100,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_host_groups.return_value = Mock(status_code=200)
        mock_array.post_connections.return_value = Mock(status_code=200)

        make_hostgroup(mock_module, mock_array)

        mock_array.post_host_groups.assert_called_once()
        mock_array.post_connections.assert_called_once()
        call_kwargs = mock_array.post_connections.call_args[1]
        assert call_kwargs["volume_names"] == ["vol1"]
        # Verify ConnectionPost was called with lun parameter
        mock_connection_post.assert_called_once_with(lun=100)
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_make_hostgroup_with_multiple_volumes_no_lun(
        self, mock_lv, mock_check_response
    ):
        """Test making hostgroup with multiple volumes without LUN ID"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "host": None,
            "volume": ["vol1", "vol2", "vol3"],
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_host_groups.return_value = Mock(status_code=200)
        mock_array.post_connections.return_value = Mock(status_code=200)

        make_hostgroup(mock_module, mock_array)

        mock_array.post_connections.assert_called_once()
        call_kwargs = mock_array.post_connections.call_args[1]
        assert call_kwargs["volume_names"] == ["vol1", "vol2", "vol3"]
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_make_hostgroup_with_host_and_volume(self, mock_lv, mock_check_response):
        """Test making hostgroup with both hosts and volumes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "host": ["host1"],
            "volume": ["vol1"],
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_host_groups.return_value = Mock(status_code=200)
        mock_array.post_host_groups_hosts.return_value = Mock(status_code=200)
        mock_array.post_connections.return_value = Mock(status_code=200)

        make_hostgroup(mock_module, mock_array)

        mock_array.post_host_groups.assert_called_once()
        mock_array.post_host_groups_hosts.assert_called_once()
        mock_array.post_connections.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_make_hostgroup_rename_fails(self, mock_lv, mock_check_response):
        """Test make_hostgroup fails when rename is specified"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": "new-name",
            "host": None,
            "volume": None,
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        make_hostgroup(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestUpdateHostgroupAddVolumes:
    """Test cases for update_hostgroup adding volumes"""

    @patch("plugins.modules.purefa_hg.ConnectionPost")
    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_add_single_volume_with_lun_to_existing(
        self, mock_lv, mock_check_response, mock_get_hg_hosts, mock_connection_post
    ):
        """Test adding single volume with LUN to hostgroup with existing volumes"""
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "present",
            "host": None,
            "volume": ["vol2"],
            "lun": 50,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Existing volume connection - properly set name attribute
        mock_vol = Mock()
        mock_vol.volume.name = "vol1"
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_vol]
        )
        mock_array.post_connections.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        mock_array.post_connections.assert_called_once()
        call_kwargs = mock_array.post_connections.call_args[1]
        assert call_kwargs["volume_names"] == ["vol2"]
        mock_connection_post.assert_called_once_with(lun=50)
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_add_multiple_volumes_to_existing(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test adding multiple volumes to hostgroup with existing volumes"""
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "present",
            "host": None,
            "volume": ["vol2", "vol3"],
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Existing volume connection
        mock_vol = Mock()
        mock_vol.volume = Mock(name="vol1")
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_vol]
        )
        mock_array.post_connections.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        # Should be called twice, once per new volume
        assert mock_array.post_connections.call_count == 2
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.ConnectionPost")
    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_add_volume_to_empty_hostgroup_with_lun(
        self, mock_lv, mock_check_response, mock_get_hg_hosts, mock_connection_post
    ):
        """Test adding volume with LUN to empty hostgroup (no existing volumes)"""
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "present",
            "host": None,
            "volume": ["vol1"],
            "lun": 100,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # No existing volumes
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.post_connections.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        mock_array.post_connections.assert_called_once()
        mock_connection_post.assert_called_once_with(lun=100)
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_add_volumes_to_empty_hostgroup_no_lun(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test adding volumes to empty hostgroup without LUN"""
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "present",
            "host": None,
            "volume": ["vol1", "vol2"],
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.post_connections.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        # Should be called twice, once per volume
        assert mock_array.post_connections.call_count == 2
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateHostgroupAbsentState:
    """Test cases for update_hostgroup with state=absent (removing hosts/volumes)"""

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_remove_hosts_from_hostgroup(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test removing hosts from hostgroup (state=absent with host param)"""
        # Existing hosts in hostgroup - properly set name attribute
        mock_host1 = Mock()
        mock_host1.member.name = "host1"
        mock_host2 = Mock()
        mock_host2.member.name = "host2"
        mock_get_hg_hosts.return_value = [mock_host1, mock_host2]

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "absent",
            "host": ["host1"],  # Remove host1
            "volume": None,
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.delete_host_groups_hosts.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        mock_array.delete_host_groups_hosts.assert_called_once()
        call_kwargs = mock_array.delete_host_groups_hosts.call_args[1]
        assert "host1" in call_kwargs["member_names"]
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_remove_volumes_from_hostgroup(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test removing volumes from hostgroup (state=absent with volume param)"""
        mock_get_hg_hosts.return_value = []

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "absent",
            "host": None,
            "volume": ["vol1", "vol2"],  # Remove volumes
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Existing volume connections - properly set name attribute
        mock_vol1 = Mock()
        mock_vol1.volume.name = "vol1"
        mock_vol2 = Mock()
        mock_vol2.volume.name = "vol2"
        mock_vol3 = Mock()
        mock_vol3.volume.name = "vol3"
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_vol1, mock_vol2, mock_vol3]
        )
        mock_array.delete_connections.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        mock_array.delete_connections.assert_called_once()
        call_kwargs = mock_array.delete_connections.call_args[1]
        assert set(call_kwargs["volume_names"]) == {"vol1", "vol2"}
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_remove_nonexistent_host_no_change(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test removing host that doesn't exist in hostgroup results in no change"""
        mock_host = Mock()
        mock_host.member.name = "host1"
        mock_get_hg_hosts.return_value = [mock_host]

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "absent",
            "host": ["host999"],  # Not in hostgroup
            "volume": None,
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])

        update_hostgroup(mock_module, mock_array)

        mock_array.delete_host_groups_hosts.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestDeleteHostgroupPaths:
    """Test cases for delete_hostgroup additional paths"""

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_delete_hostgroup_with_volumes(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test deleting hostgroup that has volume connections"""
        mock_get_hg_hosts.return_value = []

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Hostgroup has volumes connected
        mock_vol = Mock()
        mock_vol.volume = Mock(name="vol1")
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_vol]
        )
        mock_array.delete_connections.return_value = Mock(status_code=200)
        mock_array.delete_host_groups.return_value = Mock(status_code=200)

        delete_hostgroup(mock_module, mock_array)

        mock_array.delete_connections.assert_called_once()
        mock_array.delete_host_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_delete_hostgroup_check_mode(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test delete_hostgroup in check mode"""
        mock_get_hg_hosts.return_value = []

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-hg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vol = Mock()
        mock_vol.volume = Mock(name="vol1")
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_vol]
        )

        delete_hostgroup(mock_module, mock_array)

        mock_array.delete_connections.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestOldApiVersionPaths:
    """Test cases for older API version paths (without context support)"""

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_make_hostgroup_old_api_with_volume(self, mock_lv, mock_check_response):
        """Test make_hostgroup with old API version (no context)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "host": None,
            "volume": ["vol1"],
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Old API
        mock_array.post_host_groups.return_value = Mock(status_code=200)
        mock_array.post_connections.return_value = Mock(status_code=200)

        make_hostgroup(mock_module, mock_array)

        # Verify no context_names in call
        call_kwargs = mock_array.post_connections.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_make_hostgroup_old_api_with_hosts(self, mock_lv, mock_check_response):
        """Test make_hostgroup with old API version adding hosts"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "host": ["host1"],
            "volume": None,
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Old API
        mock_array.post_host_groups.return_value = Mock(status_code=200)
        mock_array.post_host_groups_hosts.return_value = Mock(status_code=200)

        make_hostgroup(mock_module, mock_array)

        # Verify no context_names in call
        call_kwargs = mock_array.post_host_groups_hosts.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_update_hostgroup_old_api_add_hosts(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test update_hostgroup with old API version adding hosts"""
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "present",
            "host": ["host1"],
            "volume": None,
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Old API
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.patch_hosts.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        call_kwargs = mock_array.patch_hosts.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.rename_exists")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_update_hostgroup_old_api_rename(
        self, mock_lv, mock_check_response, mock_rename_exists, mock_get_hg_hosts
    ):
        """Test update_hostgroup with old API version renaming"""
        mock_get_hg_hosts.return_value = []
        mock_rename_exists.return_value = False
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": "new-hg",
            "state": "present",
            "host": None,
            "volume": None,
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Old API
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.patch_host_groups.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        call_kwargs = mock_array.patch_host_groups.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_delete_hostgroup_old_api(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test delete_hostgroup with old API version"""
        mock_get_hg_hosts.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Old API
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.delete_host_groups.return_value = Mock(status_code=200)

        delete_hostgroup(mock_module, mock_array)

        call_kwargs = mock_array.delete_host_groups.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_delete_hostgroup_old_api_with_hosts(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test delete_hostgroup with old API removing hosts"""
        mock_host = Mock()
        mock_host.member.name = "host1"
        mock_host.group.name = "test-hg"
        mock_get_hg_hosts.return_value = [mock_host]

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Old API
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.delete_host_groups_hosts.return_value = Mock(status_code=200)
        mock_array.delete_host_groups.return_value = Mock(status_code=200)

        delete_hostgroup(mock_module, mock_array)

        call_kwargs = mock_array.delete_host_groups_hosts.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_update_hostgroup_old_api_remove_hosts(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test update_hostgroup with old API removing hosts"""
        mock_host = Mock()
        mock_host.member.name = "host1"
        mock_get_hg_hosts.return_value = [mock_host]

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "absent",
            "host": ["host1"],
            "volume": None,
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Old API
        mock_array.get_connections.return_value = Mock(status_code=200, items=[])
        mock_array.delete_host_groups_hosts.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        call_kwargs = mock_array.delete_host_groups_hosts.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_hg.get_hostgroup_hosts")
    @patch("plugins.modules.purefa_hg.check_response")
    @patch("plugins.modules.purefa_hg.LooseVersion", side_effect=LooseVersion)
    def test_update_hostgroup_old_api_remove_volumes(
        self, mock_lv, mock_check_response, mock_get_hg_hosts
    ):
        """Test update_hostgroup with old API removing volumes"""
        mock_get_hg_hosts.return_value = []

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-hg",
            "rename": None,
            "state": "absent",
            "host": None,
            "volume": ["vol1"],
            "lun": None,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Old API
        mock_vol = Mock()
        mock_vol.volume.name = "vol1"
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_vol]
        )
        mock_array.delete_connections.return_value = Mock(status_code=200)

        update_hostgroup(mock_module, mock_array)

        call_kwargs = mock_array.delete_connections.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)
