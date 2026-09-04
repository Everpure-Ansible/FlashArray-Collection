# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_volume module."""

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


def _ctx_delegate(client, method_name, context_version, module, **kwargs):
    """Stand-in for the *_with_context helpers used during migration.

    Mirrors the real helper: call the array method, adding context_names only
    when the API version supports it and a context is set. This lets the
    existing array-method-based assertions continue to work.
    """
    api_version = client.get_rest_version()
    if LooseVersion(context_version) <= LooseVersion(api_version) and module.params.get(
        "context"
    ):
        kwargs["context_names"] = [module.params["context"]]
    return getattr(client, method_name)(**kwargs)


_api_helpers_mock = sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
]
for _helper_name in (
    "get_with_context",
    "post_with_context",
    "patch_with_context",
    "delete_with_context",
):
    getattr(_api_helpers_mock, _helper_name).side_effect = _ctx_delegate

from plugins.modules.purefa_volume import (
    main,
    get_volume,
    get_destroyed_volume,
    get_target,
    create_volume,
    create_multi_volume,
    update_volume,
    delete_volume,
    eradicate_volume,
    recover_volume,
    copy_from_volume,
    rename_volume,
    _create_nguid,
    _volfact,
    move_volume,
    get_pod,
    check_pod,
    check_vgroup,
    get_multi_volumes,
    get_endpoint,
    get_pending_pgroup,
    get_pgroup,
    pg_exists,
)


class TestCreateNguid:
    """Test cases for _create_nguid helper function"""

    def test_create_nguid_valid_serial(self):
        """Test NGUID creation from valid serial"""
        serial = "361019ecace43d83000120a4"
        result = _create_nguid(serial)
        assert result.startswith("eui.00")
        assert "24a937" in result

    def test_create_nguid_format(self):
        """Test NGUID format is correct"""
        serial = "abcdef12345678901234"
        result = _create_nguid(serial)
        # Should be: eui.00 + first 14 chars + 24a937 + last 10 chars
        # serial[0:14] = "abcdef12345678"
        # serial[-10:] = "5678901234"
        assert result == "eui.00abcdef1234567824a9375678901234"


class TestGetVolume:
    """Test cases for get_volume function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_volume_exists(self, mock_loose_version):
        """Test get_volume returns volume when it exists"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {"name": "test_volume", "context": "array1"}

        mock_volume = Mock()
        mock_volume.name = "test_volume"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_volume]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_response

        result = get_volume(mock_module, mock_array)

        assert result == mock_volume
        mock_array.get_volumes.assert_called_once()

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_volume_not_exists(self, mock_loose_version):
        """Test get_volume returns None when volume doesn't exist"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent_volume", "context": "array1"}

        mock_response = Mock()
        mock_response.status_code = 400

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_response

        result = get_volume(mock_module, mock_array)

        assert result is None


class TestGetDestroyedVolume:
    """Test cases for get_destroyed_volume function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_destroyed_volume_exists(self, mock_loose_version):
        """Test get_destroyed_volume returns destroyed volume"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {"name": "deleted_volume", "context": "array1"}

        mock_volume = Mock()
        mock_volume.destroyed = True
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_volume]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_response

        result = get_destroyed_volume(mock_module, mock_array)

        assert result == mock_volume
        mock_array.get_volumes.assert_called_once()


class TestGetTarget:
    """Test cases for get_target function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_target_exists(self, mock_loose_version):
        """Test get_target returns target volume"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {"target": "target_volume", "context": "array1"}

        mock_volume = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_volume]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_response

        result = get_target(mock_module, mock_array)

        assert result == mock_volume


class TestCreateVolume:
    """Test cases for create_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_vgroup")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    def test_create_volume_basic(
        self,
        mock_volume_post,
        mock_loose_version,
        mock_check_pod,
        mock_check_vgroup,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test basic volume creation without QoS"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_check_vgroup.return_value = True
        mock_check_pod.return_value = True
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "pgroup": None,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = mock_response

        create_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_create_volume_missing_size(self, mock_loose_version):
        """Test volume creation fails without size"""
        mock_loose_version.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        try:
            create_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "Size for a new volume must be specified" in call_args["msg"]

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_check_mode(
        self,
        mock_qos,
        mock_volume_post,
        mock_loose_version,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test volume creation in check mode"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "pgroup": None,
            "context": "array1",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        create_volume(mock_module, mock_array)

        # In check mode, post_volumes should NOT be called
        mock_array.post_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_with_bw_qos_only(
        self,
        mock_qos,
        mock_volume_post,
        mock_loose_version,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test volume creation with bandwidth QoS only"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": "100M",  # 100MB bandwidth limit
            "iops_qos": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "pgroup": None,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = mock_response

        create_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_qos.assert_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_with_iops_qos_only(
        self,
        mock_qos,
        mock_volume_post,
        mock_loose_version,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test volume creation with IOPS QoS only"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": "100000",  # IOPS limit as integer string
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "pgroup": None,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = mock_response

        create_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_qos.assert_called()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.human_to_real")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_with_both_qos(
        self,
        mock_qos,
        mock_volume_post,
        mock_loose_version,
        mock_human_to_real,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test volume creation with both bandwidth and IOPS QoS"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_human_to_real.return_value = 100000  # 100K IOPS
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": "100M",  # 100MB bandwidth limit
            "iops_qos": "100K",  # 100K IOPS limit
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "pgroup": None,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = mock_response

        create_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_qos.assert_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True


class TestUpdateVolume:
    """Test cases for update_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_update_volume_size_increase(
        self,
        mock_volume_patch,
        mock_loose_version,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test volume size increase"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 2147483648  # 2GB
        mock_volfact.return_value = {"test_volume": {"size": 2147483648}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "2G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "pgroup": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "array1",
        }

        # Mock existing volume with 1GB
        mock_vol = Mock()
        mock_vol.provisioned = 1073741824  # 1GB
        mock_qos = Mock(spec=[])
        mock_vol.qos = mock_qos

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.items = [mock_vol]

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_get_response
        mock_array.patch_volumes.return_value = mock_patch_response

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True


class TestDeleteVolume:
    """Test cases for delete_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_delete_volume_success(
        self,
        mock_volume_patch,
        mock_loose_version,
        mock_check_response,
        mock_volfact,
    ):
        """Test successful volume deletion"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {"test_volume": {"destroyed": True}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "add_to_pgs": None,
            "eradicate": False,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volumes.return_value = mock_response

        delete_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_delete_volume_check_mode(
        self,
        mock_volume_patch,
        mock_loose_version,
        mock_volfact,
    ):
        """Test volume deletion in check mode"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test_volume",
            "add_to_pgs": None,
            "eradicate": False,
            "context": "array1",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        delete_volume(mock_module, mock_array)

        # In check mode, patch_volumes should NOT be called
        mock_array.patch_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()


class TestEradicateVolume:
    """Test cases for eradicate_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_eradicate_volume_success(
        self,
        mock_loose_version,
        mock_check_response,
        mock_volfact,
    ):
        """Test successful volume eradication"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = []

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "eradicate": True,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.delete_volumes.return_value = mock_response

        eradicate_volume(mock_module, mock_array)

        mock_array.delete_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_eradicate_volume_no_eradicate_flag(
        self,
        mock_loose_version,
        mock_volfact,
    ):
        """Test eradicate_volume when eradicate flag is False"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {"test_volume": {"destroyed": True}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "eradicate": False,
            "context": "array1",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        eradicate_volume(mock_module, mock_array)

        # Should not call delete_volumes when eradicate is False
        mock_array.delete_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False


class TestRecoverVolume:
    """Test cases for recover_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_recover_volume_success(
        self,
        mock_volume_patch,
        mock_loose_version,
        mock_check_response,
        mock_volfact,
    ):
        """Test successful volume recovery"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {"test_volume": {"destroyed": False}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volumes.return_value = mock_response

        recover_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_recover_volume_check_mode(
        self,
        mock_volume_patch,
        mock_loose_version,
        mock_volfact,
    ):
        """Test volume recovery in check mode"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test_volume",
            "context": "array1",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        recover_volume(mock_module, mock_array)

        # In check mode, patch_volumes should NOT be called
        mock_array.patch_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True


class TestCopyFromVolume:
    """Test cases for copy_from_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_target")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_copy_volume_success(
        self,
        mock_reference,
        mock_volume_post,
        mock_loose_version,
        mock_get_target,
        mock_check_response,
        mock_volfact,
    ):
        """Test successful volume copy"""
        mock_loose_version.side_effect = float
        mock_get_target.return_value = None  # Target doesn't exist
        mock_volfact.return_value = {"target_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source_volume",
            "target": "target_volume",
            "overwrite": False,
            "add_to_pgs": None,
            "with_default_protection": True,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = mock_response

        copy_from_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()


class TestRenameVolume:
    """Test cases for rename_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_rename_volume_success(
        self,
        mock_volume_patch,
        mock_loose_version,
        mock_check_response,
        mock_volfact,
    ):
        """Test successful volume rename"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {"new_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old_volume",
            "rename": "new_volume",
            "context": "array1",
        }

        # Mock target doesn't exist check
        mock_get_response = Mock()
        mock_get_response.status_code = 400
        mock_patch_response = Mock()
        mock_patch_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_get_response
        mock_array.patch_volumes.return_value = mock_patch_response

        rename_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_rename_volume_target_exists(self, mock_loose_version):
        """Test rename fails when target exists"""
        mock_loose_version.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old_volume",
            "rename": "existing_volume",
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_response = Mock()
        mock_response.status_code = 200  # Target exists

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_response

        try:
            rename_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "already exists" in call_args["msg"]


class TestMain:
    """Test cases for main function"""

    @patch("plugins.modules.purefa_volume.get_array")
    @patch("plugins.modules.purefa_volume.AnsibleModule")
    @patch("plugins.modules.purefa_volume.HAS_PURESTORAGE", False)
    def test_main_missing_sdk(self, mock_ansible_module, mock_get_array):
        """Test main when pypureclient SDK is missing"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test_volume",
            "state": "present",
            "size": "1G",
            "target": None,
            "move": None,
            "rename": None,
            "eradicate": False,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "count": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        # Mock get_volume and get_endpoint
        with patch("plugins.modules.purefa_volume.get_volume") as mock_get_vol:
            with patch("plugins.modules.purefa_volume.get_endpoint") as mock_get_ep:
                mock_get_vol.return_value = None
                mock_get_ep.return_value = None

                try:
                    main()
                except SystemExit:
                    pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "py-pure-client sdk is required" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.get_volume")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.get_array")
    @patch("plugins.modules.purefa_volume.AnsibleModule")
    @patch("plugins.modules.purefa_volume.HAS_PURESTORAGE", True)
    def test_main_volume_is_endpoint(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_get_volume,
        mock_get_endpoint,
    ):
        """Test main fails when volume is a protocol endpoint"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {
            "name": "endpoint_volume",
            "state": "present",
            "size": "1G",
            "target": None,
            "move": None,
            "rename": None,
            "eradicate": False,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "count": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_item = Mock()
        mock_array_item.name = "array1"
        mock_arrays_response = Mock()
        mock_arrays_response.items = [mock_array_item]
        mock_array.get_arrays.return_value = mock_arrays_response
        mock_get_array.return_value = mock_array

        mock_get_volume.return_value = None
        mock_endpoint = Mock()
        mock_endpoint.subtype = "protocol_endpoint"
        mock_get_endpoint.return_value = mock_endpoint

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "is an endpoint" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.get_volume")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.get_array")
    @patch("plugins.modules.purefa_volume.AnsibleModule")
    @patch("plugins.modules.purefa_volume.HAS_PURESTORAGE", True)
    def test_main_bw_qos_out_of_range(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_get_volume,
        mock_get_endpoint,
        mock_human_to_bytes,
    ):
        """Test main fails when bandwidth QoS is out of range"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 100  # Too low

        mock_module = Mock()
        mock_module.params = {
            "name": "test_volume",
            "state": "present",
            "size": "1G",
            "target": None,
            "move": None,
            "rename": None,
            "eradicate": False,
            "bw_qos": "100B",  # Too low
            "iops_qos": None,
            "pgroup": None,
            "count": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_item = Mock()
        mock_array_item.name = "array1"
        mock_arrays_response = Mock()
        mock_arrays_response.items = [mock_array_item]
        mock_array.get_arrays.return_value = mock_arrays_response
        mock_get_array.return_value = mock_array

        mock_get_volume.return_value = None
        mock_get_endpoint.return_value = None

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "Bandwidth QoS value out of range" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.human_to_real")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.get_volume")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.get_array")
    @patch("plugins.modules.purefa_volume.AnsibleModule")
    @patch("plugins.modules.purefa_volume.HAS_PURESTORAGE", True)
    def test_main_iops_qos_out_of_range(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_loose_version,
        mock_get_volume,
        mock_get_endpoint,
        mock_human_to_bytes,
        mock_human_to_real,
    ):
        """Test main fails when IOPs QoS is out of range"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 0
        mock_human_to_real.return_value = 10  # Too low (min is 100)

        mock_module = Mock()
        mock_module.params = {
            "name": "test_volume",
            "state": "present",
            "size": "1G",
            "target": None,
            "move": None,
            "rename": None,
            "eradicate": False,
            "bw_qos": None,
            "iops_qos": "10",  # Too low
            "pgroup": None,
            "count": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_item = Mock()
        mock_array_item.name = "array1"
        mock_arrays_response = Mock()
        mock_arrays_response.items = [mock_array_item]
        mock_array.get_arrays.return_value = mock_arrays_response
        mock_get_array.return_value = mock_array

        mock_get_volume.return_value = None
        mock_get_endpoint.return_value = None

        try:
            main()
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "IOPs QoS value out of range" in call_args["msg"]


class TestCreateMultiVolume:
    """Test cases for create_multi_volume function"""

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_vgroup")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    def test_create_multi_volume_basic(
        self,
        mock_volume_post,
        mock_loose_version,
        mock_check_pod,
        mock_check_vgroup,
        mock_human_to_bytes,
        mock_check_response,
    ):
        """Test basic multi-volume creation with count, start, digits, suffix"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_check_vgroup.return_value = True
        mock_check_pod.return_value = True

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vol",
            "size": "1G",
            "count": 5,
            "start": 0,
            "digits": 2,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
            "with_default_protection": True,
            "context": "",
        }

        mock_vol_post = Mock()
        mock_volume_post.return_value = mock_vol_post

        # Create mock volume items for the response
        mock_vol_items = []
        for i in range(5):
            mock_item = Mock()
            mock_item.name = f"vol0{i}"
            mock_item.provisioned = 1073741824
            mock_item.serial = f"SERIAL000{i}"
            mock_item.created = 1700000000000
            mock_vol_items.append(mock_item)

        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.items = mock_vol_items

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_item = Mock()
        mock_array_item.name = "array1"
        mock_arrays_response = Mock()
        mock_arrays_response.items = [mock_array_item]
        mock_array.get_arrays.return_value = mock_arrays_response
        mock_array.post_volumes.return_value = mock_post_response

        create_multi_volume(mock_module, mock_array)

        # Verify post_volumes was called with correct names
        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        # Volume names should be vol00, vol01, vol02, vol03, vol04
        expected_names = ["vol00", "vol01", "vol02", "vol03", "vol04"]
        assert call_kwargs["names"] == expected_names
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_vgroup")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    def test_create_multi_volume_with_suffix(
        self,
        mock_volume_post,
        mock_loose_version,
        mock_check_pod,
        mock_check_vgroup,
        mock_human_to_bytes,
        mock_check_response,
    ):
        """Test multi-volume creation with custom suffix and start"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 2147483648  # 2GB
        mock_check_vgroup.return_value = True
        mock_check_pod.return_value = True

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "data",
            "size": "2G",
            "count": 3,
            "start": 10,
            "digits": 3,
            "suffix": "_disk",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
            "with_default_protection": True,
            "context": "",
        }

        mock_vol_post = Mock()
        mock_volume_post.return_value = mock_vol_post

        # Create mock volume items for the response
        mock_vol_items = []
        for i, name in enumerate(["data010_disk", "data011_disk", "data012_disk"]):
            mock_item = Mock()
            mock_item.name = name
            mock_item.provisioned = 2147483648
            mock_item.serial = f"SERIAL001{i}"
            mock_item.created = 1700000000000
            mock_vol_items.append(mock_item)

        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.items = mock_vol_items

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array_item = Mock()
        mock_array_item.name = "array1"
        mock_arrays_response = Mock()
        mock_arrays_response.items = [mock_array_item]
        mock_array.get_arrays.return_value = mock_arrays_response
        mock_array.post_volumes.return_value = mock_post_response

        create_multi_volume(mock_module, mock_array)

        # Verify post_volumes was called with correct names
        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        # Volume names should be data010_disk, data011_disk, data012_disk
        expected_names = ["data010_disk", "data011_disk", "data012_disk"]
        assert call_kwargs["names"] == expected_names
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_vgroup")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    def test_create_multi_volume_check_mode(
        self,
        mock_volume_post,
        mock_loose_version,
        mock_check_pod,
        mock_check_vgroup,
        mock_human_to_bytes,
        mock_check_response,
    ):
        """Test multi-volume creation in check mode"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824
        mock_check_vgroup.return_value = True
        mock_check_pod.return_value = True

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "vol",
            "size": "1G",
            "count": 3,
            "start": 0,
            "digits": 1,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "with_default_protection": True,
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        create_multi_volume(mock_module, mock_array)

        # In check mode, post_volumes should NOT be called
        mock_array.post_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume.check_vgroup")
    def test_create_multi_volume_vgroup_not_exists(self, mock_check_vgroup):
        """Test multi-volume creation fails when volume group doesn't exist"""
        mock_check_vgroup.return_value = False

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vgroup/vol",
            "size": "1G",
            "count": 5,
            "start": 0,
            "digits": 1,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        try:
            create_multi_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "Volume Group" in call_args["msg"]
        assert "does not exist" in call_args["msg"]


class TestGetPod:
    """Test cases for get_pod function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_pod_exists(self, mock_loose_version):
        """Test get_pod returns pod when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"pgroup": "pod1::pgroup1"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_pod = Mock()
        mock_pod.name = "pod1"
        mock_array.get_pods.return_value.status_code = 200
        mock_array.get_pods.return_value.items = [mock_pod]

        result = get_pod(mock_module, mock_array)

        assert result is not None

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_pod_not_exists(self, mock_loose_version):
        """Test get_pod returns None when pod doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"pgroup": "pod1::pgroup1"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_pods.return_value.status_code = 404

        result = get_pod(mock_module, mock_array)

        assert result is None


class TestCheckPod:
    """Test cases for check_pod function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_check_pod_exists(self, mock_loose_version):
        """Test check_pod returns True when pod exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "pod1::volume1"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_pods.return_value.status_code = 200

        result = check_pod(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_check_pod_not_exists(self, mock_loose_version):
        """Test check_pod returns False when pod doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "pod1::volume1"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_pods.return_value.status_code = 404

        result = check_pod(mock_module, mock_array)

        assert result is False


class TestCheckVgroup:
    """Test cases for check_vgroup function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_check_vgroup_exists(self, mock_loose_version):
        """Test check_vgroup returns True when vgroup exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "vgroup1/volume1"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_groups.return_value.status_code = 200

        result = check_vgroup(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_check_vgroup_not_exists(self, mock_loose_version):
        """Test check_vgroup returns False when vgroup doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"name": "vgroup1/volume1"}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volume_groups.return_value.status_code = 404

        result = check_vgroup(mock_module, mock_array)

        assert result is False


class TestGetEndpoint:
    """Test cases for get_endpoint function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_endpoint_exists(self, mock_loose_version):
        """Test get_endpoint returns endpoint when it exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_endpoint = Mock()
        mock_endpoint.name = "endpoint1"
        mock_endpoint.subtype = "protocol_endpoint"  # Must be protocol_endpoint
        mock_array.get_volumes.return_value.status_code = 200
        mock_array.get_volumes.return_value.items = [mock_endpoint]

        result = get_endpoint(mock_module, "endpoint1", mock_array)

        assert result is not None

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_endpoint_not_exists(self, mock_loose_version):
        """Test get_endpoint returns None when endpoint doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volumes.return_value.status_code = 404

        result = get_endpoint(mock_module, "endpoint1", mock_array)

        assert result is None


class TestGetMultiVolumes:
    """Test cases for get_multi_volumes function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_multi_volumes_all_exist(self, mock_loose_version):
        """Test get_multi_volumes returns volume when all volumes exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {
            "name": "vol",
            "count": 3,
            "start": 0,
            "digits": 1,
            "suffix": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        # Return volumes for each check
        mock_vol = Mock()
        mock_vol.name = "vol0"
        mock_array.get_volumes.return_value.status_code = 200
        mock_array.get_volumes.return_value.items = [mock_vol]

        result = get_multi_volumes(mock_module, mock_array)

        # Returns the first volume when found
        assert result is not None

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_multi_volumes_not_exist(self, mock_loose_version):
        """Test get_multi_volumes returns None when volumes don't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {
            "name": "vol",
            "count": 3,
            "start": 0,
            "digits": 1,
            "suffix": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_volumes.return_value.status_code = 404

        result = get_multi_volumes(mock_module, mock_array)

        assert result is None


class TestGetPendingPgroup:
    """Test cases for get_pending_pgroup function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_pending_pgroup_exists_destroyed(self, mock_loose_version):
        """Test get_pending_pgroup returns pgroup when exists and destroyed"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"pgroup": "test-pg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        mock_pgroup = Mock()
        mock_pgroup.destroyed = True
        mock_array.get_protection_groups.return_value.status_code = 200
        mock_array.get_protection_groups.return_value.items = [mock_pgroup]

        result = get_pending_pgroup(mock_module, mock_array)

        assert result == mock_pgroup

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_pending_pgroup_exists_not_destroyed(self, mock_loose_version):
        """Test get_pending_pgroup returns None when exists but not destroyed"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"pgroup": "test-pg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        mock_pgroup = Mock()
        mock_pgroup.destroyed = False
        mock_array.get_protection_groups.return_value.status_code = 200
        mock_array.get_protection_groups.return_value.items = [mock_pgroup]

        result = get_pending_pgroup(mock_module, mock_array)

        assert result is None


class TestGetPgroup:
    """Test cases for get_pgroup function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_pgroup_exists(self, mock_loose_version):
        """Test get_pgroup returns pgroup when exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"pgroup": "test-pg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"

        mock_pgroup = Mock()
        mock_array.get_protection_groups.return_value.status_code = 200
        mock_array.get_protection_groups.return_value.items = [mock_pgroup]

        result = get_pgroup(mock_module, mock_array)

        assert result == mock_pgroup

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_pgroup_not_exists(self, mock_loose_version):
        """Test get_pgroup returns None when not exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"pgroup": "test-pg", "context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_protection_groups.return_value.status_code = 404

        result = get_pgroup(mock_module, mock_array)

        assert result is None


class TestPgExists:
    """Test cases for pg_exists function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_pg_exists_true(self, mock_loose_version):
        """Test pg_exists returns True when pgroup exists"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_protection_groups.return_value.status_code = 200

        result = pg_exists(mock_module, "test-pg", mock_array)

        assert result is True

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_pg_exists_false(self, mock_loose_version):
        """Test pg_exists returns False when pgroup doesn't exist"""
        mock_loose_version.side_effect = lambda x: float(x) if x != "2.0" else 2.0
        mock_module = Mock()
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"
        mock_array.get_protection_groups.return_value.status_code = 404

        result = pg_exists(mock_module, "test-pg", mock_array)

        assert result is False


class TestMoveVolume:
    """Test cases for move_volume function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_local_same_source_dest(self, mock_loose_version):
        """Test move_volume fails when moving local to local"""
        import pytest
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "test-vol",
            "context": "",
            "move": "local",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        with pytest.raises(SystemExit):
            move_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_target_exists(self, mock_loose_version):
        """Test move_volume fails when target volume exists"""
        import pytest
        from packaging.version import Version as LooseVersion

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "vgroup1/test-vol",
            "context": "",
            "move": "local",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value.status_code = 200  # target exists

        with pytest.raises(SystemExit):
            move_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestVolfact:
    """Test cases for _volfact function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_volfact_check_mode(self, mock_loose_version):
        """Test _volfact returns empty dict in check mode"""
        from packaging.version import Version as LooseVersion
        from plugins.modules.purefa_volume import _volfact

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        result = _volfact(mock_module, mock_array, "test-vol")

        assert result == {}

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_volfact_basic(self, mock_loose_version):
        """Test _volfact returns volume facts"""
        from packaging.version import Version as LooseVersion
        from plugins.modules.purefa_volume import _volfact

        mock_loose_version.side_effect = LooseVersion
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        mock_volume = Mock()
        mock_volume.serial = "12345ABCDEF0123456"
        mock_volume.provisioned = 1073741824
        mock_volume.created = 1700000000000
        mock_volume.qos = Mock()
        mock_volume.qos.iops_limit = 10000
        mock_volume.qos.bandwidth_limit = 100000000
        mock_volume.requested_promotion_state = "promoted"
        mock_volume.promotion_status = "promoted"
        mock_volume.priority = 50
        mock_volume.destroyed = False
        mock_volume.priority_adjustment = Mock()
        mock_volume.priority_adjustment.priority_adjustment_operator = "+"
        mock_volume.priority_adjustment.priority_adjustment_value = 10
        mock_volume.context = Mock()
        mock_volume.context.name = ""
        mock_array.get_volumes.return_value = Mock(items=[mock_volume], status_code=200)

        result = _volfact(mock_module, mock_array, "test-vol")

        assert "test-vol" in result
        assert result["test-vol"]["serial"] == "12345ABCDEF0123456"


class TestMoveVolumeSuccess:
    """Test cases for move_volume function success scenarios"""

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_move_volume_to_vgroup(self, mock_lv, mock_volfact, mock_check_response):
        """Test moving volume to a volume group"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "move": "vgroup1",
            "context": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_pods.return_value = Mock(status_code=400)  # Not a pod
        mock_array.get_volume_groups.return_value = Mock(
            items=[Mock(destroyed=False)], status_code=200
        )
        mock_array.get_volumes.return_value = Mock(
            status_code=400
        )  # Target doesn't exist
        # Mock patch_volumes response with items
        mock_new_vol = Mock()
        mock_new_vol.name = "vgroup1/test-vol"
        mock_array.patch_volumes.return_value = Mock(
            status_code=200, items=[mock_new_vol]
        )
        mock_volfact.return_value = {"vgroup1/test-vol": {}}

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_move_volume_to_pod(self, mock_lv, mock_volfact, mock_check_response):
        """Test moving volume to a pod"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "move": "pod1",
            "context": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"
        mock_array.get_pods.return_value = Mock(items=[mock_pod], status_code=200)
        mock_array.get_volumes.return_value = Mock(
            status_code=400
        )  # Target doesn't exist
        # Mock patch_volumes response with items
        mock_new_vol = Mock()
        mock_new_vol.name = "pod1::test-vol"
        mock_array.patch_volumes.return_value = Mock(
            status_code=200, items=[mock_new_vol]
        )
        mock_volfact.return_value = {"pod1::test-vol": {}}

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()


class TestDeleteVolumeSuccess:
    """Test cases for delete_volume function success scenarios"""

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_delete_volume_with_eradicate(
        self, mock_lv, mock_volfact, mock_check_response
    ):
        """Test deleting a volume with eradicate flag"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "add_to_pgs": None,
            "eradicate": True,
            "context": None,
        }
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_array.delete_volumes.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            delete_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_array.delete_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_delete_volume_remove_from_pgs(
        self, mock_lv, mock_volfact, mock_check_response
    ):
        """Test deleting a volume from protection groups"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "add_to_pgs": ["pg1", "pg2"],
            "eradicate": False,
            "context": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_pg1 = Mock()
        mock_pg1.group = Mock()
        mock_pg1.group.name = "pg1"
        mock_array.get_protection_groups_volumes.return_value = Mock(items=[mock_pg1])
        mock_array.delete_volumes_protection_groups.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"test-vol": {}}

        delete_volume(mock_module, mock_array)

        mock_array.delete_volumes_protection_groups.assert_called_once()
        mock_module.exit_json.assert_called_once()


class TestUpdateVolumeSuccess:
    """Test cases for update_volume function success scenarios"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_update_volume_resize(
        self, mock_lv, mock_check_response, mock_h2b, mock_volfact
    ):
        """Test updating volume size"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": "20G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "context": "",
            "with_default_protection": False,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock human_to_bytes to return larger size
        mock_h2b.return_value = 21474836480  # 20G
        # Mock current volume with smaller size
        mock_vol = Mock()
        mock_vol.provisioned = 10737418240  # 10G
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"test-vol": {}}

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_update_volume_bw_qos(self, mock_lv, mock_check_response, mock_volfact):
        """Test updating volume bandwidth QoS"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": "100M",
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "context": "",
            "with_default_protection": False,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current volume
        mock_vol = Mock()
        mock_vol.provisioned = 10737418240
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888  # Default unlimited
        mock_vol.qos.iops_limit = 100000000
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"test-vol": {}}

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_update_volume_no_changes(self, mock_lv, mock_volfact):
        """Test update_volume when no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "context": "",
            "with_default_protection": False,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # Mock current volume
        mock_vol = Mock()
        mock_vol.provisioned = 10737418240
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_volfact.return_value = {"test-vol": {}}

        update_volume(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(
            changed=False, volume={"test-vol": {}}
        )


class TestCopyFromVolumeExtended:
    """Extended test cases for copy_from_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_target")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_copy_from_volume_overwrite_existing(
        self, mock_lv, mock_get_target, mock_check_response, mock_volfact
    ):
        """Test copy_from_volume overwrites existing target"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-vol",
            "target": "target-vol",
            "overwrite": True,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_target.return_value = Mock(name="target-vol")  # Target exists
        mock_array.post_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"target-vol": {}}

        copy_from_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.get_target")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_copy_from_volume_target_exists_no_overwrite(
        self, mock_lv, mock_get_target, mock_volfact
    ):
        """Test copy_from_volume does nothing when target exists without overwrite"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-vol",
            "target": "target-vol",
            "overwrite": False,
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_target.return_value = Mock(name="target-vol")  # Target exists
        mock_volfact.return_value = {"target-vol": {}}

        copy_from_volume(mock_module, mock_array)

        # When target exists and overwrite is False, no changes should be made
        mock_array.post_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once_with(
            changed=False, volume={"target-vol": {}}
        )

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_target")
    @patch("plugins.modules.purefa_volume.ReferenceType")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Reference")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_copy_from_volume_with_add_to_pgs(
        self,
        mock_lv,
        mock_reference,
        mock_volume_post,
        mock_ref_type,
        mock_get_target,
        mock_check_response,
        mock_volfact,
    ):
        """Test copy_from_volume with add_to_pgs parameter"""
        mock_lv.side_effect = float
        mock_get_target.return_value = None  # Target doesn't exist
        mock_volfact.return_value = {"target-vol": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-vol",
            "target": "target-vol",
            "overwrite": False,
            "add_to_pgs": ["pg1", "pg2"],
            "with_default_protection": False,
            "context": "array1",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = Mock(status_code=200)

        copy_from_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()
        # Verify ReferenceType was called for each protection group
        assert mock_ref_type.call_count == 2

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_target")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Reference")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_copy_from_volume_check_mode(
        self,
        mock_lv,
        mock_reference,
        mock_volume_post,
        mock_get_target,
        mock_check_response,
        mock_volfact,
    ):
        """Test copy_from_volume in check mode"""
        mock_lv.side_effect = float
        mock_get_target.return_value = None  # Target doesn't exist
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "source-vol",
            "target": "target-vol",
            "overwrite": False,
            "add_to_pgs": None,
            "with_default_protection": True,
            "context": "array1",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        copy_from_volume(mock_module, mock_array)

        # In check mode, post_volumes should NOT be called
        mock_array.post_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True


class TestRenameVolumeExtended:
    """Extended test cases for rename_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_rename_volume_in_pod(self, mock_lv, mock_check_response, mock_volfact):
        """Test rename_volume within a pod"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::source-vol",
            "rename": "new-vol",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(
            status_code=404
        )  # Target doesn't exist
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"new-vol": {}}

        rename_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_rename_volume_in_vgroup(self, mock_lv, mock_check_response, mock_volfact):
        """Test rename_volume within a volume group"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vgroup1/source-vol",
            "rename": "new-vol",
            "context": "",
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(
            status_code=404
        )  # Target doesn't exist
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"new-vol": {}}

        rename_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()


class TestUpdateVolumeQos:
    """Test cases for update_volume QoS changes"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_update_volume_reduce_bandwidth(
        self, mock_lv, mock_check_response, mock_h2b, mock_volfact
    ):
        """Test update_volume reduces bandwidth QoS"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": "10G",
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "context": "",
            "with_default_protection": False,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vol = Mock()
        mock_vol.provisioned = 10737418240
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888  # Current is max
        mock_vol.qos.iops_limit = 100000000
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_h2b.return_value = 10737418240  # 10G
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"test-vol": {}}

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_update_volume_check_mode_no_patch(
        self, mock_lv, mock_check_response, mock_volfact
    ):
        """Test update_volume doesn't call patch in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-vol",
            "size": "20G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "context": "",
            "with_default_protection": False,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vol = Mock()
        mock_vol.provisioned = 10737418240  # 10G
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_volfact.return_value = {"test-vol": {}}

        from plugins.modules.purefa_volume import human_to_bytes

        with patch("plugins.modules.purefa_volume.human_to_bytes") as mock_h2b:
            mock_h2b.return_value = 21474836480  # 20G - larger than current

            update_volume(mock_module, mock_array)

        # In check mode, patch_volumes should NOT be called
        mock_array.patch_volumes.assert_not_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_update_volume_remove_bw_qos_context_api(
        self, mock_lv, mock_check_response, mock_h2b, mock_volfact
    ):
        """Test update_volume removes bandwidth QoS (bw_qos=0) with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": "0",  # Zero removes the QoS limit
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "context": "pod1",
            "with_default_protection": False,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vol = Mock()
        mock_vol.provisioned = 10737418240
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 10737418240  # Current limit is 10G
        mock_vol.qos.iops_limit = 100000000
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_h2b.return_value = 0  # bw_qos="0"
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"test-vol": {}}

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_update_volume_remove_bw_qos_no_context(
        self, mock_lv, mock_check_response, mock_h2b, mock_volfact
    ):
        """Test update_volume removes bandwidth QoS without context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": "0",
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "context": None,
            "with_default_protection": False,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Below CONTEXT_API_VERSION
        mock_vol = Mock()
        mock_vol.provisioned = 10737418240
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 10737418240
        mock_vol.qos.iops_limit = 100000000
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_h2b.return_value = 0
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"test-vol": {}}

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.human_to_real")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_update_volume_remove_iops_qos_context_api(
        self, mock_lv, mock_check_response, mock_h2b, mock_h2r, mock_volfact
    ):
        """Test update_volume removes IOPS QoS (iops_qos=0) with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": "0",  # Zero removes the IOPS limit
            "pgroup": None,
            "add_to_pgs": None,
            "context": "pod1",
            "with_default_protection": False,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vol = Mock()
        mock_vol.provisioned = 10737418240
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 50000  # Current limit
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_h2b.return_value = 549755813888
        mock_h2r.return_value = 0
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"test-vol": {}}

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.human_to_real")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion", side_effect=LooseVersion)
    def test_update_volume_change_iops_qos_context_api(
        self, mock_lv, mock_check_response, mock_h2b, mock_h2r, mock_volfact
    ):
        """Test update_volume changes IOPS QoS with context API"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": "50K",  # Change IOPS limit
            "pgroup": None,
            "add_to_pgs": None,
            "context": "pod1",
            "with_default_protection": False,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
        }
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_vol = Mock()
        mock_vol.provisioned = 10737418240
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000  # Current is max
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_h2b.return_value = 549755813888
        mock_h2r.return_value = 50000  # 50K
        mock_array.patch_volumes.return_value = Mock(status_code=200)
        mock_volfact.return_value = {"test-vol": {}}

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called()


class TestMoveVolume:
    """Test cases for move_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_to_pod_success(
        self,
        mock_lv,
        mock_reference,
        mock_vol_patch,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test moving a volume to a pod successfully"""
        mock_lv.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {"pod1::test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "pod1",
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Pod exists
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"
        mock_array.get_pods.return_value = Mock(status_code=200, items=[mock_pod])

        # Volume doesn't exist at target
        mock_array.get_volumes.return_value = Mock(status_code=400)

        # Vgroup doesn't exist
        mock_array.get_volume_groups.return_value = Mock(status_code=400)

        # Patch succeeds - need items to be iterable
        mock_moved_vol = Mock()
        mock_moved_vol.name = "pod1::test_volume"
        mock_array.patch_volumes.return_value = Mock(
            status_code=200, items=[mock_moved_vol]
        )

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_to_vgroup_success(
        self,
        mock_lv,
        mock_reference,
        mock_vol_patch,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test moving a volume to a volume group successfully"""
        mock_lv.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {"vgroup1/test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "vgroup1",
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Pod doesn't exist
        mock_array.get_pods.return_value = Mock(status_code=400)

        # Vgroup exists
        mock_array.get_volume_groups.return_value = Mock(status_code=200)

        # Volume doesn't exist at target
        mock_array.get_volumes.return_value = Mock(status_code=400)

        # Patch succeeds - need items to be iterable
        mock_moved_vol = Mock()
        mock_moved_vol.name = "vgroup1/test_volume"
        mock_array.patch_volumes.return_value = Mock(
            status_code=200, items=[mock_moved_vol]
        )

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_to_local_same_location(self, mock_lv):
        """Test move to local fails when volume is already local"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",  # No :: or / means it's local
            "move": "local",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "cannot be the same" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_to_stretched_pod_fails(self, mock_lv):
        """Test move to a stretched pod fails"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "stretched_pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Pod exists but is stretched (array_count > 1)
        mock_pod = Mock()
        mock_pod.array_count = 2  # Stretched
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"
        mock_array.get_pods.return_value = Mock(status_code=200, items=[mock_pod])

        # Volume doesn't exist at target
        mock_array.get_volumes.return_value = Mock(status_code=400)

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "stretched pod" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_to_demoted_pod_fails(self, mock_lv):
        """Test move to a demoted pod fails"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "demoted_pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Pod exists but is demoted
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "demoted"
        mock_array.get_pods.return_value = Mock(status_code=200, items=[mock_pod])

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "demoted pod" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_target_exists_fails(self, mock_lv):
        """Test move fails when target volume already exists"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "pod1",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Pod exists
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"
        mock_array.get_pods.return_value = Mock(status_code=200, items=[mock_pod])

        # Volume already exists at target
        mock_array.get_volumes.return_value = Mock(status_code=200)

        # Vgroup doesn't exist
        mock_array.get_volume_groups.return_value = Mock(status_code=400)

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "already exists" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_location_not_exists_fails(self, mock_lv):
        """Test move fails when move location doesn't exist"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "nonexistent",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Neither pod nor vgroup exists
        mock_array.get_pods.return_value = Mock(status_code=400)
        mock_array.get_volume_groups.return_value = Mock(status_code=400)

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "does not exist" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_check_mode(
        self, mock_lv, mock_reference, mock_vol_patch, mock_get_endpoint
    ):
        """Test move volume in check mode"""
        mock_lv.side_effect = float
        mock_get_endpoint.return_value = None

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test_volume",
            "move": "pod1",
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Pod exists
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"
        mock_array.get_pods.return_value = Mock(status_code=200, items=[mock_pod])

        # Volume doesn't exist at target
        mock_array.get_volumes.return_value = Mock(status_code=400)

        # Vgroup doesn't exist
        mock_array.get_volume_groups.return_value = Mock(status_code=400)

        move_volume(mock_module, mock_array)

        # In check mode, patch should not be called
        mock_array.patch_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_from_vgroup_to_local(
        self,
        mock_lv,
        mock_reference,
        mock_vol_patch,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test moving a volume from vgroup to local array"""
        mock_lv.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vgroup1/test_volume",  # Volume is in a vgroup
            "move": "local",
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Target doesn't exist
        mock_array.get_volumes.return_value = Mock(status_code=400)

        # Patch succeeds
        mock_moved_vol = Mock()
        mock_moved_vol.name = "test_volume"
        mock_array.patch_volumes.return_value = Mock(
            status_code=200, items=[mock_moved_vol]
        )

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_from_pod_to_local(
        self,
        mock_lv,
        mock_reference,
        mock_vol_patch,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test moving a volume from pod to local array"""
        mock_lv.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::test_volume",  # Volume is in a pod
            "move": "local",
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Target doesn't exist
        mock_array.get_volumes.return_value = Mock(status_code=400)

        # Patch succeeds
        mock_moved_vol = Mock()
        mock_moved_vol.name = "test_volume"
        mock_array.patch_volumes.return_value = Mock(
            status_code=200, items=[mock_moved_vol]
        )

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_to_linked_source_pod_fails(self, mock_lv):
        """Test move to a linked source pod fails"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "linked_pod",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Pod exists but is linked
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 1  # Has linked targets
        mock_pod.promotion_status = "promoted"
        mock_array.get_pods.return_value = Mock(status_code=200, items=[mock_pod])

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "linked source pod" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_both_pod_and_vgroup_exist_fails(self, mock_lv):
        """Test move fails when move location matches both pod and vgroup"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "ambiguous_name",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        # Both pod and vgroup exist with same name
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"
        mock_array.get_pods.return_value = Mock(status_code=200, items=[mock_pod])
        mock_array.get_volume_groups.return_value = Mock(status_code=200)

        # Volume doesn't exist at target
        mock_array.get_volumes.return_value = Mock(status_code=400)

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "both a pod and a vgroup" in call_args["msg"]


class TestVolfact:
    """Test cases for _volfact function"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_volfact_returns_volume_facts(self, mock_lv):
        """Test _volfact returns correct volume facts"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"context": ""}

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.serial = "ABC123DEF456GHI"
        mock_vol.created = 1700000000000
        mock_vol.qos = Mock()
        mock_vol.qos.iops_limit = 100000
        mock_vol.qos.bandwidth_limit = 1073741824
        mock_vol.requested_promotion_state = "promoted"
        mock_vol.promotion_status = "promoted"
        mock_vol.priority = 50
        mock_vol.destroyed = False
        mock_vol.priority_adjustment = Mock()
        mock_vol.priority_adjustment.priority_adjustment_operator = "+"
        mock_vol.priority_adjustment.priority_adjustment_value = 10
        mock_vol.context = Mock()
        mock_vol.context.name = "pod1"

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])

        result = _volfact(mock_module, mock_array, "test_volume")

        assert "test_volume" in result
        assert result["test_volume"]["size"] == 1073741824
        assert result["test_volume"]["serial"] == "ABC123DEF456GHI"
        assert result["test_volume"]["iops_limit"] == 100000
        assert result["test_volume"]["bandwidth_limit"] == 1073741824
        assert result["test_volume"]["destroyed"] is False

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_volfact_check_mode_returns_empty(self, mock_lv):
        """Test _volfact returns empty dict in check mode"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"context": ""}

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        result = _volfact(mock_module, mock_array, "test_volume")

        assert result == {}
        mock_array.get_volumes.assert_not_called()

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_volfact_with_priority_api_version(self, mock_lv):
        """Test _volfact handles priority API version"""
        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"context": ""}

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.serial = "ABC123DEF456GHI"
        mock_vol.created = 1700000000000
        mock_vol.qos = Mock()
        mock_vol.qos.iops_limit = 100000
        mock_vol.qos.bandwidth_limit = 1073741824
        mock_vol.requested_promotion_state = "promoted"
        mock_vol.promotion_status = "promoted"
        mock_vol.priority = 50
        mock_vol.destroyed = False
        mock_vol.priority_adjustment = Mock()
        mock_vol.priority_adjustment.priority_adjustment_operator = "+"
        mock_vol.priority_adjustment.priority_adjustment_value = 10
        mock_vol.context = Mock()
        mock_vol.context.name = "pod1"

        mock_array = Mock()
        mock_array.get_rest_version.return_value = (
            "2.38"  # Higher than PRIORITY_API_VERSION
        )
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])

        result = _volfact(mock_module, mock_array, "test_volume")

        assert result["test_volume"]["priority_operator"] == "+"
        assert result["test_volume"]["priority_value"] == 10
        assert result["test_volume"]["context"] == "pod1"


class TestCreateMultiVolumeExtended:
    """Extended test cases for create_multi_volume function"""

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_vgroup")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    def test_create_multi_volume_vgroup_not_exists(
        self,
        mock_volume_post,
        mock_lv,
        mock_check_vgroup,
        mock_h2b,
        mock_check_response,
    ):
        """Test multi-volume creation fails when vgroup doesn't exist"""
        import pytest

        mock_lv.side_effect = float
        mock_check_vgroup.return_value = False  # VGroup doesn't exist

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vg1/vol",
            "size": "1G",
            "count": 3,
            "start": 0,
            "digits": 2,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
            "with_default_protection": True,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        with pytest.raises(SystemExit):
            create_multi_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "Volume Group" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    def test_create_multi_volume_pod_not_exists(
        self,
        mock_volume_post,
        mock_lv,
        mock_check_pod,
        mock_h2b,
        mock_check_response,
    ):
        """Test multi-volume creation fails when pod doesn't exist"""
        import pytest

        mock_lv.side_effect = float
        mock_check_pod.return_value = False  # Pod doesn't exist

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::vol",
            "size": "1G",
            "count": 3,
            "start": 0,
            "digits": 2,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
            "with_default_protection": True,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        with pytest.raises(SystemExit):
            create_multi_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "Pod" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    def test_create_multi_volume_demoted_pod_fails(
        self,
        mock_volume_post,
        mock_lv,
        mock_check_pod,
        mock_h2b,
        mock_check_response,
    ):
        """Test multi-volume creation fails when pod is demoted"""
        import pytest

        mock_lv.side_effect = float
        mock_check_pod.return_value = True

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::vol",
            "size": "1G",
            "count": 3,
            "start": 0,
            "digits": 2,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
            "with_default_protection": True,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        # Mock demoted pod
        mock_pod = Mock()
        mock_pod.promotion_status = "demoted"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_pods.return_value = Mock(items=[mock_pod])

        with pytest.raises(SystemExit):
            create_multi_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "demoted" in str(mock_module.fail_json.call_args)


class TestUpdateVolumePromotionState:
    """Test cases for update_volume with promotion_state parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_update_volume_change_promotion_state(
        self, mock_vol_patch, mock_lv, mock_check_response, mock_volfact
    ):
        """Test update_volume changes promotion state"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {"promotion_status": "demoted"}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": "demoted",
            "priority_operator": None,
            "priority_value": None,
            "context": "",
        }

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000
        mock_vol.promotion_status = "promoted"  # Current state is different

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        update_volume(mock_module, mock_array)

        # Verify patch_volumes was called for promotion_state change
        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_update_volume_same_promotion_state_no_change(
        self, mock_vol_patch, mock_lv, mock_check_response, mock_volfact
    ):
        """Test update_volume no change when promotion_state is same"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {"promotion_status": "promoted"}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": "promoted",  # Same as current
            "priority_operator": None,
            "priority_value": None,
            "context": "",
        }

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000
        mock_vol.promotion_status = "promoted"  # Same state

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])

        update_volume(mock_module, mock_array)

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False


class TestUpdateVolumePriority:
    """Test cases for update_volume with priority_operator parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.PriorityAdjustment")
    def test_update_volume_change_priority_operator(
        self,
        mock_prio_adj,
        mock_vol_patch,
        mock_lv,
        mock_check_response,
        mock_volfact,
    ):
        """Test update_volume changes priority operator"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": "-",  # New operator
            "priority_value": 5,
            "context": "",
        }

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000
        mock_vol.priority_adjustment = Mock()
        mock_vol.priority_adjustment.priority_adjustment_operator = "+"  # Current
        mock_vol.priority_adjustment.priority_adjustment_value = 10

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.PriorityAdjustment")
    def test_update_volume_change_priority_value(
        self,
        mock_prio_adj,
        mock_vol_patch,
        mock_lv,
        mock_check_response,
        mock_volfact,
    ):
        """Test update_volume changes priority value"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": "+",  # Same operator
            "priority_value": 20,  # Different value
            "context": "",
        }

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000
        mock_vol.priority_adjustment = Mock()
        mock_vol.priority_adjustment.priority_adjustment_operator = "+"
        mock_vol.priority_adjustment.priority_adjustment_value = 10  # Current value

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True


class TestUpdateVolumeAddToPgs:
    """Test cases for update_volume with add_to_pgs parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_update_volume_add_to_new_pgs(
        self, mock_lv, mock_check_response, mock_volfact
    ):
        """Test update_volume adds volume to new protection groups"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": ["pg1", "pg2"],
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
            "context": "",
        }

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000

        # Currently not in any PGs
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.get_protection_groups_volumes.return_value = Mock(items=[])
        mock_array.post_volumes_protection_groups.return_value = Mock(status_code=200)

        update_volume(mock_module, mock_array)

        mock_array.post_volumes_protection_groups.assert_called_once()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_update_volume_already_in_pgs_no_change(
        self, mock_lv, mock_check_response, mock_volfact
    ):
        """Test update_volume no change when already in specified PGs"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": ["pg1"],
            "promotion_state": None,
            "priority_operator": None,
            "priority_value": None,
            "context": "",
        }

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000

        # Already in pg1
        mock_current_pg = Mock()
        mock_current_pg.group = Mock()
        mock_current_pg.group.name = "pg1"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.get_protection_groups_volumes.return_value = Mock(
            items=[mock_current_pg]
        )

        update_volume(mock_module, mock_array)

        # Should not call post because already in PG
        mock_array.post_volumes_protection_groups.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False


class TestCreateVolumeExtended:
    """Extended test cases for create_volume function"""

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_pod_not_exists(
        self,
        mock_qos,
        mock_volume_post,
        mock_lv,
        mock_check_pod,
        mock_h2b,
        mock_check_response,
    ):
        """Test create_volume fails when pod doesn't exist"""
        import pytest

        mock_lv.side_effect = float
        mock_check_pod.return_value = False

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::test-vol",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        with pytest.raises(SystemExit):
            create_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "Pod does not exist" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_demoted_pod_fails(
        self,
        mock_qos,
        mock_volume_post,
        mock_lv,
        mock_check_pod,
        mock_h2b,
        mock_check_response,
    ):
        """Test create_volume fails when pod is demoted"""
        import pytest

        mock_lv.side_effect = float
        mock_check_pod.return_value = True

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::test-vol",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        # Mock demoted pod
        mock_pod = Mock()
        mock_pod.promotion_status = "demoted"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_pods.return_value = Mock(items=[mock_pod])

        with pytest.raises(SystemExit):
            create_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "demoted" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_no_size_fails(
        self,
        mock_qos,
        mock_volume_post,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test create_volume fails when no size specified"""
        import pytest

        mock_lv.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,  # No size
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        with pytest.raises(SystemExit):
            create_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "Size" in str(mock_module.fail_json.call_args)


class TestRecoverVolumeExtended:
    """Extended test cases for recover_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_recover_volume_old_api_version(
        self, mock_vol_patch, mock_lv, mock_check_response, mock_volfact
    ):
        """Test recover_volume with old API version (no context)"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {"destroyed": False}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API version
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        recover_volume(mock_module, mock_array)

        # Should call patch_volumes without context_names
        mock_array.patch_volumes.assert_called_once()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True


class TestDeleteVolumeExtended:
    """Extended test cases for delete_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_delete_volume_old_api_version(
        self, mock_vol_patch, mock_lv, mock_check_response, mock_volfact
    ):
        """Test delete_volume with old API version (no context)"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {"destroyed": True}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "add_to_pgs": None,
            "eradicate": False,
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API version
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        delete_volume(mock_module, mock_array)

        # Should call patch_volumes without context_names
        mock_array.patch_volumes.assert_called_once()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_delete_volume_patch_fails(
        self, mock_vol_patch, mock_lv, mock_check_response, mock_volfact
    ):
        """Test delete_volume when patch fails"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "add_to_pgs": None,
            "eradicate": False,
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.patch_volumes.return_value = Mock(status_code=400)  # Fails

        delete_volume(mock_module, mock_array)

        # Should call check_response due to non-200 status
        mock_check_response.assert_called()


class TestEradicateVolumeExtended:
    """Extended test cases for eradicate_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_eradicate_volume_old_api_version(
        self, mock_lv, mock_check_response, mock_volfact
    ):
        """Test eradicate_volume with old API version (no context)"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {"destroyed": True}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "eradicate": True,
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API version
        mock_array.delete_volumes.return_value = Mock(status_code=200)

        eradicate_volume(mock_module, mock_array)

        # Should call delete_volumes without context_names
        mock_array.delete_volumes.assert_called_once()
        call_kwargs = mock_array.delete_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_eradicate_volume_no_eradicate_flag(self, mock_lv, mock_volfact):
        """Test eradicate_volume when eradicate flag is False"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {"destroyed": True}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "eradicate": False,  # Not set to eradicate
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        eradicate_volume(mock_module, mock_array)

        # Should NOT call delete_volumes since eradicate is False
        mock_array.delete_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False


class TestCreateVolumeWithPromotionState:
    """Test cases for create_volume with promotion_state parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_with_promotion_state_success(
        self,
        mock_qos,
        mock_vol_patch,
        mock_vol_post,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test create_volume with promotion_state parameter succeeds"""
        mock_lv.side_effect = float
        mock_h2b.return_value = 1073741824
        mock_volfact.return_value = {"test-vol": {"promotion_state": "promoted"}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": "promoted",
            "priority_operator": None,
            "context": "",
            "with_default_protection": True,
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = Mock(status_code=200)
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        create_volume(mock_module, mock_array)

        # Should call post_volumes and patch_volumes for promotion_state
        mock_array.post_volumes.assert_called_once()
        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_with_promotion_state_fails_cleanup(
        self,
        mock_qos,
        mock_vol_patch,
        mock_vol_post,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test create_volume with promotion_state fails and cleans up volume"""
        import pytest

        mock_lv.side_effect = float
        mock_h2b.return_value = 1073741824
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": "demoted",
            "priority_operator": None,
            "context": "",
            "with_default_protection": True,
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        # First call succeeds (create), second call fails (set promotion_state)
        mock_error = Mock()
        mock_error.message = "Cannot set promotion state"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = Mock(status_code=200)
        mock_array.patch_volumes.return_value = Mock(
            status_code=400, errors=[mock_error]
        )
        mock_array.delete_volumes.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            create_volume(mock_module, mock_array)

        # Should fail and clean up the volume
        mock_module.fail_json.assert_called_once()
        assert "Promotion State" in str(mock_module.fail_json.call_args)


class TestCreateVolumeWithPriorityOperator:
    """Test cases for create_volume with priority_operator parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Qos")
    @patch("plugins.modules.purefa_volume.PriorityAdjustment")
    def test_create_volume_with_priority_operator_success(
        self,
        mock_priority_adj,
        mock_qos,
        mock_vol_patch,
        mock_vol_post,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test create_volume with priority_operator parameter succeeds"""
        mock_lv.side_effect = float
        mock_h2b.return_value = 1073741824
        mock_volfact.return_value = {"test-vol": {"priority": 10}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": "+",
            "priority_value": 10,
            "context": "",
            "with_default_protection": True,
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = Mock(status_code=200)
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        create_volume(mock_module, mock_array)

        # Should call post_volumes and patch_volumes for priority
        mock_array.post_volumes.assert_called_once()
        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Qos")
    @patch("plugins.modules.purefa_volume.PriorityAdjustment")
    def test_create_volume_with_priority_operator_fails_cleanup(
        self,
        mock_priority_adj,
        mock_qos,
        mock_vol_patch,
        mock_vol_post,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test create_volume with priority_operator fails and cleans up"""
        import pytest

        mock_lv.side_effect = float
        mock_h2b.return_value = 1073741824

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": "+",
            "priority_value": 10,
            "context": "",
            "with_default_protection": True,
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_error = Mock()
        mock_error.message = "Cannot set DMM priority"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = Mock(status_code=200)
        mock_array.patch_volumes.return_value = Mock(
            status_code=400, errors=[mock_error]
        )
        mock_array.delete_volumes.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            create_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "DMM Priority" in str(mock_module.fail_json.call_args)


class TestCreateVolumeWithPgroup:
    """Test cases for create_volume with pgroup parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    @patch("plugins.modules.purefa_volume.ReferenceType")
    def test_create_volume_with_pgroup_success(
        self,
        mock_ref_type,
        mock_qos,
        mock_vol_post,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test create_volume with pgroup parameter succeeds"""
        mock_lv.side_effect = float
        mock_h2b.return_value = 1073741824
        mock_volfact.return_value = {"test-vol": {"pgroup": "pg1"}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": "pg1",
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "",
            "with_default_protection": True,
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.post_volumes.return_value = Mock(status_code=200)
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        create_volume(mock_module, mock_array)

        # Should call post_volumes and patch_volumes for pgroup
        mock_array.post_volumes.assert_called_once()
        mock_array.patch_volumes.assert_called()
        mock_module.exit_json.assert_called_once()


class TestMoveVolumeExtended:
    """Extended test cases for move_volume function"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_move_volume_from_stretched_pod_fails(
        self,
        mock_ref,
        mock_vol_patch,
        mock_lv,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test move_volume fails when source pod is stretched"""
        import pytest

        mock_lv.side_effect = float
        mock_get_endpoint.return_value = False

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::test-vol",
            "move": "dest-pod",  # Moving to another pod
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        # Mock stretched pod (array_count > 1)
        mock_stretched_pod = Mock()
        mock_stretched_pod.array_count = 2
        mock_stretched_pod.linked_target_count = 0
        mock_stretched_pod.promotion_status = "promoted"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        # First call gets dest-pod, second call gets pod1 (source)
        mock_array.get_pods.return_value = Mock(
            status_code=200, items=[mock_stretched_pod]
        )
        mock_array.get_volumes.return_value = Mock(
            status_code=400
        )  # Target doesn't exist
        mock_array.get_volume_groups.return_value = Mock(status_code=400)

        with pytest.raises(SystemExit):
            move_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "stretched pod" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_move_volume_from_linked_pod_fails(
        self,
        mock_ref,
        mock_vol_patch,
        mock_lv,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test move_volume fails when source pod has linked targets"""
        import pytest

        mock_lv.side_effect = float
        mock_get_endpoint.return_value = False

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::test-vol",
            "move": "dest-pod",  # Moving to another pod
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        # Mock pod with linked targets
        mock_linked_pod = Mock()
        mock_linked_pod.array_count = 1
        mock_linked_pod.linked_target_count = 2  # Has linked targets
        mock_linked_pod.promotion_status = "promoted"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_pods.return_value = Mock(
            status_code=200, items=[mock_linked_pod]
        )
        mock_array.get_volumes.return_value = Mock(status_code=400)
        mock_array.get_volume_groups.return_value = Mock(status_code=400)

        with pytest.raises(SystemExit):
            move_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "linked source pod" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_move_volume_to_protocol_endpoint_fails(
        self,
        mock_ref,
        mock_vol_patch,
        mock_lv,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test move_volume fails when target is a protocol endpoint"""
        import pytest

        mock_lv.side_effect = float
        mock_get_endpoint.return_value = True  # Target is a protocol endpoint

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "move": "endpoint-target",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=400)
        mock_array.get_volume_groups.return_value = Mock(status_code=200)  # Must exist
        mock_array.get_pods.return_value = Mock(status_code=400)

        with pytest.raises(SystemExit):
            move_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        # Note: The code has a typo "protocol-endpoinnt"
        assert "protocol-endpoin" in str(mock_module.fail_json.call_args).lower()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_move_volume_vgroup_same_location_fails(
        self,
        mock_ref,
        mock_vol_patch,
        mock_lv,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test move_volume fails when source vgroup equals destination"""
        import pytest

        mock_lv.side_effect = float
        mock_get_endpoint.return_value = False

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vgroup1/test-vol",
            "move": "vgroup1",  # Same as source vgroup
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=400)
        mock_array.get_volume_groups.return_value = Mock(
            status_code=200
        )  # vgroup exists
        mock_array.get_pods.return_value = Mock(status_code=400)

        with pytest.raises(SystemExit):
            move_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "same" in str(mock_module.fail_json.call_args).lower()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_move_volume_local_from_vgroup_old_api(
        self,
        mock_ref,
        mock_vol_patch,
        mock_lv,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test move_volume from vgroup to local with old API version"""
        mock_lv.side_effect = float
        mock_get_endpoint.return_value = False
        mock_volfact.return_value = {"test-vol": {}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vgroup1/test-vol",
            "move": "local",
            "context": "",
        }

        mock_moved_vol = Mock()
        mock_moved_vol.name = "test-vol"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API
        mock_array.get_volumes.return_value = Mock(
            status_code=400
        )  # Target doesn't exist
        mock_array.get_volume_groups.return_value = Mock(status_code=400)
        mock_array.get_pods.return_value = Mock(status_code=400)
        mock_array.patch_volumes.return_value = Mock(
            status_code=200, items=[mock_moved_vol]
        )

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_move_volume_local_from_pod_old_api(
        self,
        mock_ref,
        mock_vol_patch,
        mock_lv,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test move_volume from pod to local with old API version"""
        mock_lv.side_effect = float
        mock_get_endpoint.return_value = False
        mock_volfact.return_value = {"test-vol": {}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::test-vol",
            "move": "local",
            "context": "",
        }

        # Mock pod that allows moving
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.linked_target_count = 0
        mock_pod.promotion_status = "promoted"

        mock_moved_vol = Mock()
        mock_moved_vol.name = "test-vol"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API
        mock_array.get_volumes.return_value = Mock(
            status_code=400
        )  # Target doesn't exist
        mock_array.get_volume_groups.return_value = Mock(status_code=400)
        mock_array.get_pods.return_value = Mock(items=[mock_pod])
        mock_array.patch_volumes.return_value = Mock(
            status_code=200, items=[mock_moved_vol]
        )

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()


class TestCopyVolumeOverwrite:
    """Test cases for copy_from_volume with overwrite parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_copy_volume_overwrite_success(
        self,
        mock_ref,
        mock_vol_post,
        mock_lv,
        mock_check_response,
        mock_volfact,
    ):
        """Test copy_from_volume with overwrite=True when target exists"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"target-vol": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-vol",
            "target": "target-vol",
            "overwrite": True,
            "add_to_pgs": None,
            "context": "",
        }

        mock_target = Mock()
        mock_target.name = "target-vol"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_target])
        mock_array.post_volumes.return_value = Mock(status_code=200)

        copy_from_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert call_kwargs["overwrite"] is True
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_copy_volume_overwrite_old_api(
        self,
        mock_ref,
        mock_vol_post,
        mock_lv,
        mock_check_response,
        mock_volfact,
    ):
        """Test copy_from_volume with overwrite using old API version"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"target-vol": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-vol",
            "target": "target-vol",
            "overwrite": True,
            "add_to_pgs": None,
            "context": "",
        }

        mock_target = Mock()
        mock_target.name = "target-vol"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_target])
        mock_array.post_volumes.return_value = Mock(status_code=200)

        copy_from_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_copy_volume_target_not_exists_old_api(
        self,
        mock_ref,
        mock_vol_post,
        mock_lv,
        mock_check_response,
        mock_volfact,
    ):
        """Test copy_from_volume when target doesn't exist using old API"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"target-vol": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source-vol",
            "target": "target-vol",
            "overwrite": False,
            "add_to_pgs": None,
            "with_default_protection": True,
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API
        mock_array.get_volumes.return_value = Mock(
            status_code=400
        )  # Target doesn't exist
        mock_array.post_volumes.return_value = Mock(status_code=200)

        copy_from_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()


class TestCreateMultiVolumePromotionState:
    """Test cases for create_multi_volume with promotion_state parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_multi_volume_with_promotion_state_check_mode(
        self,
        mock_qos,
        mock_vol_patch,
        mock_vol_post,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test create_multi_volume with promotion_state in check_mode"""
        mock_lv.side_effect = float
        mock_h2b.return_value = 1073741824
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-vol",
            "size": "1G",
            "count": 2,
            "start": 0,
            "digits": 1,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": "demoted",
            "priority_operator": None,
            "context": "",
            "with_default_protection": True,
        }

        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(
            status_code=400
        )  # Volumes don't exist
        mock_array.get_volume_groups.return_value = Mock(status_code=400)
        mock_array.get_pods.return_value = Mock(status_code=400)
        mock_array.get_arrays.return_value = Mock(items=[mock_array_info])

        create_multi_volume(mock_module, mock_array)

        # In check_mode, no actual API calls should be made
        mock_array.post_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True


class TestCreateMultiVolumePriorityOperator:
    """Test cases for create_multi_volume with priority_operator parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Qos")
    @patch("plugins.modules.purefa_volume.PriorityAdjustment")
    def test_create_multi_volume_with_priority_operator_fails(
        self,
        mock_priority_adj,
        mock_qos,
        mock_vol_patch,
        mock_vol_post,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test create_multi_volume with priority_operator failure"""
        import pytest

        mock_lv.side_effect = float
        mock_h2b.return_value = 1073741824
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": "1G",
            "count": 2,
            "start": 0,
            "digits": 1,
            "suffix": "",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": "+",
            "priority_value": 10,
            "context": "",
            "with_default_protection": True,
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        # Mock successful create but failed priority_operator
        mock_error = Mock()
        mock_error.message = "Cannot set DMM priority"
        mock_vol1 = Mock()
        mock_vol1.name = "test-vol0"
        mock_vol2 = Mock()
        mock_vol2.name = "test-vol1"
        mock_array_info = Mock()
        mock_array_info.name = "array1"
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = Mock(status_code=400)
        mock_array.get_volume_groups.return_value = Mock(status_code=400)
        mock_array.get_pods.return_value = Mock(status_code=400)
        mock_array.get_arrays.return_value = Mock(items=[mock_array_info])
        mock_array.post_volumes.return_value = Mock(
            status_code=200, items=[mock_vol1, mock_vol2]
        )
        mock_array.patch_volumes.return_value = Mock(
            status_code=400, errors=[mock_error]
        )
        mock_array.delete_volumes.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            create_multi_volume(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "DMM Priority" in str(mock_module.fail_json.call_args)


class TestUpdateVolumeOldApi:
    """Test cases for update_volume with old API version"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_update_volume_resize_old_api(
        self,
        mock_vol_patch,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test update_volume resize with old API version (no context)"""
        mock_lv.side_effect = float
        mock_h2b.return_value = 2147483648  # 2G
        mock_volfact.return_value = {"test-vol": {"size": 2147483648}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": "2G",
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "",
        }

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824  # 1G
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_update_volume_add_to_pgs_old_api(
        self,
        mock_vol_patch,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test update_volume with add_to_pgs using old API version"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {"pgs": ["pg1"]}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": ["pg1"],
            "promotion_state": None,
            "priority_operator": None,
            "context": "",
        }

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.get_protection_groups_volumes.return_value = Mock(items=[])
        mock_array.post_volumes_protection_groups.return_value = Mock(status_code=200)

        update_volume(mock_module, mock_array)

        mock_array.post_volumes_protection_groups.assert_called_once()
        call_kwargs = mock_array.post_volumes_protection_groups.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.PriorityAdjustment")
    def test_update_volume_priority_old_api(
        self,
        mock_priority_adj,
        mock_vol_patch,
        mock_lv,
        mock_h2b,
        mock_check_response,
        mock_volfact,
    ):
        """Test update_volume with priority_operator using old API version"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"test-vol": {"priority": 10}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-vol",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "pgroup": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": "+",
            "priority_value": 10,
            "context": "",
        }

        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_vol.qos = Mock()
        mock_vol.qos.bandwidth_limit = 549755813888
        mock_vol.qos.iops_limit = 100000000
        mock_vol.priority_adjustment = Mock()
        mock_vol.priority_adjustment.priority_adjustment_operator = "="
        mock_vol.priority_adjustment.priority_adjustment_value = 0

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API
        mock_array.get_volumes.return_value = Mock(status_code=200, items=[mock_vol])
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()


class TestRenameVolumeOldApi:
    """Test cases for rename_volume with old API version"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_rename_volume_old_api(
        self, mock_vol_patch, mock_lv, mock_check_response, mock_volfact
    ):
        """Test rename_volume with old API version (no context)"""
        mock_lv.side_effect = float
        mock_volfact.return_value = {"new-vol": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-vol",
            "rename": "new-vol",
            "context": "",
        }

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.20"  # Old API
        mock_array.get_volumes.return_value = Mock(
            status_code=400
        )  # Target doesn't exist
        mock_array.patch_volumes.return_value = Mock(status_code=200)

        rename_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()


class TestDeleteVolumeWithAddToPgs:
    """Test cases for delete_volume with add_to_pgs parameter"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_delete_volume_remove_from_pgs_old_api(
        self,
        mock_loose_version,
        mock_check_response,
        mock_volfact,
    ):
        """Test delete_volume removes volume from PGs using old API"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "add_to_pgs": ["pg1", "pg2"],
            "eradicate": False,
            "context": "array1",
        }

        # Mock current PGs response
        mock_pg1 = Mock()
        mock_pg1.group = Mock()
        mock_pg1.group.name = "pg1"
        mock_pg2 = Mock()
        mock_pg2.group = Mock()
        mock_pg2.group.name = "pg2"

        mock_get_pgs_response = Mock()
        mock_get_pgs_response.items = [mock_pg1, mock_pg2]

        mock_delete_response = Mock()
        mock_delete_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_protection_groups_volumes.return_value = mock_get_pgs_response
        mock_array.delete_volumes_protection_groups.return_value = mock_delete_response

        delete_volume(mock_module, mock_array)

        # Verify delete_volumes_protection_groups was called without context_names
        mock_array.delete_volumes_protection_groups.assert_called_once()
        call_kwargs = mock_array.delete_volumes_protection_groups.call_args[1]
        assert "context_names" not in call_kwargs
        assert call_kwargs["member_names"] == ["test_volume"]
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_delete_volume_no_matching_pgs(
        self,
        mock_loose_version,
        mock_check_response,
        mock_volfact,
    ):
        """Test delete_volume when volume is not in any of the specified PGs"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "add_to_pgs": ["pg1", "pg2"],
            "eradicate": False,
            "context": "array1",
        }

        # Mock current PGs response - volume is in different PGs
        mock_pg = Mock()
        mock_pg.group = Mock()
        mock_pg.group.name = "other_pg"

        mock_get_pgs_response = Mock()
        mock_get_pgs_response.items = [mock_pg]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_protection_groups_volumes.return_value = mock_get_pgs_response

        delete_volume(mock_module, mock_array)

        # Should not call delete_volumes_protection_groups since no matching PGs
        mock_array.delete_volumes_protection_groups.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False


class TestDeleteVolumeEradicateOldApi:
    """Test cases for delete_volume with eradicate using old API"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_delete_and_eradicate_volume_old_api(
        self,
        mock_volume_patch,
        mock_loose_version,
        mock_check_response,
        mock_volfact,
    ):
        """Test delete and eradicate volume using old API"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "add_to_pgs": None,
            "eradicate": True,
            "context": "array1",
        }
        # Make exit_json raise SystemExit to stop execution after first call
        mock_module.exit_json.side_effect = SystemExit("exit_json called")

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200

        mock_delete_response = Mock()
        mock_delete_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.patch_volumes.return_value = mock_patch_response
        mock_array.delete_volumes.return_value = mock_delete_response

        try:
            delete_volume(mock_module, mock_array)
        except SystemExit:
            pass

        # Verify both patch_volumes and delete_volumes were called without context_names
        mock_array.patch_volumes.assert_called_once()
        patch_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in patch_kwargs

        mock_array.delete_volumes.assert_called_once()
        delete_kwargs = mock_array.delete_volumes.call_args[1]
        assert "context_names" not in delete_kwargs
        mock_module.exit_json.assert_called_once()


class TestUpdateVolumePriorityEdgeCases:
    """Test cases for update_volume priority adjustment edge cases"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.PriorityAdjustment")
    def test_update_volume_reset_priority_value_to_zero(
        self,
        mock_priority_adjustment,
        mock_volume_patch,
        mock_loose_version,
        mock_check_response,
        mock_volfact,
    ):
        """Test update_volume resets priority_value to 0 when not specified"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "pgroup": None,
            "promotion_state": None,
            "priority_operator": "+",  # Operator specified
            "priority_value": None,  # Value not specified - should reset to 0
            "context": "array1",
        }

        # Mock existing volume with non-zero priority value
        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_qos = Mock(spec=[])
        mock_vol.qos = mock_qos
        mock_priority = Mock()
        mock_priority.priority_adjustment_operator = "+"
        mock_priority.priority_adjustment_value = 10  # Non-zero value
        mock_vol.priority_adjustment = mock_priority

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.items = [mock_vol]

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_get_response
        mock_array.patch_volumes.return_value = mock_patch_response

        update_volume(mock_module, mock_array)

        # Verify PriorityAdjustment was called with value=0
        mock_priority_adjustment.assert_called_once()
        call_kwargs = mock_priority_adjustment.call_args[1]
        assert call_kwargs["priority_adjustment_value"] == 0
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.PriorityAdjustment")
    def test_update_volume_priority_no_change_needed(
        self,
        mock_priority_adjustment,
        mock_volume_patch,
        mock_loose_version,
        mock_check_response,
        mock_volfact,
    ):
        """Test update_volume when priority is already at desired value"""
        mock_loose_version.side_effect = float
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "pgroup": None,
            "promotion_state": None,
            "priority_operator": "+",
            "priority_value": None,  # Not specified, current is 0
            "context": "array1",
        }

        # Mock existing volume with priority value already 0
        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_qos = Mock(spec=[])
        mock_vol.qos = mock_qos
        mock_priority = Mock()
        mock_priority.priority_adjustment_operator = "+"
        mock_priority.priority_adjustment_value = 0  # Already 0
        mock_vol.priority_adjustment = mock_priority

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.items = [mock_vol]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_get_response

        update_volume(mock_module, mock_array)

        # Should not call patch_volumes since no change needed
        mock_array.patch_volumes.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False


class TestCreateVolumeQosOldApi:
    """Test cases for create_volume with QoS using old API"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_vgroup")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_bw_qos_old_api(
        self,
        mock_qos,
        mock_volume_post,
        mock_loose_version,
        mock_check_pod,
        mock_check_vgroup,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test volume creation with bandwidth QoS using old API"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_check_vgroup.return_value = True
        mock_check_pod.return_value = True
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": "100M",
            "iops_qos": None,
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "pgroup": None,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.post_volumes.return_value = mock_response

        create_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.check_vgroup")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_iops_qos_old_api(
        self,
        mock_qos,
        mock_volume_post,
        mock_loose_version,
        mock_check_pod,
        mock_check_vgroup,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test volume creation with IOPS QoS using old API"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_check_vgroup.return_value = True
        mock_check_pod.return_value = True
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": "100000",
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "pgroup": None,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.post_volumes.return_value = mock_response

        create_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.human_to_real")
    @patch("plugins.modules.purefa_volume.check_vgroup")
    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_create_volume_both_qos_old_api(
        self,
        mock_qos,
        mock_volume_post,
        mock_loose_version,
        mock_check_pod,
        mock_check_vgroup,
        mock_human_to_real,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test volume creation with both QoS using old API"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB
        mock_human_to_real.return_value = 100000
        mock_check_vgroup.return_value = True
        mock_check_pod.return_value = True
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": "100M",
            "iops_qos": "100K",
            "add_to_pgs": None,
            "promotion_state": None,
            "priority_operator": None,
            "pgroup": None,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.post_volumes.return_value = mock_response

        create_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()


class TestUpdateVolumeQosOldApi:
    """Test cases for update_volume QoS with old API"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_update_volume_bw_qos_old_api(
        self,
        mock_qos,
        mock_volume_patch,
        mock_loose_version,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test update_volume bandwidth QoS using old API"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 104857600  # 100MB
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": None,
            "bw_qos": "100M",
            "iops_qos": None,
            "add_to_pgs": None,
            "pgroup": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "array1",
        }

        # Mock existing volume
        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_qos_obj = Mock()
        mock_qos_obj.bandwidth_limit = 52428800  # Current 50MB
        mock_qos_obj.iops_limit = 100000000
        mock_vol.qos = mock_qos_obj

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.items = [mock_vol]

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_volumes.return_value = mock_get_response
        mock_array.patch_volumes.return_value = mock_patch_response

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.human_to_real")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Qos")
    def test_update_volume_iops_qos_old_api(
        self,
        mock_qos,
        mock_volume_patch,
        mock_loose_version,
        mock_human_to_real,
        mock_human_to_bytes,
        mock_check_response,
        mock_volfact,
    ):
        """Test update_volume IOPS QoS using old API"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 0
        mock_human_to_real.return_value = 50000  # 50K IOPS
        mock_volfact.return_value = {"test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": None,
            "bw_qos": None,
            "iops_qos": "50K",
            "add_to_pgs": None,
            "pgroup": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "array1",
        }

        # Mock existing volume
        mock_vol = Mock()
        mock_vol.provisioned = 1073741824
        mock_qos_obj = Mock()
        mock_qos_obj.bandwidth_limit = 549755813888
        mock_qos_obj.iops_limit = 100000  # Current 100K
        mock_vol.qos = mock_qos_obj

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.items = [mock_vol]

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_volumes.return_value = mock_get_response
        mock_array.patch_volumes.return_value = mock_patch_response

        update_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()


class TestCopyFromVolumeOldApi:
    """Test cases for copy_from_volume using old API"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_target")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_copy_volume_no_add_to_pgs_old_api(
        self,
        mock_reference,
        mock_volume_post,
        mock_loose_version,
        mock_get_target,
        mock_check_response,
        mock_volfact,
    ):
        """Test copy_from_volume without add_to_pgs using old API"""
        mock_loose_version.side_effect = float
        mock_get_target.return_value = None  # Target doesn't exist
        mock_volfact.return_value = {"target_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source_volume",
            "target": "target_volume",
            "overwrite": False,
            "add_to_pgs": None,
            "with_default_protection": True,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.post_volumes.return_value = mock_response

        copy_from_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_target")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_copy_volume_with_add_to_pgs_old_api(
        self,
        mock_reference,
        mock_volume_post,
        mock_loose_version,
        mock_get_target,
        mock_check_response,
        mock_volfact,
    ):
        """Test copy_from_volume with add_to_pgs using old API"""
        mock_loose_version.side_effect = float
        mock_get_target.return_value = None  # Target doesn't exist
        mock_volfact.return_value = {"target_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source_volume",
            "target": "target_volume",
            "overwrite": False,
            "add_to_pgs": ["pg1", "pg2"],
            "with_default_protection": True,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.post_volumes.return_value = mock_response

        copy_from_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()


class TestMoveVolumeValidation:
    """Test cases for move_volume validation paths"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_target_exists_fails(
        self,
        mock_loose_version,
        mock_get_endpoint,
        mock_volfact,
    ):
        """Test move_volume fails when target volume already exists (pod move)"""
        mock_loose_version.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "pod1",
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        # Pod exists
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"

        mock_get_pods_response = Mock()
        mock_get_pods_response.status_code = 200
        mock_get_pods_response.items = [mock_pod]

        # Target volume exists
        mock_get_volumes_response = Mock()
        mock_get_volumes_response.status_code = 200

        # Volume group doesn't exist
        mock_get_vgroups_response = Mock()
        mock_get_vgroups_response.status_code = 400

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_pods.return_value = mock_get_pods_response
        mock_array.get_volumes.return_value = mock_get_volumes_response
        mock_array.get_volume_groups.return_value = mock_get_vgroups_response

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called()
        call_args = mock_module.fail_json.call_args[1]
        assert "already exists" in call_args["msg"]

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_into_stretched_pod_fails(
        self,
        mock_loose_version,
        mock_get_endpoint,
        mock_volfact,
    ):
        """Test move_volume fails when moving into stretched pod"""
        mock_loose_version.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "pod1",
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        # Stretched pod (array_count > 1)
        mock_pod = Mock()
        mock_pod.array_count = 2  # Stretched
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"

        mock_get_pods_response = Mock()
        mock_get_pods_response.status_code = 200
        mock_get_pods_response.items = [mock_pod]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_pods.return_value = mock_get_pods_response

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called()
        call_args = mock_module.fail_json.call_args[1]
        assert "stretched pod" in call_args["msg"]

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_into_linked_pod_fails(
        self,
        mock_loose_version,
        mock_get_endpoint,
        mock_volfact,
    ):
        """Test move_volume fails when moving into linked source pod"""
        mock_loose_version.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "pod1",
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        # Linked pod
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 1  # Linked
        mock_pod.promotion_status = "promoted"

        mock_get_pods_response = Mock()
        mock_get_pods_response.status_code = 200
        mock_get_pods_response.items = [mock_pod]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_pods.return_value = mock_get_pods_response

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called()
        call_args = mock_module.fail_json.call_args[1]
        assert "linked source pod" in call_args["msg"]

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_into_demoted_pod_fails(
        self,
        mock_loose_version,
        mock_get_endpoint,
        mock_volfact,
    ):
        """Test move_volume fails when moving into demoted pod"""
        mock_loose_version.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "pod1",
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        # Demoted pod
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "demoted"  # Demoted

        mock_get_pods_response = Mock()
        mock_get_pods_response.status_code = 200
        mock_get_pods_response.items = [mock_pod]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_pods.return_value = mock_get_pods_response

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called()
        call_args = mock_module.fail_json.call_args[1]
        assert "demoted pod" in call_args["msg"]


class TestMoveVolumeOldApiPaths:
    """Test cases for move_volume using old API paths"""

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_move_volume_to_pod_old_api(
        self,
        mock_reference,
        mock_volume_patch,
        mock_loose_version,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test move_volume to pod using old API"""
        mock_loose_version.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {"pod1::test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "pod1",
            "context": "array1",
        }

        # Pod exists with old API
        mock_pod = Mock()
        mock_pod.array_count = 1
        mock_pod.link_target_count = 0
        mock_pod.promotion_status = "promoted"

        mock_get_pods_response = Mock()
        mock_get_pods_response.status_code = 200
        mock_get_pods_response.items = [mock_pod]

        # Target volume doesn't exist
        mock_get_volumes_response = Mock()
        mock_get_volumes_response.status_code = 400

        # Volume group doesn't exist
        mock_get_vgroups_response = Mock()
        mock_get_vgroups_response.status_code = 400

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_vol_item = Mock()
        mock_vol_item.name = "pod1::test_volume"
        mock_patch_response.items = [mock_vol_item]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_pods.return_value = mock_get_pods_response
        mock_array.get_volumes.return_value = mock_get_volumes_response
        mock_array.get_volume_groups.return_value = mock_get_vgroups_response
        mock_array.patch_volumes.return_value = mock_patch_response

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume._volfact")
    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    @patch("plugins.modules.purefa_volume.Reference")
    def test_move_volume_to_vgroup_old_api(
        self,
        mock_reference,
        mock_volume_patch,
        mock_loose_version,
        mock_get_endpoint,
        mock_check_response,
        mock_volfact,
    ):
        """Test move_volume to volume group using old API"""
        mock_loose_version.side_effect = float
        mock_get_endpoint.return_value = None
        mock_volfact.return_value = {"vgroup1/test_volume": {"size": 1073741824}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "move": "vgroup1",
            "context": "array1",
        }

        # Pod doesn't exist
        mock_get_pods_response = Mock()
        mock_get_pods_response.status_code = 400

        # Target volume doesn't exist
        mock_get_volumes_response = Mock()
        mock_get_volumes_response.status_code = 400

        # Volume group exists
        mock_get_vgroups_response = Mock()
        mock_get_vgroups_response.status_code = 200

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_vol_item = Mock()
        mock_vol_item.name = "vgroup1/test_volume"
        mock_patch_response.items = [mock_vol_item]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_pods.return_value = mock_get_pods_response
        mock_array.get_volumes.return_value = mock_get_volumes_response
        mock_array.get_volume_groups.return_value = mock_get_vgroups_response
        mock_array.patch_volumes.return_value = mock_patch_response

        move_volume(mock_module, mock_array)

        mock_array.patch_volumes.assert_called_once()
        call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()


class TestGetDestroyedVolumeOldApi:
    """Test cases for get_destroyed_volume with old API"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_destroyed_volume_old_api(self, mock_loose_version):
        """Test get_destroyed_volume using old API"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {"name": "deleted_volume", "context": "array1"}

        mock_volume = Mock()
        mock_volume.destroyed = True
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_volume]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_volumes.return_value = mock_response

        result = get_destroyed_volume(mock_module, mock_array)

        assert result == mock_volume
        mock_array.get_volumes.assert_called_once()
        call_kwargs = mock_array.get_volumes.call_args[1]
        assert "context_names" not in call_kwargs


class TestCreateVolumeValidation:
    """Test cases for create_volume validation paths"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_create_volume_add_to_pgs_old_api_fails(self, mock_loose_version):
        """Test create_volume fails when add_to_pgs is used with old API"""
        mock_loose_version.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": ["pg1"],  # add_to_pgs not supported on old API
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version

        try:
            create_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "pgroup parameter" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.check_vgroup")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_create_volume_vgroup_not_exists(
        self, mock_loose_version, mock_check_vgroup
    ):
        """Test create_volume fails when volume group doesn't exist"""
        mock_loose_version.side_effect = float
        mock_check_vgroup.return_value = False

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vgroup1/test_volume",  # Volume in vgroup
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        try:
            create_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "Volume Group does not exist" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_create_volume_pod_not_exists(self, mock_loose_version, mock_check_pod):
        """Test create_volume fails when pod doesn't exist"""
        mock_loose_version.side_effect = float
        mock_check_pod.return_value = False

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::test_volume",  # Volume in pod
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"

        try:
            create_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "Pod does not exist" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_create_volume_in_demoted_pod_fails(
        self, mock_loose_version, mock_check_pod
    ):
        """Test create_volume fails when pod is demoted"""
        mock_loose_version.side_effect = float
        mock_check_pod.return_value = True

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::test_volume",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        # Pod is demoted
        mock_pod = Mock()
        mock_pod.promotion_status = "demoted"

        mock_get_pods_response = Mock()
        mock_get_pods_response.status_code = 200
        mock_get_pods_response.items = [mock_pod]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_pods.return_value = mock_get_pods_response

        try:
            create_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "demoted pod" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.check_pod")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_create_volume_in_pod_old_api(self, mock_loose_version, mock_check_pod):
        """Test create_volume in pod using old API path"""
        mock_loose_version.side_effect = float
        mock_check_pod.return_value = True

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "pod1::test_volume",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        # Pod is demoted (to trigger fail path and verify old API path was used)
        mock_pod = Mock()
        mock_pod.promotion_status = "demoted"

        mock_get_pods_response = Mock()
        mock_get_pods_response.status_code = 200
        mock_get_pods_response.items = [mock_pod]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_pods.return_value = mock_get_pods_response

        try:
            create_volume(mock_module, mock_array)
        except SystemExit:
            pass

        # Verify get_pods was called without context_names
        mock_array.get_pods.assert_called()
        call_kwargs = mock_array.get_pods.call_args[1]
        assert "context_names" not in call_kwargs


class TestCheckVgroupOldApi:
    """Test cases for check_vgroup with old API"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_check_vgroup_old_api(self, mock_loose_version):
        """Test check_vgroup using old API"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {"name": "vgroup1/volume1", "context": "array1"}

        mock_response = Mock()
        mock_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_volume_groups.return_value = mock_response

        result = check_vgroup(mock_module, mock_array)

        assert result is True
        mock_array.get_volume_groups.assert_called_once()
        call_kwargs = mock_array.get_volume_groups.call_args[1]
        assert "context_names" not in call_kwargs


class TestCheckPodOldApi:
    """Test cases for check_pod with old API"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_check_pod_old_api(self, mock_loose_version):
        """Test check_pod using old API"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {"name": "pod1::volume1", "context": "array1"}

        mock_response = Mock()
        mock_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_pods.return_value = mock_response

        result = check_pod(mock_module, mock_array)

        assert result is True
        mock_array.get_pods.assert_called_once()
        call_kwargs = mock_array.get_pods.call_args[1]
        assert "context_names" not in call_kwargs


class TestUpdateVolumeParamValidation:
    """Test cases for update_volume parameter validation"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_update_volume_pgroup_on_new_api_fails(self, mock_loose_version):
        """Test update_volume fails when pgroup is used with new API"""
        mock_loose_version.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "pgroup": "pg1",  # pgroup not supported on new API
            "promotion_state": None,
            "priority_operator": None,
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"  # New API version

        try:
            update_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "add_to_pgs parameter" in call_args["msg"]

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_update_volume_add_to_pgs_on_old_api_fails(self, mock_loose_version):
        """Test update_volume fails when add_to_pgs is used with old API"""
        mock_loose_version.side_effect = float

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": None,
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": ["pg1"],  # add_to_pgs not supported on old API
            "pgroup": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version

        try:
            update_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "pgroup parameter" in call_args["msg"]


class TestGetTargetOldApi:
    """Test cases for get_target with old API"""

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_target_old_api(self, mock_loose_version):
        """Test get_target using old API"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {"target": "target_volume", "context": "array1"}

        mock_volume = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.items = [mock_volume]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_volumes.return_value = mock_response

        result = get_target(mock_module, mock_array)

        assert result == mock_volume
        mock_array.get_volumes.assert_called_once()
        call_kwargs = mock_array.get_volumes.call_args[1]
        assert "context_names" not in call_kwargs

    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_get_target_not_found(self, mock_loose_version):
        """Test get_target returns None when target not found"""
        mock_loose_version.side_effect = float
        mock_module = Mock()
        mock_module.params = {"target": "nonexistent_volume", "context": "array1"}

        mock_response = Mock()
        mock_response.status_code = 400

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_array.get_volumes.return_value = mock_response

        result = get_target(mock_module, mock_array)

        assert result is None


class TestCreateVolumeOldApiPaths:
    """Test cases for create_volume old API paths"""

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    def test_create_volume_basic_old_api(
        self,
        mock_volume_post,
        mock_loose_version,
        mock_human_to_bytes,
        mock_check_response,
    ):
        """Test create_volume basic creation with old API"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "pgroup": None,
            "promotion_state": None,
            "priority_operator": None,
            "context": "array1",
        }

        mock_response = Mock()
        mock_response.status_code = 200

        # Mock get_volumes for _volfact
        mock_vol = Mock()
        mock_vol.name = "test_volume"
        mock_vol.size = 1073741824
        mock_vol.serial = "ABC123"
        mock_vol.created = 1234567890
        mock_vol.provisioned = 1073741824
        mock_vol.space = Mock()
        mock_vol.space.total_provisioned = 1073741824
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.items = [mock_vol]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.post_volumes.return_value = mock_response
        mock_array.get_volumes.return_value = mock_get_response

        create_volume(mock_module, mock_array)

        mock_array.post_volumes.assert_called_once()
        call_kwargs = mock_array.post_volumes.call_args[1]
        assert "context_names" not in call_kwargs
        mock_module.exit_json.assert_called_once()

    @patch("plugins.modules.purefa_volume.check_response")
    @patch("plugins.modules.purefa_volume.human_to_bytes")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    @patch("plugins.modules.purefa_volume.VolumePost")
    @patch("plugins.modules.purefa_volume.VolumePatch")
    def test_create_volume_with_promotion_state_old_api(
        self,
        mock_volume_patch,
        mock_volume_post,
        mock_loose_version,
        mock_human_to_bytes,
        mock_check_response,
    ):
        """Test create_volume with promotion_state using old API"""
        mock_loose_version.side_effect = float
        mock_human_to_bytes.return_value = 1073741824  # 1GB

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test_volume",
            "size": "1G",
            "bw_qos": None,
            "iops_qos": None,
            "add_to_pgs": None,
            "pgroup": None,
            "promotion_state": "demoted",
            "priority_operator": None,
            "context": "array1",
        }

        mock_post_response = Mock()
        mock_post_response.status_code = 200

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200

        # Mock get_volumes for _volfact
        mock_vol = Mock()
        mock_vol.name = "test_volume"
        mock_vol.size = 1073741824
        mock_vol.serial = "ABC123"
        mock_vol.created = 1234567890
        mock_vol.provisioned = 1073741824
        mock_vol.space = Mock()
        mock_vol.space.total_provisioned = 1073741824
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.items = [mock_vol]

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.post_volumes.return_value = mock_post_response
        mock_array.patch_volumes.return_value = mock_patch_response
        mock_array.get_volumes.return_value = mock_get_response

        create_volume(mock_module, mock_array)

        # Verify post_volumes and patch_volumes called without context_names
        post_call_kwargs = mock_array.post_volumes.call_args[1]
        assert "context_names" not in post_call_kwargs
        patch_call_kwargs = mock_array.patch_volumes.call_args[1]
        assert "context_names" not in patch_call_kwargs
        mock_module.exit_json.assert_called_once()


class TestMoveVolumeTargetExists:
    """Test cases for move_volume when target already exists"""

    @patch("plugins.modules.purefa_volume.get_endpoint")
    @patch("plugins.modules.purefa_volume.LooseVersion")
    def test_move_volume_target_already_exists_old_api(
        self, mock_loose_version, mock_get_endpoint
    ):
        """Test move_volume fails when target volume exists on old API"""
        mock_loose_version.side_effect = float
        mock_get_endpoint.return_value = None

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "source_volume",
            "move": "vgroup1",
            "rename": None,
            "context": "array1",
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        # Volume group exists
        mock_vgroup_response = Mock()
        mock_vgroup_response.status_code = 200

        # Target volume already exists
        mock_vol_response = Mock()
        mock_vol_response.status_code = 200

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.0"  # Old API version
        mock_array.get_volume_groups.return_value = mock_vgroup_response
        mock_array.get_volumes.return_value = mock_vol_response

        try:
            move_volume(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "already exists" in call_args["msg"]
