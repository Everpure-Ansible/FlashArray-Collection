# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_pgsnap module."""

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

import pytest  # pylint: disable=unused-import

from plugins.modules.purefa_pgsnap import (
    _check_offload,
    get_pgroup,
    get_pgsnapshot,
    get_rpgsnapshot,
    create_pgsnapshot,
    update_pgsnapshot,
    delete_pgsnapshot,
    eradicate_pgsnapshot,
    restore_pgsnapshot_all,
)
import plugins.modules.purefa_pgsnap as _pgsnap_module


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


_pgsnap_module.get_with_context = _passthrough_with_context
_pgsnap_module.post_with_context = _passthrough_with_context
_pgsnap_module.patch_with_context = _passthrough_with_context
_pgsnap_module.delete_with_context = _passthrough_with_context
# api_helpers/version are mocked at import; point LooseVersion at the real
# implementation so main()'s context-default check evaluates a real comparison.
# Per-test @patch("...LooseVersion") decorators still override this as needed.
_pgsnap_module.LooseVersion = LooseVersion


class TestCheckOffload:
    """Test cases for _check_offload function"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
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

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_check_offload_not_found(self, mock_loose_version):
        """Test _check_offload returns False when offload not found"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"offload": "nfs-target", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_offloads.return_value = Mock(status_code=404)

        result = _check_offload(mock_module, mock_array)

        assert result is False


class TestGetPgroup:
    """Test cases for get_pgroup function"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_get_pgroup_exists(self, mock_loose_version):
        """Test get_pgroup returns True when pgroup exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_protection_groups.return_value = Mock(status_code=200)

        result = get_pgroup(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_get_pgroup_not_exists(self, mock_loose_version):
        """Test get_pgroup returns False when pgroup doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_protection_groups.return_value = Mock(status_code=404)

        result = get_pgroup(mock_module, mock_array)

        assert result is False


class TestGetPgsnapshot:
    """Test cases for get_pgsnapshot function"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_get_pgsnapshot_exists(self, mock_loose_version):
        """Test get_pgsnapshot returns snapshot when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "suffix": "snap1", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_snap = Mock()
        mock_snap.name = "test-pg.snap1"
        mock_array.get_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap]
        )

        result = get_pgsnapshot(mock_module, mock_array)

        assert result == mock_snap

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_get_pgsnapshot_not_exists(self, mock_loose_version):
        """Test get_pgsnapshot returns None when snapshot doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "test-pg", "suffix": "snap1", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_protection_group_snapshots.return_value = Mock(status_code=404)

        result = get_pgsnapshot(mock_module, mock_array)

        assert result is None


class TestCreatePgsnapshot:
    """Test cases for create_pgsnapshot function"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_create_pgsnapshot_success(self, mock_loose_version, mock_check_response):
        """Test create_pgsnapshot creates snapshot successfully"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "context": "",
            "now": False,
            "remote": False,
            "apply_retention": False,
            "offload": None,
            "throttle": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_pg = Mock()
        mock_pg.target_count = 0
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_snap = Mock()
        mock_snap.suffix = "snap1"
        mock_array.post_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap]
        )

        create_pgsnapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True, suffix="snap1")


class TestDeletePgsnapshot:
    """Test cases for delete_pgsnapshot function"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_delete_pgsnapshot_check_mode(self, mock_loose_version):
        """Test delete_pgsnapshot in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        delete_pgsnapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePgsnapshot:
    """Test cases for eradicate_pgsnapshot function"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_eradicate_pgsnapshot_check_mode(self, mock_loose_version):
        """Test eradicate_pgsnapshot in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-pg", "suffix": "snap1", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        eradicate_pgsnapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestGetRpgsnapshot:
    """Test cases for get_rpgsnapshot function"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_get_rpgsnapshot_exists(self, mock_loose_version):
        """Test get_rpgsnapshot returns snapshot name when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "restore": "source-vol",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_snapshots.return_value.status_code = 200

        result = get_rpgsnapshot(mock_module, mock_array)

        assert result == "test-pg.snap1.source-vol"

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_get_rpgsnapshot_not_exists(self, mock_loose_version):
        """Test get_rpgsnapshot returns None when snapshot doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "restore": "source-vol",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_snapshots.return_value.status_code = 404

        result = get_rpgsnapshot(mock_module, mock_array)

        assert result is None


class TestUpdatePgsnapshot:
    """Test cases for update_pgsnapshot function"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_update_pgsnapshot_check_mode(self, mock_loose_version):
        """Test update_pgsnapshot in check mode"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "rename": "new-suffix",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        update_pgsnapshot(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_update_pgsnapshot_success(self, mock_loose_version, mock_check_response):
        """Test update_pgsnapshot successfully renames"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "target": "snap2",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.patch_protection_group_snapshots.return_value = Mock(status_code=200)

        update_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeletePgsnapshotSuccess:
    """Test cases for delete_pgsnapshot success paths"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_delete_pgsnapshot_success(self, mock_loose_version, mock_check_response):
        """Test delete_pgsnapshot successfully deletes"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.patch_protection_group_snapshots.return_value = Mock(status_code=200)

        delete_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_delete_pgsnapshot_with_eradicate(
        self, mock_loose_version, mock_check_response
    ):
        """Test delete_pgsnapshot with eradicate=True"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "context": "",
            "eradicate": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.patch_protection_group_snapshots.return_value = Mock(status_code=200)
        mock_array.delete_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        delete_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_called_once()
        mock_array.delete_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePgsnapshotSuccess:
    """Test cases for eradicate_pgsnapshot success paths"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_eradicate_pgsnapshot_success(
        self, mock_loose_version, mock_check_response
    ):
        """Test eradicate_pgsnapshot successfully eradicates"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.delete_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        eradicate_pgsnapshot(mock_module, mock_array)

        mock_array.delete_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRestorePgsnapvolume:
    """Test cases for restore_pgsnapvolume function"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    @patch("plugins.modules.purefa_pgsnap.get_pgroupvolume")
    def test_restore_pgsnapvolume_check_mode(
        self, mock_get_pgroupvolume, mock_loose_version, mock_check_response
    ):
        """Test restore_pgsnapvolume in check mode"""
        mock_loose_version.side_effect = LooseVersion
        mock_get_pgroupvolume.return_value = Mock()  # Volume exists
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "restore": "vol1",
            "target": "new-vol1",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        from plugins.modules.purefa_pgsnap import restore_pgsnapvolume

        restore_pgsnapvolume(mock_module, mock_array)

        mock_array.post_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    @patch("plugins.modules.purefa_pgsnap.get_pgroupvolume")
    def test_restore_pgsnapvolume_volume_not_in_pgroup(
        self, mock_get_pgroupvolume, mock_loose_version, mock_check_response
    ):
        """Test restore_pgsnapvolume fails when volume not in pgroup"""
        import pytest

        mock_loose_version.side_effect = LooseVersion
        mock_get_pgroupvolume.return_value = None  # Volume doesn't exist
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "restore": "nonexistent-vol",
            "target": "new-vol",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        from plugins.modules.purefa_pgsnap import restore_pgsnapvolume

        with pytest.raises(SystemExit):
            restore_pgsnapvolume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    @patch("plugins.modules.purefa_pgsnap.get_pgroupvolume")
    def test_restore_pgsnapvolume_success(
        self, mock_get_pgroupvolume, mock_loose_version, mock_check_response
    ):
        """Test restore_pgsnapvolume successfully restores volume"""
        mock_loose_version.side_effect = LooseVersion
        mock_get_pgroupvolume.return_value = Mock()  # Volume exists
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "restore": "vol1",
            "target": "new-vol1",
            "context": "",
            "overwrite": False,
            "with_default_protection": False,
            "add_to_pgs": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = Mock(status_code=200)

        from plugins.modules.purefa_pgsnap import restore_pgsnapvolume

        restore_pgsnapvolume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePgsnapshotSuccess:
    """Test cases for create_pgsnapshot success paths"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.ProtectionGroupSnapshot")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_create_pgsnapshot_with_target(
        self, mock_lv, mock_pgs, mock_check_response
    ):
        """Test create_pgsnapshot with remote target"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "apply_retention": False,
            "now": False,
            "remote": True,
            "context": "",
            "throttle": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_pg = Mock()
        mock_pg.target_count = 1
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_snap = Mock()
        mock_snap.name = "test-pg.snap1"
        mock_array.post_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap]
        )

        from plugins.modules.purefa_pgsnap import create_pgsnapshot

        create_pgsnapshot(mock_module, mock_array)

        mock_array.post_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called()


class TestDeletePgsnapshotSuccess:
    """Test cases for delete_pgsnapshot success paths"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_pgsnapshot_success(self, mock_lv, mock_check_response):
        """Test delete_pgsnapshot deletes successfully"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_protection_group_snapshots.return_value = Mock(status_code=200)

        delete_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_called_once()
        mock_check_response.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_delete_pgsnapshot_check_mode(self):
        """Test delete_pgsnapshot in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()

        delete_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePgsnapshotSuccess:
    """Test cases for eradicate_pgsnapshot success paths"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_pgsnapshot_success(self, mock_lv, mock_check_response):
        """Test eradicate_pgsnapshot eradicates successfully"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-pg", "suffix": "snap1", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        eradicate_pgsnapshot(mock_module, mock_array)

        mock_array.delete_protection_group_snapshots.assert_called_once()
        mock_check_response.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_eradicate_pgsnapshot_check_mode(self):
        """Test eradicate_pgsnapshot in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-pg", "suffix": "snap1", "context": ""}
        mock_array = Mock()

        eradicate_pgsnapshot(mock_module, mock_array)

        mock_array.delete_protection_group_snapshots.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePgsnapshotExtended:
    """Extended test cases for update_pgsnapshot"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_update_pgsnapshot_rename(self, mock_lv, mock_check_response):
        """Test update_pgsnapshot with rename"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "context": "",
            "target": "snap2",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_protection_group_snapshots.return_value = Mock(status_code=200)

        update_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_called_once()
        mock_check_response.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_pgsnapshot_check_mode(self):
        """Test update_pgsnapshot in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-pg",
            "suffix": "snap1",
            "context": "",
            "target": "snap2",
        }
        mock_array = Mock()

        update_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteOffloadSnapshot:
    """Test cases for delete_offload_snapshot function"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap._check_offload")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_success(
        self, mock_lv, mock_check_offload, mock_check_response
    ):
        """Test successful deletion of offload snapshot"""
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "array2:pg1",
            "suffix": "snap1",
            "offload": "s3target",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_remote_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[Mock(destroyed=False)]
        )
        mock_array.patch_remote_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        delete_offload_snapshot(mock_module, mock_array)

        mock_array.patch_remote_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap._check_offload")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_offload_not_connected(
        self, mock_lv, mock_check_offload
    ):
        """Test delete_offload_snapshot fails when offload not connected"""
        import pytest
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_check_offload.return_value = False
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "array2:pg1",
            "suffix": "snap1",
            "offload": "s3target",
            "context": "",
            "eradicate": False,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        with pytest.raises(SystemExit):
            delete_offload_snapshot(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "not exist or not connected" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_bad_name_format(self, mock_lv):
        """Test delete_offload_snapshot fails with bad name format"""
        import pytest
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",  # No colon - bad format
            "suffix": "snap1",
            "offload": "s3target",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        with pytest.raises(SystemExit):
            delete_offload_snapshot(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "not in the correct format" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap._check_offload")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_with_eradicate(
        self, mock_lv, mock_check_offload, mock_check_response
    ):
        """Test deletion of offload snapshot with eradicate"""
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_check_offload.return_value = True
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "array2:pg1",
            "suffix": "snap1",
            "offload": "s3target",
            "context": "",
            "eradicate": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_remote_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[Mock(destroyed=False)]
        )
        mock_array.patch_remote_protection_group_snapshots.return_value = Mock(
            status_code=200
        )
        mock_array.delete_remote_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        delete_offload_snapshot(mock_module, mock_array)

        mock_array.patch_remote_protection_group_snapshots.assert_called_once()
        mock_array.delete_remote_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePgSnapshot:
    """Test cases for update_pgsnapshot function"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_update_pgsnapshot_success(self, mock_lv, mock_check_response):
        """Test updating/renaming a protection group snapshot"""
        from plugins.modules.purefa_pgsnap import update_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "target": "snap2",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_protection_group_snapshots.return_value = Mock(status_code=200)

        update_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_update_pgsnapshot_check_mode(self, mock_lv):
        """Test updating snapshot in check mode"""
        from plugins.modules.purefa_pgsnap import update_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "target": "snap2",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        update_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_update_pgsnapshot_older_api(self, mock_lv, mock_check_response):
        """Test updating snapshot with older API version"""
        from plugins.modules.purefa_pgsnap import update_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "target": "snap2",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.16"
        mock_array.patch_protection_group_snapshots.return_value = Mock(status_code=200)

        update_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_called_once()
        # Verify no context_names kwarg in call
        call_kwargs = mock_array.patch_protection_group_snapshots.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicatePgSnapshot:
    """Test cases for eradicate_pgsnapshot function"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_pgsnapshot_success(self, mock_lv, mock_check_response):
        """Test eradicating a protection group snapshot"""
        from plugins.modules.purefa_pgsnap import eradicate_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        eradicate_pgsnapshot(mock_module, mock_array)

        mock_array.delete_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_pgsnapshot_check_mode(self, mock_lv):
        """Test eradicating snapshot in check mode"""
        from plugins.modules.purefa_pgsnap import eradicate_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        eradicate_pgsnapshot(mock_module, mock_array)

        mock_array.delete_protection_group_snapshots.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_eradicate_pgsnapshot_older_api(self, mock_lv, mock_check_response):
        """Test eradicating snapshot with older API version"""
        from plugins.modules.purefa_pgsnap import eradicate_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.16"
        mock_array.delete_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        eradicate_pgsnapshot(mock_module, mock_array)

        mock_array.delete_protection_group_snapshots.assert_called_once()
        # Verify no context_names kwarg in call
        call_kwargs = mock_array.delete_protection_group_snapshots.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestGetPgroupvolume:
    """Test cases for get_pgroupvolume function"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_get_pgroupvolume_host_pg_context_api(self, mock_lv):
        """Test get_pgroupvolume with host PG and context API"""
        from plugins.modules.purefa_pgsnap import get_pgroupvolume

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "context": "",
            "restore": "vol1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock pgroup with host_count > 0
        mock_pgroup = Mock()
        mock_pgroup.host_count = 1
        mock_pgroup.host_group_count = 0
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pgroup]
        )

        # Mock hosts in protection group
        mock_host = Mock()
        mock_host.member = Mock()
        mock_host.member.name = "host1"
        mock_array.get_protection_groups_hosts.return_value = Mock(
            status_code=200, items=[mock_host]
        )

        # Mock volumes connected to host
        mock_connection = Mock()
        mock_connection.volume = Mock()
        mock_connection.volume.name = "vol1"
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_connection]
        )

        result = get_pgroupvolume(mock_module, mock_array)

        assert result == "vol1"
        mock_array.get_protection_groups.assert_called_once()
        mock_array.get_protection_groups_hosts.assert_called_once()
        mock_array.get_connections.assert_called_once()

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_get_pgroupvolume_hostgroup_pg_context_api(self, mock_lv):
        """Test get_pgroupvolume with hostgroup PG and context API"""
        from plugins.modules.purefa_pgsnap import get_pgroupvolume

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "context": "",
            "restore": "vol2",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock pgroup with host_group_count > 0
        mock_pgroup = Mock()
        mock_pgroup.host_count = 0
        mock_pgroup.host_group_count = 1
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pgroup]
        )

        # Mock hostgroups in protection group
        mock_hgroup = Mock()
        mock_hgroup.member = Mock()
        mock_hgroup.member.name = "hg1"
        mock_array.get_protection_groups_host_groups.return_value = Mock(
            status_code=200, items=[mock_hgroup]
        )

        # Mock volumes connected to hostgroup
        mock_connection = Mock()
        mock_connection.volume = Mock()
        mock_connection.volume.name = "vol2"
        mock_array.get_connections.return_value = Mock(
            status_code=200, items=[mock_connection]
        )

        # Mock hosts in hostgroup
        mock_hg_host = Mock()
        mock_hg_host.member = Mock()
        mock_hg_host.member.name = "host_in_hg"
        mock_array.get_host_groups_hosts.return_value = Mock(
            status_code=200, items=[mock_hg_host]
        )

        result = get_pgroupvolume(mock_module, mock_array)

        assert result == "vol2"

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_get_pgroupvolume_volume_pg_context_api(self, mock_lv):
        """Test get_pgroupvolume with volume PG and context API"""
        from plugins.modules.purefa_pgsnap import get_pgroupvolume

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "context": "",
            "restore": "vol3",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock pgroup with no hosts or hostgroups (volume PG)
        mock_pgroup = Mock()
        mock_pgroup.host_count = 0
        mock_pgroup.host_group_count = 0
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pgroup]
        )

        # Mock volumes in protection group
        mock_vol_entry = Mock()
        mock_vol_entry.member = Mock()
        mock_vol_entry.member.name = "vol3"
        mock_array.get_protection_groups_volumes.return_value = Mock(
            status_code=200, items=[mock_vol_entry]
        )

        result = get_pgroupvolume(mock_module, mock_array)

        assert result == "vol3"
        mock_array.get_protection_groups_volumes.assert_called_once()

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_get_pgroupvolume_volume_not_found(self, mock_lv):
        """Test get_pgroupvolume when volume is not found"""
        from plugins.modules.purefa_pgsnap import get_pgroupvolume

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "context": "",
            "restore": "nonexistent_vol",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock pgroup with no hosts or hostgroups (volume PG)
        mock_pgroup = Mock()
        mock_pgroup.host_count = 0
        mock_pgroup.host_group_count = 0
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pgroup]
        )

        # Mock volumes in protection group - different volume
        mock_vol_entry = Mock()
        mock_vol_entry.member = Mock()
        mock_vol_entry.member.name = "other_vol"
        mock_array.get_protection_groups_volumes.return_value = Mock(
            status_code=200, items=[mock_vol_entry]
        )

        result = get_pgroupvolume(mock_module, mock_array)

        assert result is None

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_get_pgroupvolume_exception_returns_none(self, mock_lv):
        """Test get_pgroupvolume returns None on exception"""
        from plugins.modules.purefa_pgsnap import get_pgroupvolume

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "context": "",
            "restore": "vol1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_protection_groups.side_effect = Exception("API error")

        result = get_pgroupvolume(mock_module, mock_array)

        assert result is None

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_get_pgroupvolume_pod_volume(self, mock_lv):
        """Test get_pgroupvolume with pod volume (:: in name)"""
        from plugins.modules.purefa_pgsnap import get_pgroupvolume

        mock_module = Mock()
        mock_module.params = {
            "name": "pod1::pg1",
            "context": "",
            "restore": "vol1",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock pgroup with no hosts or hostgroups (volume PG)
        mock_pgroup = Mock()
        mock_pgroup.host_count = 0
        mock_pgroup.host_group_count = 0
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pgroup]
        )

        # Mock volumes in protection group - pod volume
        mock_vol_entry = Mock()
        mock_vol_entry.member = Mock()
        mock_vol_entry.member.name = "pod1::vol1"
        mock_array.get_protection_groups_volumes.return_value = Mock(
            status_code=200, items=[mock_vol_entry]
        )

        result = get_pgroupvolume(mock_module, mock_array)

        assert result == "pod1::vol1"


class TestDeleteOffloadSnapshot:
    """Test cases for delete_offload_snapshot function"""

    @patch("plugins.modules.purefa_pgsnap._check_offload")
    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_replicated_pg(
        self, mock_lv, mock_check_response, mock_check_offload
    ):
        """Test delete_offload_snapshot for replicated PG"""
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "remote::pg1",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_check_offload.return_value = True

        # Remote snapshot exists and not destroyed
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_array.get_remote_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap]
        )
        mock_array.patch_remote_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        delete_offload_snapshot(mock_module, mock_array)

        mock_array.patch_remote_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap._check_offload")
    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_with_eradicate(
        self, mock_lv, mock_check_response, mock_check_offload
    ):
        """Test delete_offload_snapshot with eradication"""
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "remote::pg1",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
            "eradicate": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_check_offload.return_value = True

        # Remote snapshot exists and not destroyed
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_array.get_remote_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap]
        )
        mock_array.patch_remote_protection_group_snapshots.return_value = Mock(
            status_code=200
        )
        mock_array.delete_remote_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        delete_offload_snapshot(mock_module, mock_array)

        mock_array.delete_remote_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap._check_offload")
    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_already_destroyed_with_eradicate(
        self, mock_lv, mock_check_response, mock_check_offload
    ):
        """Test delete_offload_snapshot when already destroyed and eradicate requested"""
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "remote::pg1",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
            "eradicate": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_check_offload.return_value = True

        # Remote snapshot exists but already destroyed
        mock_snap = Mock()
        mock_snap.destroyed = True
        mock_array.get_remote_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap]
        )
        mock_array.delete_remote_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        delete_offload_snapshot(mock_module, mock_array)

        mock_array.delete_remote_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap._check_offload")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_offload_not_connected(
        self, mock_lv, mock_check_offload
    ):
        """Test delete_offload_snapshot when offload is not connected"""
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "remote::pg1",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_check_offload.return_value = False

        delete_offload_snapshot(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "does not exist or not connected" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_invalid_name_format(self, mock_lv):
        """Test delete_offload_snapshot with invalid PG name format"""
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",  # No colon - invalid for offload
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
            "eradicate": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        delete_offload_snapshot(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "not in the correct format" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pgsnap._check_offload")
    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_offload_snapshot_legacy_api(
        self, mock_lv, mock_check_response, mock_check_offload
    ):
        """Test delete_offload_snapshot with legacy API version"""
        from plugins.modules.purefa_pgsnap import delete_offload_snapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "remote::pg1",
            "suffix": "snap1",
            "offload": "nfs-target",
            "context": "",
            "eradicate": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Legacy version
        mock_check_offload.return_value = True

        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_array.get_remote_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap]
        )
        mock_array.patch_remote_protection_group_snapshots.return_value = Mock(
            status_code=200
        )
        mock_array.delete_remote_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        delete_offload_snapshot(mock_module, mock_array)

        # Verify called without context_names
        mock_array.get_remote_protection_group_snapshots.assert_called_once()
        call_kwargs = mock_array.get_remote_protection_group_snapshots.call_args[1]
        assert "context_names" not in call_kwargs


class TestCheckOffloadContext:
    """Test _check_offload with context API version"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_check_offload_with_context(self, mock_lv):
        """Test _check_offload uses context for newer API"""
        mock_module = Mock()
        mock_module.params = {"offload": "nfs-target", "context": "test-context"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_offload = Mock()
        mock_offload.status = "connected"
        mock_array.get_offloads.return_value = Mock(
            status_code=200, items=[mock_offload]
        )

        result = _check_offload(mock_module, mock_array)

        assert result is True
        mock_array.get_offloads.assert_called_once()
        call_kwargs = mock_array.get_offloads.call_args[1]
        assert call_kwargs.get("context_names") == ["test-context"]


class TestDeletePgsnapshot:
    """Test delete_pgsnapshot function"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_pgsnapshot_with_eradicate(self, mock_lv, mock_check_response):
        """Test delete_pgsnapshot with immediate eradication"""
        from plugins.modules.purefa_pgsnap import delete_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
            "eradicate": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_protection_group_snapshots.return_value = Mock(status_code=200)
        mock_array.delete_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        delete_pgsnapshot(mock_module, mock_array)

        mock_array.patch_protection_group_snapshots.assert_called_once()
        mock_array.delete_protection_group_snapshots.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_delete_pgsnapshot_legacy_api_with_eradicate(
        self, mock_lv, mock_check_response
    ):
        """Test delete_pgsnapshot with legacy API"""
        from plugins.modules.purefa_pgsnap import delete_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
            "eradicate": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Legacy
        mock_array.patch_protection_group_snapshots.return_value = Mock(status_code=200)
        mock_array.delete_protection_group_snapshots.return_value = Mock(
            status_code=200
        )

        delete_pgsnapshot(mock_module, mock_array)

        # Verify called without context_names for legacy API
        call_kwargs = mock_array.patch_protection_group_snapshots.call_args[1]
        assert "context_names" not in call_kwargs


class TestRestorePgsnapvolume:
    """Test restore_pgsnapvolume function"""

    @patch("plugins.modules.purefa_pgsnap.get_pgroupvolume")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.get_rpgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_restore_pgsnapvolume_stretched_pod_fails(
        self, mock_lv, mock_get_rpgsnapshot, mock_get_pgsnapshot, mock_get_pgroupvolume
    ):
        """Test restore to stretched pod fails"""
        from plugins.modules.purefa_pgsnap import restore_pgsnapvolume

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
            "restore": "vol1",
            "target": "stretched-pod::vol1",
            "overwrite": False,
            "add_to_pgs": None,
            "with_default_protection": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_pgsnapshot.return_value = Mock()
        mock_get_pgroupvolume.return_value = "vol1"

        # Mock stretched pod (array_count > 1)
        mock_pod = Mock()
        mock_pod.array_count = 2  # Stretched
        mock_array.get_pods.return_value = Mock(status_code=200, items=[mock_pod])

        restore_pgsnapvolume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "cannot be restored to a stretched pod" in str(
            mock_module.fail_json.call_args
        )

    @patch("plugins.modules.purefa_pgsnap.get_pgroupvolume")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_restore_pgsnapvolume_with_add_to_pgs(
        self, mock_lv, mock_get_pgsnapshot, mock_get_pgroupvolume
    ):
        """Test restore with add_to_pgs parameter"""
        from plugins.modules.purefa_pgsnap import restore_pgsnapvolume

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
            "restore": "vol1",
            "target": "restored_vol",
            "overwrite": False,
            "add_to_pgs": ["pg2", "pg3"],
            "with_default_protection": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_pgsnapshot.return_value = Mock()
        mock_get_pgroupvolume.return_value = "vol1"
        mock_array.post_volumes.return_value = Mock(status_code=200)

        restore_pgsnapvolume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert "add_to_protection_groups" in call_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.get_pgroupvolume")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_restore_pgsnapvolume_with_overwrite_context(
        self, mock_lv, mock_get_pgsnapshot, mock_get_pgroupvolume
    ):
        """Test restore with overwrite and context"""
        from plugins.modules.purefa_pgsnap import restore_pgsnapvolume

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "test-context",
            "restore": "vol1",
            "target": "vol1",
            "overwrite": True,
            "add_to_pgs": None,
            "with_default_protection": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_pgsnapshot.return_value = Mock()
        mock_get_pgroupvolume.return_value = "vol1"
        mock_array.post_volumes.return_value = Mock(status_code=200)

        restore_pgsnapvolume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert call_kwargs.get("context_names") == ["test-context"]
        assert call_kwargs.get("overwrite") is True

    @patch("plugins.modules.purefa_pgsnap.get_pgroupvolume")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_restore_pgsnapvolume_legacy_api_no_overwrite(
        self, mock_lv, mock_get_pgsnapshot, mock_get_pgroupvolume
    ):
        """Test restore with legacy API and no overwrite"""
        from plugins.modules.purefa_pgsnap import restore_pgsnapvolume

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
            "restore": "vol1",
            "target": "restored_vol",
            "overwrite": False,
            "add_to_pgs": None,
            "with_default_protection": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_pgsnapshot.return_value = Mock()
        mock_get_pgroupvolume.return_value = "vol1"
        mock_array.post_volumes.return_value = Mock(status_code=200)

        restore_pgsnapvolume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert call_kwargs.get("overwrite") is False


class TestCreatePgsnapshot:
    """Test create_pgsnapshot function additional branches"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_create_pgsnapshot_with_throttle_and_now(
        self, mock_lv, mock_check_response
    ):
        """Test create_pgsnapshot with throttle and now options"""
        from plugins.modules.purefa_pgsnap import create_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
            "throttle": True,
            "now": True,
            "apply_retention": True,
            "remote": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock remote target check
        mock_pg = Mock()
        mock_pg.target_count = 1  # Has remote target
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        # Mock proper response with snap_data
        mock_snap_data = Mock()
        mock_snap_data.suffix = "snap1"
        mock_array.post_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap_data]
        )

        create_pgsnapshot(mock_module, mock_array)

        mock_array.post_protection_group_snapshots.assert_called_once()
        call_kwargs = mock_array.post_protection_group_snapshots.call_args[1]
        assert call_kwargs.get("replicate_now") is True
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_create_pgsnapshot_no_remote_target_with_context(
        self, mock_lv, mock_check_response
    ):
        """Test create_pgsnapshot with no remote target using context"""
        from plugins.modules.purefa_pgsnap import create_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "test-context",
            "throttle": True,
            "now": False,
            "apply_retention": True,
            "remote": False,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Mock no remote target
        mock_pg = Mock()
        mock_pg.target_count = 0
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_snap_data = Mock()
        mock_snap_data.suffix = "snap1"
        mock_array.post_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap_data]
        )

        create_pgsnapshot(mock_module, mock_array)

        call_kwargs = mock_array.post_protection_group_snapshots.call_args[1]
        assert call_kwargs.get("context_names") == ["test-context"]

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    def test_create_pgsnapshot_legacy_api_with_remote(
        self, mock_lv, mock_check_response
    ):
        """Test create_pgsnapshot with legacy API and remote replication"""
        from plugins.modules.purefa_pgsnap import create_pgsnapshot

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "context": "",
            "throttle": True,
            "now": False,
            "apply_retention": True,
            "remote": True,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.30"  # Legacy

        # Mock remote target
        mock_pg = Mock()
        mock_pg.target_count = 1
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=[mock_pg]
        )
        mock_snap_data = Mock()
        mock_snap_data.suffix = "snap1"
        mock_array.post_protection_group_snapshots.return_value = Mock(
            status_code=200, items=[mock_snap_data]
        )

        create_pgsnapshot(mock_module, mock_array)

        call_kwargs = mock_array.post_protection_group_snapshots.call_args[1]
        assert call_kwargs.get("replicate") is True
        assert "context_names" not in call_kwargs


class TestMain:
    """Test main function branches"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_pgroup_not_found(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main fails when protection group doesn't exist"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "nonexistent_pg",
            "suffix": "snap1",
            "state": "present",
            "offload": None,
            "restore": None,
            "target": None,
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = False

        main()

        mock_module.fail_json.assert_called_once()
        assert "does not exist" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_offload_not_supported_for_present(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main fails when offload used with state=present"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "present",
            "offload": "nfs-target",
            "restore": None,
            "target": None,
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_get_pgsnapshot.return_value = None

        main()

        mock_module.fail_json.assert_called_once()
        assert "offload parameter not supported" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.restore_pgsnapvolume")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_copy_with_overwrite_and_add_to_pgs_fails(
        self,
        mock_ansible,
        mock_restore,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main fails when copy with overwrite and add_to_pgs"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "copy",
            "offload": None,
            "restore": "vol1",
            "target": "restored_vol",
            "context": "",
            "overwrite": True,
            "add_to_pgs": ["pg2"],
            "with_default_protection": True,
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_get_pgsnapshot.return_value = None

        main()

        mock_module.fail_json.assert_called_once()
        assert "overwrite and add_to_pgs" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_present_snapshot_exists_no_change(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main exits unchanged when snapshot already exists"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "present",
            "offload": None,
            "restore": None,
            "target": None,
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_get_pgsnapshot.return_value = mock_snap

        main()

        mock_module.exit_json.assert_called_with(changed=False)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_absent_snapshot_not_exists_no_change(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main exits unchanged when absent and snapshot doesn't exist"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "absent",
            "offload": None,
            "restore": None,
            "target": None,
            "context": "",
            "eradicate": False,
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_get_pgsnapshot.return_value = None

        main()

        mock_module.exit_json.assert_called_with(changed=False)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.update_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_rename_calls_update(
        self,
        mock_ansible,
        mock_update,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main calls update_pgsnapshot for rename state"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "rename",
            "offload": None,
            "restore": None,
            "target": "newsnap",
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_get_pgsnapshot.return_value = mock_snap

        main()

        mock_update.assert_called_once()

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.delete_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_absent_calls_delete(
        self,
        mock_ansible,
        mock_delete,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main calls delete_pgsnapshot for absent state"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "absent",
            "offload": None,
            "restore": None,
            "target": None,
            "context": "",
            "eradicate": False,
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_get_pgsnapshot.return_value = mock_snap

        main()

        mock_delete.assert_called_once()

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.eradicate_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_absent_destroyed_eradicate_calls_eradicate(
        self,
        mock_ansible,
        mock_eradicate,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main calls eradicate_pgsnapshot for destroyed snapshot with eradicate"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "absent",
            "offload": None,
            "restore": None,
            "target": None,
            "context": "",
            "eradicate": True,
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = True
        mock_get_pgsnapshot.return_value = mock_snap

        main()

        mock_eradicate.assert_called_once()

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.delete_offload_snapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_absent_with_offload_calls_delete_offload(
        self,
        mock_ansible,
        mock_delete_offload,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main calls delete_offload_snapshot for absent with offload"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "absent",
            "offload": "nfs-target",
            "restore": None,
            "target": None,
            "context": "",
            "eradicate": False,
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_get_pgsnapshot.return_value = mock_snap

        main()

        mock_delete_offload.assert_called_once()

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_suffix_validation_fails(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main fails on invalid suffix name"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "!invalid",  # Invalid suffix - starts with special char
            "state": "present",
            "offload": None,
            "restore": None,
            "target": None,
            "context": "",
        }
        # Make fail_json raise SystemExit to stop execution
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_get_array.return_value = Mock()
        mock_get_pgroup.return_value = True
        mock_get_pgsnapshot.return_value = None

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        assert "does not conform to suffix name rules" in str(
            mock_module.fail_json.call_args
        )

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_rename_target_validation_fails(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_lv,
    ):
        """Test main fails on invalid rename target"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "rename",
            "offload": None,
            "restore": None,
            "target": "123!invalid",  # Invalid target
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_get_pgsnapshot.return_value = mock_snap

        main()

        mock_module.fail_json.assert_called_once()
        assert "does not conform to suffix name rules" in str(
            mock_module.fail_json.call_args
        )


class TestRestorePgsnapshotAll:
    """Tests for restore_pgsnapshot_all function"""

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_restore_all_to_new_pgroup(self, mock_loose, mock_check):
        """Test restore all volumes to a new protection group"""
        mock_loose.side_effect = LooseVersion

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "target": "pg1_clone",
            "overwrite": False,
            "context": "",
        }
        mock_module.check_mode = False

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Target doesn't exist
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=iter([])
        )
        mock_array.post_protection_groups.return_value = Mock(status_code=200)

        restore_pgsnapshot_all(mock_module, mock_array)

        # Empty context is omitted by the get_with_context helper (#1005 fix)
        mock_array.post_protection_groups.assert_called_once_with(
            names=["pg1_clone"],
            source_names=["pg1.snap1"],
            overwrite=False,
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_restore_all_overwrite_existing(self, mock_loose, mock_check):
        """Test restore all volumes overwriting existing protection group"""
        mock_loose.side_effect = LooseVersion

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "target": None,  # Defaults to source pg name
            "overwrite": True,
            "context": "",
        }
        mock_module.check_mode = False

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Target exists
        mock_pgroup = Mock()
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=iter([mock_pgroup])
        )
        mock_array.post_protection_groups.return_value = Mock(status_code=200)

        restore_pgsnapshot_all(mock_module, mock_array)

        # Empty context is omitted by the get_with_context helper (#1005 fix)
        mock_array.post_protection_groups.assert_called_once_with(
            names=["pg1"],
            source_names=["pg1.snap1"],
            overwrite=True,
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_restore_all_existing_without_overwrite_fails(self, mock_loose):
        """Test restore all fails when target exists and overwrite=False"""
        mock_loose.side_effect = LooseVersion

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "target": None,
            "overwrite": False,
            "context": "",
        }
        mock_module.check_mode = False

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Target exists
        mock_pgroup = Mock()
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=iter([mock_pgroup])
        )

        restore_pgsnapshot_all(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "overwrite must be True" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_restore_all_with_latest_suffix(self, mock_loose, mock_check):
        """Test restore all with 'latest' suffix resolves to actual suffix"""
        mock_loose.side_effect = LooseVersion

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "latest",
            "target": "pg1_clone",
            "overwrite": False,
            "context": "",
        }
        mock_module.check_mode = False

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Latest snapshot
        mock_snap = Mock()
        mock_snap.suffix = "snap-actual"
        mock_array.get_protection_group_snapshots.return_value = Mock(
            items=iter([mock_snap])
        )
        # Target doesn't exist
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=iter([])
        )
        mock_array.post_protection_groups.return_value = Mock(status_code=200)

        restore_pgsnapshot_all(mock_module, mock_array)

        # Should use the resolved suffix; empty context omitted by helper (#1005 fix)
        mock_array.post_protection_groups.assert_called_once_with(
            names=["pg1_clone"],
            source_names=["pg1.snap-actual"],
            overwrite=False,
        )

    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_restore_all_check_mode(self, mock_loose):
        """Test restore all in check mode doesn't make API calls"""
        mock_loose.side_effect = LooseVersion

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "target": "pg1_clone",
            "overwrite": False,
            "context": "",
        }
        mock_module.check_mode = True

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Target doesn't exist
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=iter([])
        )

        restore_pgsnapshot_all(mock_module, mock_array)

        mock_array.post_protection_groups.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_pgsnap.check_response")
    @patch("plugins.modules.purefa_pgsnap.LooseVersion")
    def test_restore_all_older_api_version(self, mock_loose, mock_check):
        """Test restore all with older API version (no context support)"""
        mock_loose.side_effect = LooseVersion

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "target": "pg1_clone",
            "overwrite": False,
            "context": "",
        }
        mock_module.check_mode = False

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Older version
        # Target doesn't exist
        mock_array.get_protection_groups.return_value = Mock(
            status_code=200, items=iter([])
        )
        mock_array.post_protection_groups.return_value = Mock(status_code=200)

        restore_pgsnapshot_all(mock_module, mock_array)

        # Should not include context_names
        mock_array.post_protection_groups.assert_called_once_with(
            names=["pg1_clone"],
            source_names=["pg1.snap1"],
            overwrite=False,
        )


class TestMainRestoreAll:
    """Tests for main() function with restore=all"""

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.restore_pgsnapshot_all")
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_restore_all_calls_restore_pgsnapshot_all(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_restore_all,
        mock_lv,
    ):
        """Test main() calls restore_pgsnapshot_all when restore=all"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "copy",
            "restore": "all",
            "target": None,
            "offload": None,
            "overwrite": True,
            "add_to_pgs": None,
            "with_default_protection": True,
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_get_pgsnapshot.return_value = mock_snap

        main()

        mock_restore_all.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.restore_pgsnapshot_all")
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_restore_all_fails_with_add_to_pgs(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_restore_all,
        mock_lv,
    ):
        """Test main() fails when restore=all with add_to_pgs"""
        import pytest
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "copy",
            "restore": "all",
            "target": None,
            "offload": None,
            "overwrite": True,
            "add_to_pgs": ["pg2"],  # Not supported with restore=all
            "with_default_protection": True,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_get_pgsnapshot.return_value = mock_snap

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "not supported when restore=all" in str(mock_module.fail_json.call_args)
        mock_restore_all.assert_not_called()

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.restore_pgsnapshot_all")
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_restore_all_fails_with_default_protection_false(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_restore_all,
        mock_lv,
    ):
        """Test main() fails when restore=all with with_default_protection=False"""
        import pytest
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "copy",
            "restore": "all",
            "target": None,
            "offload": None,
            "overwrite": True,
            "add_to_pgs": None,
            "with_default_protection": False,  # Not supported with restore=all
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_get_pgsnapshot.return_value = mock_snap

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
        assert "not supported when restore=all" in str(mock_module.fail_json.call_args)
        mock_restore_all.assert_not_called()

    @patch("plugins.modules.purefa_pgsnap.LooseVersion", side_effect=LooseVersion)
    @patch("plugins.modules.purefa_pgsnap.restore_pgsnapshot_all")
    @patch("plugins.modules.purefa_pgsnap.get_array")
    @patch("plugins.modules.purefa_pgsnap.get_pgroup")
    @patch("plugins.modules.purefa_pgsnap.get_pgsnapshot")
    @patch("plugins.modules.purefa_pgsnap.AnsibleModule")
    def test_main_restore_all_target_not_defaulted_to_all(
        self,
        mock_ansible,
        mock_get_pgsnapshot,
        mock_get_pgroup,
        mock_get_array,
        mock_restore_all,
        mock_lv,
    ):
        """Test that target doesn't default to 'all' when restore=all"""
        from plugins.modules.purefa_pgsnap import main

        mock_module = Mock()
        mock_module.params = {
            "name": "pg1",
            "suffix": "snap1",
            "state": "copy",
            "restore": "all",
            "target": None,  # Should stay None, not become "all"
            "offload": None,
            "overwrite": True,
            "add_to_pgs": None,
            "with_default_protection": True,
            "context": "",
        }
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array.get_arrays.return_value = Mock(items=iter([mock_array_info]))
        mock_get_array.return_value = mock_array
        mock_get_pgroup.return_value = True
        mock_snap = Mock()
        mock_snap.destroyed = False
        mock_get_pgsnapshot.return_value = mock_snap

        main()

        # Verify target was not changed to "all"
        assert mock_module.params["target"] is None
        mock_restore_all.assert_called_once()
