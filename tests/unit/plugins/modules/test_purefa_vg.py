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
    _priority_adjustment,
    _priority_bands,
    _stored_priority,
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


def _null_priority(operator="="):
    """SDK model for {"priority_adjustment_operator": "=",
    "priority_adjustment_value": null} (issue 1103): the operator reads, the
    value raises AttributeError."""
    pa = Mock(spec=["priority_adjustment_operator"])
    pa.priority_adjustment_operator = operator
    return pa


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


class TestQaFixes:
    """Regression tests for defects found by the hardware QA suite"""

    def _main_module(self, **overrides):
        params = {
            "name": "old-vg",
            "state": "present",
            "bw_qos": None,
            "iops_qos": None,
            "count": None,
            "start": 0,
            "digits": 1,
            "suffix": "",
            "priority_operator": None,
            "priority_value": None,
            "eradicate": False,
            "rename": None,
            "context": "",
        }
        params.update(overrides)
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = params
        mock_module.exit_json.side_effect = SystemExit("exit_json called")
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        return mock_module

    @patch("plugins.modules.purefa_vg.make_vgroup")
    @patch("plugins.modules.purefa_vg.rename_exists")
    @patch("plugins.modules.purefa_vg.get_pending_vgroup")
    @patch("plugins.modules.purefa_vg.get_vgroup")
    @patch("plugins.modules.purefa_vg.get_array")
    @patch("plugins.modules.purefa_vg.AnsibleModule")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.HAS_PURESTORAGE", True)
    def test_main_repeat_rename_is_noop(
        self,
        mock_lv,
        mock_ansible_module,
        mock_get_array,
        mock_get_vgroup,
        mock_get_pending,
        mock_rename_exists,
        mock_make_vgroup,
    ):
        """Repeating a completed rename neither re-creates the old name
        nor reports a change"""
        from plugins.modules.purefa_vg import main

        mock_module = self._main_module(rename="new-vg")
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_fleets.return_value = Mock(status_code=400, items=[])
        mock_get_array.return_value = mock_array
        mock_get_vgroup.return_value = None  # source already renamed away
        mock_get_pending.return_value = None
        mock_rename_exists.return_value = True

        try:
            main()
        except SystemExit:
            pass

        mock_make_vgroup.assert_not_called()
        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_vg.make_vgroup")
    @patch("plugins.modules.purefa_vg.rename_exists")
    @patch("plugins.modules.purefa_vg.get_pending_vgroup")
    @patch("plugins.modules.purefa_vg.get_vgroup")
    @patch("plugins.modules.purefa_vg.get_array")
    @patch("plugins.modules.purefa_vg.AnsibleModule")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_vg.HAS_PURESTORAGE", True)
    def test_main_rename_missing_source_fails(
        self,
        mock_lv,
        mock_ansible_module,
        mock_get_array,
        mock_get_vgroup,
        mock_get_pending,
        mock_rename_exists,
        mock_make_vgroup,
    ):
        """Rename with neither source nor target present fails instead of
        creating the source"""
        from plugins.modules.purefa_vg import main

        mock_module = self._main_module(rename="new-vg")
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_fleets.return_value = Mock(status_code=400, items=[])
        mock_get_array.return_value = mock_array
        mock_get_vgroup.return_value = None
        mock_get_pending.return_value = None
        mock_rename_exists.return_value = False

        try:
            main()
        except SystemExit:
            pass

        mock_make_vgroup.assert_not_called()
        mock_module.fail_json.assert_called_once()
        assert "rename failed" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_vgroup_qos_only_keeps_priority(self, mock_lv, mock_check_response):
        """A QoS-only update does not touch an existing -10 priority"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": "100M",
            "iops_qos": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_vg = Mock()
        mock_vg.priority_adjustment = Mock(
            priority_adjustment_operator="-", priority_adjustment_value=10
        )
        mock_vg.qos = Mock(bandwidth_limit=549755813888, iops_limit=100000000)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volume_groups.return_value = Mock(
            status_code=200, items=[mock_vg]
        )
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)

        with patch("plugins.modules.purefa_vg.human_to_bytes", return_value=104857600):
            update_vgroup(mock_module, mock_array)

        # exactly one patch, and it is the QoS one, not a priority reset
        mock_array.patch_volume_groups.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_make_vgroup_without_priority_skips_patch(
        self, mock_lv, mock_check_response
    ):
        """Creating a volume group without priority parameters does not
        patch a priority adjustment"""
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
        mock_array.post_volume_groups.return_value = Mock(status_code=200)

        make_vgroup(mock_module, mock_array)

        mock_array.post_volume_groups.assert_called_once()
        mock_array.patch_volume_groups.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_get_multi_vgroups_without_suffix(self, mock_lv):
        """count without suffix builds names without a None suffix"""
        mock_module = Mock()
        mock_module.params = {
            "name": "vg",
            "count": 2,
            "start": 0,
            "digits": 2,
            "suffix": "",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volume_groups.return_value = Mock(status_code=200)

        get_multi_vgroups(mock_module, mock_array)

        assert mock_array.get_volume_groups.call_args[1]["names"] == ["vg00", "vg01"]


class TestPriorityNullValue:
    """Regression tests for issue 1103: Purity//FA 6.12 (REST 2.59) reports
    an unset priority adjustment as operator "=" with a null value, and the
    SDK raises AttributeError when the null field is read."""

    @staticmethod
    def _module(operator, value, check_mode=False):
        mock_module = Mock()
        mock_module.check_mode = check_mode
        mock_module.params = {
            "name": "test-vg",
            "context": "",
            "bw_qos": None,
            "iops_qos": None,
            "priority_operator": operator,
            "priority_value": value,
        }
        return mock_module

    @staticmethod
    def _array(api_version, priority_adjustment):
        mock_vg = Mock()
        mock_vg.priority_adjustment = priority_adjustment
        mock_vg.qos = Mock(bandwidth_limit=549755813888, iops_limit=100000000)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = api_version
        # The array's Purity release decides the comparison form, not the
        # negotiated REST version: 2.59 stands for a 6.12 array here.
        purity = "6.12.4" if api_version == "2.59" else "6.10.6"
        mock_array.get_arrays.return_value = Mock(items=[Mock(version=purity)])
        mock_array.get_volume_groups.return_value = Mock(
            status_code=200, items=[mock_vg]
        )
        mock_array.patch_volume_groups.return_value = Mock(status_code=200)
        return mock_array

    @staticmethod
    def _explicit(operator, value):
        return Mock(
            priority_adjustment_operator=operator, priority_adjustment_value=value
        )

    def test_null_priority_model_raises_like_the_sdk(self):
        """The test model reproduces the SDK: operator reads, value raises"""
        pa = _null_priority()
        assert pa.priority_adjustment_operator == "="
        try:
            pa.priority_adjustment_value
        except AttributeError:
            pass
        else:
            raise AssertionError("value read should raise AttributeError")

    def test_priority_adjustment_helper(self):
        """Null value reads as the unset state; explicit values pass through"""
        vg = Mock()
        vg.priority_adjustment = _null_priority()
        assert _priority_adjustment(vg) == ("+", 0)
        vg.priority_adjustment = self._explicit("=", 10)
        assert _priority_adjustment(vg) == ("=", 10)
        vg.priority_adjustment = self._explicit("=", 0)
        assert _priority_adjustment(vg) == ("=", 0)
        vg.priority_adjustment = self._explicit("-", 10)
        assert _priority_adjustment(vg) == ("-", 10)
        # a missing parent is the unset state too
        assert _priority_adjustment(Mock(spec=[])) == ("+", 0)
        assert _priority_adjustment(None) == ("+", 0)

    def test_stored_priority_helper(self):
        """Relative zero is unset everywhere; priority bands fold +/- into "=" """
        assert _stored_priority("+", 0, False) == ("+", 0)
        assert _stored_priority("-", 0, True) == ("+", 0)
        assert _stored_priority("+", 10, False) == ("+", 10)
        assert _stored_priority("-", 10, False) == ("-", 10)
        assert _stored_priority("+", 10, True) == ("=", 10)
        assert _stored_priority("-", 10, True) == ("=", -10)
        assert _stored_priority("=", 0, True) == ("=", 0)
        assert _stored_priority("=", 10, False) == ("=", 10)

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_priority_bands_follows_the_purity_release(self, mock_lv):
        """Decided by the Purity release the array reports, not by the REST
        version the client negotiated (an old SDK talks 2.57 to a 6.12 array)"""
        array = Mock()
        array.get_rest_version.return_value = "2.57"
        array.get_arrays.return_value = Mock(items=[Mock(version="6.12.4")])
        assert _priority_bands(array) is True
        array.get_arrays.return_value = Mock(items=[Mock(version="6.12.0")])
        assert _priority_bands(array) is True
        array.get_arrays.return_value = Mock(items=[Mock(version="6.10.6")])
        assert _priority_bands(array) is False
        # an unreadable release keeps the pre-6.12 comparison
        array.get_arrays.return_value = Mock(items=[])
        assert _priority_bands(array) is False
        array.get_arrays.side_effect = TypeError
        assert _priority_bands(array) is False

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_bare_present_with_null_priority_does_not_raise(self, mock_lv):
        """Bare state=present on a 6.12 vgroup with a null priority value
        neither raises nor patches"""
        mock_module = self._module(None, None)
        mock_array = self._array("2.59", _null_priority())

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_plus_zero_vs_null_is_noop(self, mock_lv):
        """Requested +0 against an unset (null) adjustment is unchanged"""
        mock_module = self._module("+", 0)
        mock_array = self._array("2.59", _null_priority())

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_plus_ten_vs_stored_equals_ten_on_259_is_noop(self, mock_lv):
        """Requested +10 against the array's stored form =10 on 2.59 is
        unchanged: the second run of a playbook does not patch"""
        mock_module = self._module("+", 10)
        mock_array = self._array("2.59", self._explicit("=", 10))

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_minus_ten_vs_stored_equals_minus_ten_on_259_is_noop(self, mock_lv):
        """Requested -10 against the stored form =-10 on 2.59 is unchanged"""
        mock_module = self._module("-", 10)
        mock_array = self._array("2.59", self._explicit("=", -10))

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.PriorityAdjustment")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_plus_ten_vs_equals_ten_on_254_is_a_change(
        self, mock_lv, mock_prio, mock_check_response
    ):
        """Below 2.59 the array keeps the operator, so +10 vs =10 differs"""
        mock_module = self._module("+", 10)
        mock_array = self._array("2.54", self._explicit("=", 10))

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called_once()
        mock_prio.assert_called_once_with(
            priority_adjustment_operator="+", priority_adjustment_value=10
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.PriorityAdjustment")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_plus_ten_vs_null_patches_the_request(
        self, mock_lv, mock_prio, mock_check_response
    ):
        """Requested +10 against an unset (null) adjustment is a change and
        the PATCH body is built from the request, never from the null"""
        mock_module = self._module("+", 10)
        mock_array = self._array("2.59", _null_priority())

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called_once()
        mock_prio.assert_called_once_with(
            priority_adjustment_operator="+", priority_adjustment_value=10
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.PriorityAdjustment")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_explicit_zero_vs_null_is_a_change(
        self, mock_lv, mock_prio, mock_check_response
    ):
        """An explicit "=0" pin is distinct from the unset (null) state, so
        requesting it against null is a change sent as given"""
        mock_module = self._module("=", 0)
        mock_array = self._array("2.59", _null_priority())

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called_once()
        mock_prio.assert_called_once_with(
            priority_adjustment_operator="=", priority_adjustment_value=0
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.PriorityAdjustment")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_without_context_sends_no_context_names(
        self, mock_lv, mock_prio, mock_check_response
    ):
        """An empty context must not be sent: the array answers an empty
        context_names with a 500 'Unidentified internal error'"""
        mock_module = self._module("+", 10)
        mock_array = self._array("2.59", _null_priority())

        update_vgroup(mock_module, mock_array)

        kwargs = mock_array.patch_volume_groups.call_args[1]
        assert kwargs["names"] == ["test-vg"]
        assert "context_names" not in kwargs

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.PriorityAdjustment")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_with_context_sends_context_names(
        self, mock_lv, mock_prio, mock_check_response
    ):
        mock_module = self._module("+", 10)
        mock_module.params["context"] = "member-array"
        mock_array = self._array("2.59", _null_priority())

        update_vgroup(mock_module, mock_array)

        kwargs = mock_array.patch_volume_groups.call_args[1]
        assert kwargs["context_names"] == ["member-array"]

    @patch("plugins.modules.purefa_vg.PriorityAdjustment")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_plus_ten_vs_null_check_mode(self, mock_lv, mock_prio):
        """Check mode reports the change without patching"""
        mock_module = self._module("+", 10, check_mode=True)
        mock_array = self._array("2.59", _null_priority())

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_not_called()
        mock_prio.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vg.check_response")
    @patch("plugins.modules.purefa_vg.PriorityAdjustment")
    @patch("plugins.modules.purefa_vg.LooseVersion", side_effect=LooseVersion)
    def test_update_plus_zero_vs_stored_ten_on_259_resets(
        self, mock_lv, mock_prio, mock_check_response
    ):
        """Requested +0 against a stored =10 on 2.59 clears the adjustment
        with the request as given"""
        mock_module = self._module("+", 0)
        mock_array = self._array("2.59", self._explicit("=", 10))

        update_vgroup(mock_module, mock_array)

        mock_array.patch_volume_groups.assert_called_once()
        mock_prio.assert_called_once_with(
            priority_adjustment_operator="+", priority_adjustment_value=0
        )
        mock_module.exit_json.assert_called_once_with(changed=True)
