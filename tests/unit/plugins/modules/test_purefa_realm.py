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
        mock_module.params = {
            "name": "new-realm",
            "bw_qos": None,
            "iops_qos": None,
            "quota": None,
        }
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
        mock_module.params = {
            "name": "new-realm",
            "bw_qos": None,
            "iops_qos": None,
            "quota": "5T",
        }
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
        mock_module.params = {
            "name": "test-realm",
            "bw_qos": None,
            "iops_qos": None,
            "quota": None,
        }
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
        mock_module.params = {
            "name": "new-realm",
            "quota": "1M",
            "bw_qos": None,
            "iops_qos": None,
        }
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
        mock_module.params = {
            "name": "new-realm",
            "quota": None,
            "bw_qos": None,
            "iops_qos": None,
        }
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
        mock_module.params = {
            "name": "new-realm",
            "quota": "1M",
            "bw_qos": None,
            "iops_qos": None,
        }
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
        mock_array.patch_realm.return_value = Mock(status_code=200)

        rename_realm(mock_module, mock_array)

        mock_array.patch_realm.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateRealmSuccess:
    """Test cases for update_realm function success scenarios"""

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_update_realm_change_bw_qos(self, mock_human_to_bytes, mock_check_response):
        """Test update_realm changes bandwidth QoS"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-realm",
            "bw_qos": "100M",
            "iops_qos": None,
            "quota": None,
        }
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

        mock_array.patch_realms.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    @patch("plugins.modules.purefa_realm.human_to_real")
    def test_update_realm_change_iops_qos(
        self, mock_human_to_real, mock_human_to_bytes, mock_check_response
    ):
        """Test update_realm changes IOPS QoS"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-realm",
            "bw_qos": None,
            "iops_qos": "10000",
            "quota": None,
        }
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = 1024000
        mock_realm.qos = Mock()
        mock_realm.qos.bandwidth_limit = 50000000
        mock_realm.qos.iops_limit = 5000
        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        mock_array.patch_realms.return_value = Mock(status_code=200)
        mock_human_to_real.return_value = 10000
        mock_human_to_bytes.return_value = 0

        update_realm(mock_module, mock_array)

        mock_array.patch_realms.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_realm.check_response")
    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_update_realm_change_quota(self, mock_human_to_bytes, mock_check_response):
        """Test update_realm changes quota"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-realm",
            "bw_qos": None,
            "iops_qos": None,
            "quota": "100G",
        }
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
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-realm",
            "bw_qos": "1000",  # Too small
            "iops_qos": None,
            "quota": None,
        }
        mock_array = Mock()
        mock_realm = Mock()
        mock_realm.quota_limit = 1024000
        mock_realm.qos = Mock()
        mock_realm.qos.bandwidth_limit = 50000000
        mock_realm.qos.iops_limit = 0
        mock_array.get_realms.return_value = Mock(items=[mock_realm])
        # 1000 bytes is less than 1048576 (1MB) minimum
        mock_human_to_bytes.return_value = 1000

        update_realm(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_realm.human_to_bytes")
    def test_update_realm_quota_not_512_multiple(self, mock_human_to_bytes):
        """Test update_realm fails when quota is not a multiple of 512"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-realm",
            "bw_qos": None,
            "iops_qos": None,
            "quota": "1001",  # Not divisible by 512
        }
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
