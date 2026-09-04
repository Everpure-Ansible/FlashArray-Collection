# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_vg module."""

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

from plugins.modules.purefa_vg import (
    rename_exists,
    get_multi_vgroups,
    get_pending_vgroup,
    get_vgroup,
    rename_vgroup,
    make_vgroup,
    make_multi_vgroups,
    update_vgroup,
    delete_vgroup,
    eradicate_vgroup,
    recover_vgroup,
)
import plugins.modules.purefa_vg as _vg_module


def _passthrough_with_context(client, method_name, context_version, module, **kwargs):
    """Mirror api_helpers.*_with_context for tests by calling the array method directly.

    api_helpers is mocked out at import time, so the real helpers are unavailable.
    The context_names argument is intentionally omitted - no test asserts on it.
    """
    return getattr(client, method_name)(**kwargs)


_vg_module.get_with_context = _passthrough_with_context
_vg_module.post_with_context = _passthrough_with_context
_vg_module.patch_with_context = _passthrough_with_context
_vg_module.delete_with_context = _passthrough_with_context


class TestRenameExists:
    """Test cases for rename_exists function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_rename_exists_true(self, mock_loose_version):
        """Test rename_exists returns True when target exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"rename": "new-vg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_groups.return_value = Mock(status_code=200)

        result = rename_exists(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_rename_exists_false(self, mock_loose_version):
        """Test rename_exists returns False when target doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"rename": "new-vg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_groups.return_value = Mock(status_code=404)

        result = rename_exists(mock_module, mock_array)

        assert result is False


class TestGetMultiVgroups:
    """Test cases for get_multi_vgroups function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_get_multi_vgroups_all_exist(self, mock_loose_version):
        """Test get_multi_vgroups returns True when all vgroups exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {
            "name": "vg",
            "start": 0,
            "count": 3,
            "digits": 2,
            "suffix": "",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_groups.return_value = Mock(status_code=200)

        result = get_multi_vgroups(mock_module, mock_array)

        assert result is True


class TestGetPendingVgroup:
    """Test cases for get_pending_vgroup function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_get_pending_vgroup_exists(self, mock_loose_version):
        """Test get_pending_vgroup returns True when deleted vgroup exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "deleted-vg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_groups.return_value = Mock(status_code=200)

        result = get_pending_vgroup(mock_module, mock_array)

        assert result is True


class TestGetVgroup:
    """Test cases for get_vgroup function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_get_vgroup_exists(self, mock_loose_version):
        """Test get_vgroup returns True when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-vg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_groups.return_value = Mock(status_code=200)

        result = get_vgroup(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_get_vgroup_not_exists(self, mock_loose_version):
        """Test get_vgroup returns False when vgroup doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_groups.return_value = Mock(status_code=404)

        result = get_vgroup(mock_module, mock_array)

        assert result is False


class TestMakeVgroup:
    """Test cases for make_vgroup function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_make_vgroup_check_mode(self, mock_loose_version):
        """Test make_vgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "new-vg", "bw_qos": None, "iops_qos": None}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        make_vgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMakeMultiVgroups:
    """Test cases for make_multi_vgroups function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_make_multi_vgroups_check_mode(self, mock_loose_version):
        """Test make_multi_vgroups in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "vg",
            "start": 0,
            "count": 3,
            "digits": 2,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        make_multi_vgroups(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteVgroup:
    """Test cases for delete_vgroup function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_delete_vgroup_check_mode(self, mock_loose_version):
        """Test delete_vgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-vg", "eradicate": False}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        delete_vgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicateVgroup:
    """Test cases for eradicate_vgroup function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_eradicate_vgroup_check_mode(self, mock_loose_version):
        """Test eradicate_vgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-vg"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        eradicate_vgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverVgroup:
    """Test cases for recover_vgroup function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_recover_vgroup_check_mode(self, mock_loose_version):
        """Test recover_vgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-vg"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        recover_vgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenameVgroup:
    """Test cases for rename_vgroup function"""

    @patch("plugins.modules.purefa_vg.rename_exists")
    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_rename_vgroup_check_mode(self, mock_loose_version, mock_rename_exists):
        """Test rename_vgroup in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_rename_exists.return_value = False
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "old-vg", "rename": "new-vg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        rename_vgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.rename_exists")
    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_rename_vgroup_target_exists(self, mock_loose_version, mock_rename_exists):
        """Test rename_vgroup when target already exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_rename_exists.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "old-vg", "rename": "existing-vg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        rename_vgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdateVgroup:
    """Test cases for update_vgroup function"""

    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_update_vgroup_no_changes(self, mock_loose_version):
        """Test update_vgroup with no changes needed"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": None,
            "iops_qos": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_module.params = params
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_vg = Mock()
        mock_vg.qos = Mock(bandwidth_limit=None, iops_limit=None)
        mock_array.get_volume_groups.return_value.items = [mock_vg]

        update_vgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestDeleteVgroupSuccess:
    """Test cases for delete_vgroup success paths"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_delete_vgroup_success(self, mock_loose_version, mock_check_response):
        """Test delete_vgroup successfully deletes"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        delete_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.eradicate_vgroup")
    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_delete_vgroup_with_eradicate(
        self, mock_loose_version, mock_check_response, mock_eradicate
    ):
        """Test delete_vgroup with eradicate=True"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "eradicate": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        delete_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called_once()
        mock_eradicate.assert_called_once()


class TestEradicateVgroupSuccess:
    """Test cases for eradicate_vgroup success paths"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_eradicate_vgroup_success(self, mock_loose_version, mock_check_response):
        """Test eradicate_vgroup successfully eradicates"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-vg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.delete_volume_groups.return_value = Mock(status_code=200)

        eradicate_vgroup(mock_module, mock_array)

        mock_array.delete_volume_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverVgroupSuccess:
    """Test cases for recover_vgroup success paths"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_recover_vgroup_success(self, mock_loose_version, mock_check_response):
        """Test recover_vgroup successfully recovers"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-vg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        recover_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenameVgroupSuccess:
    """Test cases for rename_vgroup success paths"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.rename_exists")
    @patch("plugins.modules.purefa_vg.LooseVersion")
    def test_rename_vgroup_success(
        self, mock_loose_version, mock_rename_exists, mock_check_response
    ):
        """Test rename_vgroup successfully renames"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_rename_exists.return_value = False
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "old-vg", "rename": "new-vg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        rename_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMakeVgroupSuccess:
    """Test cases for make_vgroup function success scenarios"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    def test_make_vgroup_with_bw_qos(
        self, mock_human_to_bytes, mock_lv, mock_check_response
    ):
        """Test make_vgroup with bandwidth QoS"""
        mock_human_to_bytes.return_value = 1073741824  # 1GB in bytes
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": "1G",
            "iops_qos": None,
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_vgroup(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_make_vgroup_with_iops_qos(
        self, mock_human_to_real, mock_lv, mock_check_response
    ):
        """Test make_vgroup with IOPS QoS"""
        mock_human_to_real.return_value = 10000  # 10K IOPS
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": None,
            "iops_qos": "10K",
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_vgroup(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_make_vgroup_no_qos(self, mock_lv, mock_check_response):
        """Test make_vgroup without QoS settings"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": None,
            "iops_qos": None,
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_vgroup(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateVgroupSuccess:
    """Test cases for update_vgroup function success scenarios"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_vgroup_priority_change(self, mock_lv, mock_check_response):
        """Test update_vgroup changing priority"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": None,
            "iops_qos": None,
            "priority_operator": "+",
            "priority_value": 5,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current vgroup with different priority
        mock_vg = Mock()
        mock_vg.priority_adjustment = Mock()
        mock_vg.priority_adjustment.priority_adjustment_operator = "+"
        mock_vg.priority_adjustment.priority_adjustment_value = 0
        mock_vg.qos = Mock()
        mock_array.get_volume_groups.return_value = Mock(items=[mock_vg])
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    def test_update_vgroup_bw_qos_change(
        self, mock_human_to_bytes, mock_lv, mock_check_response
    ):
        """Test update_vgroup changing bandwidth QoS"""
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": "1G",
            "iops_qos": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current vgroup
        mock_vg = Mock()
        mock_vg.priority_adjustment = Mock()
        mock_vg.priority_adjustment.priority_adjustment_operator = "+"
        mock_vg.priority_adjustment.priority_adjustment_value = 0
        mock_vg.qos = Mock()
        mock_vg.qos.bandwidth_limit = 549755813888  # Default
        mock_array.get_volume_groups.return_value = Mock(items=[mock_vg])
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_vgroup_no_changes(self, mock_lv):
        """Test update_vgroup when no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": None,
            "iops_qos": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current vgroup
        mock_vg = Mock()
        mock_vg.priority_adjustment = Mock()
        mock_vg.priority_adjustment.priority_adjustment_operator = "+"
        mock_vg.priority_adjustment.priority_adjustment_value = 0
        mock_vg.qos = Mock()
        mock_array.get_volume_groups.return_value = Mock(items=[mock_vg])

        update_vgroup(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_update_vgroup_iops_qos_change(
        self, mock_human_to_real, mock_lv, mock_check_response
    ):
        """Test update_vgroup changing IOPS QoS"""
        mock_human_to_real.return_value = 50000
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": None,
            "iops_qos": "50K",
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vg = Mock()
        mock_vg.priority_adjustment = Mock()
        mock_vg.priority_adjustment.priority_adjustment_operator = "+"
        mock_vg.priority_adjustment.priority_adjustment_value = 0
        mock_vg.qos = Mock()
        mock_vg.qos.iops_limit = 100000000  # Default MAX
        mock_array.get_volume_groups.return_value = Mock(items=[mock_vg])
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_update_vgroup_iops_qos_disable(
        self, mock_human_to_real, mock_lv, mock_check_response
    ):
        """Test update_vgroup disabling IOPS QoS with 0"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": None,
            "iops_qos": "0",
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vg = Mock()
        mock_vg.priority_adjustment = Mock()
        mock_vg.priority_adjustment.priority_adjustment_operator = "+"
        mock_vg.priority_adjustment.priority_adjustment_value = 0
        mock_vg.qos = Mock()
        mock_vg.qos.iops_limit = 50000  # Current limit
        mock_array.get_volume_groups.return_value = Mock(items=[mock_vg])
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    def test_update_vgroup_bw_qos_disable(
        self, mock_human_to_bytes, mock_lv, mock_check_response
    ):
        """Test update_vgroup disabling bandwidth QoS with 0"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": "0",
            "iops_qos": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vg = Mock()
        mock_vg.priority_adjustment = Mock()
        mock_vg.priority_adjustment.priority_adjustment_operator = "+"
        mock_vg.priority_adjustment.priority_adjustment_value = 0
        mock_vg.qos = Mock()
        mock_vg.qos.bandwidth_limit = 1073741824  # Current limit
        mock_array.get_volume_groups.return_value = Mock(items=[mock_vg])
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_vgroup_priority_operator_change(self, mock_lv, mock_check_response):
        """Test update_vgroup changing priority operator"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": None,
            "iops_qos": None,
            "priority_operator": "-",
            "priority_value": 10,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vg = Mock()
        mock_vg.priority_adjustment = Mock()
        mock_vg.priority_adjustment.priority_adjustment_operator = "+"
        mock_vg.priority_adjustment.priority_adjustment_value = 0
        mock_vg.qos = Mock()
        mock_array.get_volume_groups.return_value = Mock(items=[mock_vg])
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMakeVgroupComplex:
    """Test cases for make_vgroup with complex QoS scenarios"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_make_vgroup_both_qos(
        self, mock_human_to_real, mock_human_to_bytes, mock_lv, mock_check_response
    ):
        """Test make_vgroup with both BW and IOPS QoS"""
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_human_to_real.return_value = 50000
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": "1G",
            "iops_qos": "50K",
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.11"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_vgroup(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_make_vgroup_both_qos_with_context(
        self, mock_human_to_real, mock_human_to_bytes, mock_lv, mock_check_response
    ):
        """Test make_vgroup with both QoS and context"""
        mock_human_to_bytes.return_value = 2147483648  # 2GB
        mock_human_to_real.return_value = 100000
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "fleet-context",
            "bw_qos": "2G",
            "iops_qos": "100K",
            "priority_operator": "+",
            "priority_value": 10,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_vgroup(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_make_vgroup_both_qos_out_of_range(
        self, mock_human_to_real, mock_human_to_bytes, mock_lv
    ):
        """Test make_vgroup with QoS values out of range"""
        mock_human_to_bytes.return_value = 100  # Too small
        mock_human_to_real.return_value = 10  # Too small
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": "100",
            "iops_qos": "10",
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.11"

        make_vgroup(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_make_vgroup_no_qos_with_context(self, mock_lv, mock_check_response):
        """Test make_vgroup with no QoS but with context"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "fleet-context",
            "bw_qos": None,
            "iops_qos": None,
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_vgroup(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMakeMultiVgroupsQoS:
    """Test cases for make_multi_vgroups with QoS"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    def test_make_multi_vgroups_bw_qos(
        self, mock_human_to_bytes, mock_lv, mock_check_response
    ):
        """Test make_multi_vgroups with bandwidth QoS"""
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "count": 3,
            "start": 0,
            "digits": 2,
            "suffix": "",
            "bw_qos": "1G",
            "iops_qos": None,
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.11"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_multi_vgroups(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_make_multi_vgroups_iops_qos(
        self, mock_human_to_real, mock_lv, mock_check_response
    ):
        """Test make_multi_vgroups with IOPS QoS"""
        mock_human_to_real.return_value = 50000
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "count": 3,
            "start": 1,
            "digits": 3,
            "suffix": "-data",
            "bw_qos": None,
            "iops_qos": "50K",
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.11"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_multi_vgroups(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_make_multi_vgroups_both_qos(
        self, mock_human_to_real, mock_human_to_bytes, mock_lv, mock_check_response
    ):
        """Test make_multi_vgroups with both QoS types"""
        mock_human_to_bytes.return_value = 2147483648  # 2GB
        mock_human_to_real.return_value = 100000
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "count": 5,
            "start": 0,
            "digits": 2,
            "suffix": "",
            "bw_qos": "2G",
            "iops_qos": "100K",
            "priority_operator": "-",
            "priority_value": 10,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.11"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_multi_vgroups(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_make_multi_vgroups_both_qos_with_context(
        self, mock_human_to_real, mock_human_to_bytes, mock_lv, mock_check_response
    ):
        """Test make_multi_vgroups with both QoS and context"""
        mock_human_to_bytes.return_value = 1073741824
        mock_human_to_real.return_value = 50000
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "fleet-context",
            "count": 2,
            "start": 0,
            "digits": 1,
            "suffix": "",
            "bw_qos": "1G",
            "iops_qos": "50K",
            "priority_operator": "+",
            "priority_value": 10,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volume_groups.return_value = Mock(status_code=200)
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        make_multi_vgroups(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_bytes")
    def test_make_multi_vgroups_bw_qos_out_of_range(self, mock_human_to_bytes, mock_lv):
        """Test make_multi_vgroups with bandwidth QoS out of range"""
        mock_human_to_bytes.return_value = 100  # Too small
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "count": 2,
            "start": 0,
            "digits": 1,
            "suffix": "",
            "bw_qos": "100",
            "iops_qos": None,
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.11"

        make_multi_vgroups(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.human_to_real")
    def test_make_multi_vgroups_iops_qos_out_of_range(
        self, mock_human_to_real, mock_lv
    ):
        """Test make_multi_vgroups with IOPS QoS out of range"""
        mock_human_to_real.return_value = 10  # Too small
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "count": 2,
            "start": 0,
            "digits": 1,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": "10",
            "priority_operator": "+",
            "priority_value": 0,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.11"

        make_multi_vgroups(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestRecoverVgroup:
    """Test cases for recover_vgroup function"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_recover_vgroup_with_context(self, mock_lv, mock_check_response):
        """Test recover_vgroup with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "fleet-context",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        recover_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicateVgroup:
    """Test cases for eradicate_vgroup function"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_vgroup_with_context(self, mock_lv, mock_check_response):
        """Test eradicate_vgroup with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "fleet-context",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_volume_groups.return_value = Mock(status_code=200)

        eradicate_vgroup(mock_module, mock_array)

        mock_array.delete_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteVgroup:
    """Test cases for delete_vgroup function"""

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_delete_vgroup_with_context(self, mock_lv, mock_check_response):
        """Test delete_vgroup with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "fleet-context",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        delete_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)
