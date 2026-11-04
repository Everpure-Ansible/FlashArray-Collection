# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_realm module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock

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

from unittest.mock import patch

from plugins.modules.purefa_realm import (
    get_pending_realm,
    get_realm,
    rename_realm,
    make_realm,
    update_realm,
    delete_realm,
    eradicate_realm,
    recover_realm,
)


def realm_params(**overrides):
    """Every option the module reads, with the QoS and quota options unset"""
    params = {
        "name": "test-realm",
        "bw_qos": None,
        "iops_qos": None,
        "bw_floor": None,
        "iops_floor": None,
        "quota": None,
    }
    params.update(overrides)
    return params


class TestGetPendingRealm:
    """Test cases for get_pending_realm function"""

    def test_get_pending_realm_exists(self):
        """Test get_pending_realm returns destroyed status when realm exists"""
        mock_module = Mock()
        mock_module.params = {"name": "deleted-realm"}
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.destroyed = True
        mock_array.get_realms.return_value = Mock(status_code=200, items=[mock_realm])

        result = get_pending_realm(mock_module, mock_array)

        assert result is True

    def test_get_pending_realm_not_exists(self):
        """Test get_pending_realm returns None when realm doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "realm1"}
        mock_array = Mock()
        mock_array.get_realms.return_value = Mock(status_code=404)

        result = get_pending_realm(mock_module, mock_array)

        assert result is None


class TestGetRealm:
    """Test cases for get_realm function"""

    def test_get_realm_exists(self):
        """Test get_realm returns True when realm exists and not destroyed"""
        mock_module = Mock()
        mock_module.params = {"name": "test-realm"}
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.destroyed = False
        mock_array.get_realms.return_value = Mock(status_code=200, items=[mock_realm])

        result = get_realm(mock_module, mock_array)

        assert result is True

    def test_get_realm_not_exists(self):
        """Test get_realm returns None when realm doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent"}
        mock_array = Mock()
        mock_array.get_realms.return_value = Mock(status_code=404)

        result = get_realm(mock_module, mock_array)

        assert result is None


class TestMakeRealm:
    """Test cases for make_realm function"""

    def test_make_realm_check_mode(self):
        """Test make_realm in check mode makes no API calls (#realm check-mode)"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = realm_params(name="new-realm")
        mock_array = Mock()

        make_realm(mock_module, mock_array)

        # In check mode the realm must NOT be created
        mock_array.post_realms.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_make_realm_check_mode_with_quota(self, mock_human_to_bytes):
        """Test make_realm with quota in check mode makes no API calls"""
        mock_human_to_bytes.return_value = 5497558138880  # 5T, multiple of 512
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = realm_params(name="new-realm", quota="5T")
        mock_array = Mock()

        make_realm(mock_module, mock_array)

        mock_array.post_realms.assert_not_called()
        mock_array.patch_realms.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteRealm:
    """Test cases for delete_realm function"""

    def test_delete_realm_check_mode(self):
        """Test delete_realm in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-realm", "eradicate": False}
        mock_array = Mock()

        delete_realm(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicateRealm:
    """Test cases for eradicate_realm function"""

    def test_eradicate_realm_check_mode(self):
        """Test eradicate_realm in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-realm"}
        mock_array = Mock()

        eradicate_realm(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverRealm:
    """Test cases for recover_realm function"""

    def test_recover_realm_check_mode(self):
        """Test recover_realm in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-realm"}
        mock_array = Mock()

        recover_realm(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenameRealm:
    """Test cases for rename_realm function"""

    @patch("plugins.modules.purefa_realm.check_response")
    def test_rename_realm_check_mode(self, mock_check_response):
        """Test rename_realm in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "old-realm", "rename": "new-realm"}
        mock_array = Mock()

        rename_realm(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateRealm:
    """Test cases for update_realm function"""

    def test_update_realm_no_changes(self):
        """Test update_realm with no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = realm_params()
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = None
        mock_realm.qos = Mock(bandwidth_limit=None, iops_limit=None)
        mock_array.get_realms.return_value.items = [mock_realm]

        update_realm(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestMakeRealmSuccess:
    """Additional test cases for make_realm function"""

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_make_realm_with_quota(self, mock_human_to_bytes, mock_check_response):
        """Test make_realm with valid quota"""
        mock_human_to_bytes.return_value = 1048576  # 1MB - valid quota
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = realm_params(name="new-realm", quota="1M")
        mock_array = Mock()
        mock_array.post_realms.return_value = Mock(status_code=200)

        make_realm(mock_module, mock_array)

        mock_array.post_realms.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.check_response")
    def test_make_realm_no_quota(self, mock_check_response):
        """Test make_realm without quota"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = realm_params(name="new-realm")
        mock_array = Mock()
        mock_array.post_realms.return_value = Mock(status_code=200)

        make_realm(mock_module, mock_array)

        mock_array.post_realms.assert_called_once_with(names=["new-realm"])
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_make_realm_invalid_quota_not_512_multiple(self, mock_human_to_bytes):
        """Test make_realm fails with quota not multiple of 512"""
        import pytest

        mock_human_to_bytes.return_value = 1048577  # Not multiple of 512
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = realm_params(name="new-realm", quota="1M")
        mock_array = Mock()

        with pytest.raises(SystemExit):
            make_realm(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestDeleteRealmSuccess:
    """Additional test cases for delete_realm function"""

    @patch("plugins.modules.purefa_realm.check_response")
    def test_delete_realm_success(self, mock_check_response):
        """Test delete_realm successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-realm",
            "eradicate": False,
            "delete_contents": False,
            "ignore_usage": False,
        }
        mock_array = Mock()
        mock_array.patch_realms.return_value = Mock(status_code=200)

        delete_realm(mock_module, mock_array)

        mock_array.patch_realms.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRecoverRealmSuccess:
    """Additional test cases for recover_realm function"""

    @patch("plugins.modules.purefa_realm.check_response")
    def test_recover_realm_success(self, mock_check_response):
        """Test recover_realm successfully recovers"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "deleted-realm"}
        mock_array = Mock()
        mock_array.patch_realms.return_value = Mock(status_code=200)

        recover_realm(mock_module, mock_array)

        mock_array.patch_realms.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEradicateRealmSuccess:
    """Additional test cases for eradicate_realm function"""

    @patch("plugins.modules.purefa_realm.check_response")
    def test_eradicate_realm_success(self, mock_check_response):
        """Test eradicate_realm successfully eradicates"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "deleted-realm", "delete_contents": False}
        mock_array = Mock()
        mock_array.delete_realms.return_value = Mock(status_code=200)

        eradicate_realm(mock_module, mock_array)

        mock_array.delete_realms.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestRenameRealmSuccess:
    """Additional test cases for rename_realm function"""

    @patch("plugins.modules.purefa_realm.check_response")
    def test_rename_realm_success(self, mock_check_response):
        """Test rename_realm successfully renames"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "old-realm", "rename": "new-realm"}
        mock_array = Mock()
        mock_array.patch_realms.return_value = Mock(status_code=200)

        rename_realm(mock_module, mock_array)

        mock_array.patch_realms.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateRealmSuccess:
    """Test cases for update_realm function success scenarios"""

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    @patch("plugins.modules.purefa_realm.RealmPatch")
    @patch("plugins.modules.purefa_realm.ContainerQos")
    def test_update_realm_change_bw_qos(
        self, mock_cq, mock_realm_patch, mock_human_to_bytes, mock_check_response
    ):
        """Test update_realm changes bandwidth QoS"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = realm_params(bw_qos="100M")
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = 1024000
        mock_realm.qos = Mock()
        mock_realm.qos.bandwidth_limit = 50000000
        mock_realm.qos.iops_limit = 1000
        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        mock_array.patch_realms.return_value = Mock(status_code=200)
        # 100MB is 104857600 bytes
        mock_human_to_bytes.return_value = 104857600

        update_realm(mock_module, mock_array)

        mock_cq.assert_called_once_with(bandwidth_limit=104857600)
        mock_realm_patch.assert_called_once_with(qos=mock_cq.return_value)
        mock_array.patch_realms.assert_called_once_with(
            names=["test-realm"], realm=mock_realm_patch.return_value
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    @patch("plugins.modules.purefa_realm.human_to_real")
    @patch("plugins.modules.purefa_realm.RealmPatch")
    @patch("plugins.modules.purefa_realm.ContainerQos")
    def test_update_realm_change_iops_qos(
        self,
        mock_cq,
        mock_realm_patch,
        mock_human_to_real,
        mock_human_to_bytes,
        mock_check_response,
    ):
        """Test update_realm changes IOPS QoS"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = realm_params(iops_qos="10000")
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = 1024000
        mock_realm.qos = Mock()
        mock_realm.qos.bandwidth_limit = 50000000
        mock_realm.qos.iops_limit = 5000
        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        mock_array.patch_realms.return_value = Mock(status_code=200)
        # The real helper hands a unit-less value back as the string it got
        mock_human_to_real.return_value = "10000"
        mock_human_to_bytes.return_value = 0

        update_realm(mock_module, mock_array)

        mock_cq.assert_called_once_with(iops_limit=10000)
        mock_realm_patch.assert_called_once_with(qos=mock_cq.return_value)
        mock_array.patch_realms.assert_called_once_with(
            names=["test-realm"], realm=mock_realm_patch.return_value
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_update_realm_change_quota(self, mock_human_to_bytes, mock_check_response):
        """Test update_realm changes quota"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = realm_params(quota="100G")
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = 1024000
        mock_realm.qos = Mock()
        mock_realm.qos.bandwidth_limit = 0
        mock_realm.qos.iops_limit = 0
        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        mock_array.patch_realms.return_value = Mock(status_code=200)
        # 100GB = 107374182400 bytes (divisible by 512)
        mock_human_to_bytes.return_value = 107374182400

        update_realm(mock_module, mock_array)

        mock_array.patch_realms.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_update_realm_bw_qos_out_of_range(self, mock_human_to_bytes):
        """Test update_realm fails when bandwidth QoS is out of range"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = realm_params(bw_qos="1000")  # Too small
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = 1024000
        mock_realm.qos = Mock()
        mock_realm.qos.bandwidth_limit = 50000000
        mock_realm.qos.iops_limit = 0
        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        # 1000 bytes is less than 1048576 (1MB) minimum
        mock_human_to_bytes.return_value = 1000

        with pytest.raises(SystemExit):
            update_realm(mock_module, mock_array)

        mock_module.fail_json.assert_called_once_with(
            msg="Bandwidth QoS value 1000 out of range."
        )
        mock_array.patch_realms.assert_not_called()

    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_update_realm_quota_not_512_multiple(self, mock_human_to_bytes):
        """Test update_realm fails when quota is not a multiple of 512"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = realm_params(quota="1001")  # Not divisible by 512
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = 1024000
        mock_realm.qos = Mock()
        mock_realm.qos.bandwidth_limit = 0
        mock_realm.qos.iops_limit = 0
        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        mock_human_to_bytes.return_value = 1001  # Not divisible by 512

        update_realm(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestRealmQosClear:
    """bw_qos / iops_qos of "0" or "" remove the limit"""

    @staticmethod
    def _module(bw_qos=None, iops_qos=None):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = realm_params(bw_qos=bw_qos, iops_qos=iops_qos)
        return mock_module

    @staticmethod
    def _array(bandwidth_limit, iops_limit):
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = None
        mock_realm.qos = Mock()
        mock_realm.qos.bandwidth_limit = bandwidth_limit
        mock_realm.qos.iops_limit = iops_limit
        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        mock_array.patch_realms.return_value = Mock(status_code=200)
        return mock_array

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.RealmPatch")
    @patch("plugins.modules.purefa_realm.ContainerQosPatch")
    def test_bw_qos_zero_clears_limit(
        self, mock_cqp, mock_realm_patch, mock_check_response
    ):
        mock_module = self._module(bw_qos="0")
        mock_array = self._array(50000000, 1000)

        update_realm(mock_module, mock_array)

        mock_cqp.assert_called_once_with(bandwidth_limit="")
        mock_realm_patch.assert_called_once_with(qos=mock_cqp.return_value)
        mock_array.patch_realms.assert_called_once_with(
            names=["test-realm"], realm=mock_realm_patch.return_value
        )
        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.RealmPatch")
    @patch("plugins.modules.purefa_realm.ContainerQosPatch")
    def test_iops_qos_zero_clears_limit(
        self, mock_cqp, mock_realm_patch, mock_check_response
    ):
        mock_module = self._module(iops_qos="0")
        mock_array = self._array(None, 1000)

        update_realm(mock_module, mock_array)

        mock_cqp.assert_called_once_with(iops_limit="")
        mock_realm_patch.assert_called_once_with(qos=mock_cqp.return_value)
        mock_array.patch_realms.assert_called_once_with(
            names=["test-realm"], realm=mock_realm_patch.return_value
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.ContainerQosPatch")
    def test_clear_when_unset_is_noop(self, mock_cqp):
        mock_module = self._module(bw_qos="", iops_qos="0")
        mock_array = self._array(None, None)

        update_realm(mock_module, mock_array)

        mock_array.patch_realms.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestRealmQosFloors:
    """bw_floor / iops_floor set, change and clear the container QoS floors"""

    @staticmethod
    def _module(**params):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = realm_params(**params)
        return mock_module

    @staticmethod
    def _array(
        bandwidth_limit=None, iops_limit=None, bandwidth_floor=None, iops_floor=None
    ):
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = None
        mock_realm.qos = Mock()
        mock_realm.qos.bandwidth_limit = bandwidth_limit
        mock_realm.qos.iops_limit = iops_limit
        mock_realm.qos.bandwidth_floor = bandwidth_floor
        mock_realm.qos.iops_floor = iops_floor
        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        mock_array.patch_realms.return_value = Mock(status_code=200)
        mock_array.post_realms.return_value = Mock(status_code=200)
        return mock_array

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_real")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    @patch("plugins.modules.purefa_realm.RealmPatch")
    @patch("plugins.modules.purefa_realm.ContainerQos")
    def test_floors_and_limit_sent_in_one_patch(
        self,
        mock_cq,
        mock_realm_patch,
        mock_human_to_bytes,
        mock_human_to_real,
        mock_check_response,
    ):
        """Limits and floors given together make a single PATCH"""
        mock_human_to_bytes.side_effect = lambda value: {
            "2G": 2147483648,
            "500M": 524288000,
        }[value]
        mock_human_to_real.return_value = 20000
        mock_module = self._module(bw_qos="2G", bw_floor="500M", iops_floor="20K")
        mock_array = self._array(bandwidth_limit=1048576)

        update_realm(mock_module, mock_array)

        mock_cq.assert_called_once_with(
            bandwidth_limit=2147483648, bandwidth_floor=524288000, iops_floor=20000
        )
        mock_realm_patch.assert_called_once_with(qos=mock_cq.return_value)
        mock_array.patch_realms.assert_called_once_with(
            names=["test-realm"], realm=mock_realm_patch.return_value
        )
        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.human_to_real")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_floors_already_set_is_noop(self, mock_human_to_bytes, mock_human_to_real):
        mock_human_to_bytes.return_value = 524288000
        mock_human_to_real.return_value = 20000
        mock_module = self._module(bw_floor="500M", iops_floor="20K")
        mock_array = self._array(bandwidth_floor=524288000, iops_floor=20000)

        update_realm(mock_module, mock_array)

        mock_array.patch_realms.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_realm.human_to_real")
    def test_unitless_iops_floor_already_set_is_noop(self, mock_human_to_real):
        """A unit-less IOPs value comes back from the helper as a string"""
        mock_human_to_real.return_value = "1500"
        mock_module = self._module(iops_floor="1500")
        mock_array = self._array(iops_floor=1500)

        update_realm(mock_module, mock_array)

        mock_array.patch_realms.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.RealmPatch")
    @patch("plugins.modules.purefa_realm.ContainerQosPatch")
    def test_floor_zero_clears_floor(
        self, mock_cqp, mock_realm_patch, mock_check_response
    ):
        mock_module = self._module(bw_floor="0", iops_floor="0")
        mock_array = self._array(bandwidth_floor=524288000, iops_floor=None)

        update_realm(mock_module, mock_array)

        # Only the floor that is set needs clearing
        mock_cqp.assert_called_once_with(bandwidth_floor="")
        mock_realm_patch.assert_called_once_with(qos=mock_cqp.return_value)
        mock_array.patch_realms.assert_called_once_with(
            names=["test-realm"], realm=mock_realm_patch.return_value
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_real")
    @patch("plugins.modules.purefa_realm.RealmPatch")
    @patch("plugins.modules.purefa_realm.ContainerQosPatch")
    def test_set_and_clear_share_one_patch(
        self, mock_cqp, mock_realm_patch, mock_human_to_real, mock_check_response
    ):
        """A clear and a new value in the same task use the patch model once"""
        # The real helper hands a unit-less value back as the string it got
        mock_human_to_real.return_value = "200"
        mock_module = self._module(iops_qos="200", bw_floor="")
        mock_array = self._array(iops_limit=100, bandwidth_floor=1048576)

        update_realm(mock_module, mock_array)

        mock_cqp.assert_called_once_with(iops_limit=200, bandwidth_floor="")
        mock_realm_patch.assert_called_once_with(qos=mock_cqp.return_value)
        mock_array.patch_realms.assert_called_once_with(
            names=["test-realm"], realm=mock_realm_patch.return_value
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_real")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    @patch("plugins.modules.purefa_realm.RealmPatch")
    @patch("plugins.modules.purefa_realm.ContainerQos")
    def test_maximum_values_are_in_range(
        self,
        mock_cq,
        mock_realm_patch,
        mock_human_to_bytes,
        mock_human_to_real,
        mock_check_response,
    ):
        """The documented maxima (512G, 100M IOPs) are accepted, not rejected"""
        mock_human_to_bytes.return_value = 549755813888
        mock_human_to_real.return_value = 100000000
        mock_module = self._module(bw_qos="512G", iops_floor="100M")
        mock_array = self._array()

        update_realm(mock_module, mock_array)

        mock_module.fail_json.assert_not_called()
        mock_cq.assert_called_once_with(
            bandwidth_limit=549755813888, iops_floor=100000000
        )
        mock_realm_patch.assert_called_once_with(qos=mock_cq.return_value)
        mock_array.patch_realms.assert_called_once_with(
            names=["test-realm"], realm=mock_realm_patch.return_value
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_floor_out_of_range_fails(self, mock_human_to_bytes):
        mock_human_to_bytes.return_value = 1048575
        mock_module = self._module(bw_floor="1048575")
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = self._array()
        import pytest

        with pytest.raises(SystemExit):
            update_realm(mock_module, mock_array)

        mock_module.fail_json.assert_called_once_with(
            msg="Bandwidth floor value 1048575 out of range."
        )
        mock_array.patch_realms.assert_not_called()

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_real")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    @patch("plugins.modules.purefa_realm.RealmPost")
    @patch("plugins.modules.purefa_realm.ContainerQos")
    def test_make_realm_sets_qos_in_the_create_call(
        self,
        mock_cq,
        mock_realm_post,
        mock_human_to_bytes,
        mock_human_to_real,
        mock_check_response,
    ):
        """A new realm is created with quota and QoS in one POST"""
        mock_human_to_bytes.side_effect = lambda value: {
            "10G": 10737418240,
            "2G": 2147483648,
            "500M": 524288000,
        }[value]
        mock_human_to_real.return_value = 20000
        mock_module = self._module(
            name="new-realm",
            quota="10G",
            bw_qos="2G",
            bw_floor="500M",
            iops_floor="20K",
        )
        mock_array = self._array()

        make_realm(mock_module, mock_array)

        mock_cq.assert_called_once_with(
            bandwidth_limit=2147483648, bandwidth_floor=524288000, iops_floor=20000
        )
        mock_realm_post.assert_called_once_with(
            quota_limit=10737418240, qos=mock_cq.return_value
        )
        mock_array.post_realms.assert_called_once_with(
            names=["new-realm"], realm=mock_realm_post.return_value
        )
        mock_array.patch_realms.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_real")
    @patch("plugins.modules.purefa_realm.RealmPost")
    @patch("plugins.modules.purefa_realm.ContainerQos")
    def test_make_realm_ignores_clear_requests(
        self, mock_cq, mock_realm_post, mock_human_to_real, mock_check_response
    ):
        """A 0 on create has nothing to clear and must not be an error"""
        mock_human_to_real.return_value = 1000
        mock_module = self._module(name="new-realm", bw_qos="0", iops_floor="1K")
        mock_array = self._array()

        make_realm(mock_module, mock_array)

        mock_module.fail_json.assert_not_called()
        mock_cq.assert_called_once_with(iops_floor=1000)
        mock_realm_post.assert_called_once_with(qos=mock_cq.return_value)
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_make_realm_out_of_range_floor_creates_nothing(self, mock_human_to_bytes):
        mock_human_to_bytes.return_value = 549755813889
        mock_module = self._module(name="new-realm", bw_floor="513G")
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = self._array()
        import pytest

        with pytest.raises(SystemExit):
            make_realm(mock_module, mock_array)

        mock_array.post_realms.assert_not_called()


class TestFloorVersionGate:
    """Floors are refused below REST 2.47; the gate is skipped otherwise"""

    @staticmethod
    def _run_main(params, mock_ansible, mock_get_array):
        import pytest
        from packaging.version import Version
        from plugins.modules.purefa_realm import main

        mock_module = Mock()
        mock_module.params = params
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.40"
        mock_array.get_realms.return_value = Mock(status_code=400)
        mock_get_array.return_value = mock_array

        with patch("plugins.modules.purefa_realm.LooseVersion", side_effect=Version):
            with pytest.raises(SystemExit):
                main()
        return mock_module, mock_array

    @staticmethod
    def _params(**overrides):
        params = realm_params(
            name="new-realm",
            rename=None,
            state="present",
            eradicate=False,
            delete_contents=False,
            ignore_usage=False,
        )
        params.update(overrides)
        return params

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.check_api_version")
    @patch("plugins.modules.purefa_realm.get_array")
    @patch("plugins.modules.purefa_realm.AnsibleModule")
    def test_floor_option_checks_api_version(
        self, mock_ansible, mock_get_array, mock_check_api_version, mock_check_response
    ):
        mock_check_api_version.side_effect = SystemExit(1)

        mock_module, mock_array = self._run_main(
            self._params(bw_floor="100M"), mock_ansible, mock_get_array
        )

        mock_check_api_version.assert_called_once_with(
            mock_array, "2.47", mock_module, "Realm QoS floor support"
        )
        mock_array.post_realms.assert_not_called()

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.check_api_version")
    @patch("plugins.modules.purefa_realm.get_array")
    @patch("plugins.modules.purefa_realm.AnsibleModule")
    def test_no_floor_option_skips_the_check(
        self, mock_ansible, mock_get_array, mock_check_api_version, mock_check_response
    ):
        mock_module, mock_array = self._run_main(
            self._params(), mock_ansible, mock_get_array
        )

        mock_check_api_version.assert_not_called()
        mock_array.post_realms.assert_called_once_with(names=["new-realm"])


class TestRenameRepeat:
    """Re-running a completed rename must not recreate the old realm"""

    @patch("plugins.modules.purefa_realm.get_array")
    @patch("plugins.modules.purefa_realm.AnsibleModule")
    def test_rename_repeat_reports_no_change(self, mock_ansible, mock_get_array):
        import pytest
        from packaging.version import Version
        from plugins.modules.purefa_realm import main

        mock_module = Mock()
        mock_module.params = realm_params(
            name="old-realm",
            rename="new-realm",
            state="present",
            eradicate=False,
            delete_contents=False,
            ignore_usage=False,
        )
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_ansible.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        target = Mock()
        target.destroyed = False

        def get_realms(names):
            if names == ["new-realm"]:
                return Mock(status_code=200, items=[target])
            return Mock(status_code=400)

        mock_array.get_realms.side_effect = get_realms
        mock_get_array.return_value = mock_array

        with patch("plugins.modules.purefa_realm.LooseVersion", side_effect=Version):
            with pytest.raises(SystemExit):
                main()

        mock_array.post_realms.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)
