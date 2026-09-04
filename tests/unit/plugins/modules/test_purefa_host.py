# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_host module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, patch, MagicMock

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

from plugins.modules.purefa_host import (
    _is_cbs,
    get_host,
    get_multi_hosts,
    rename_exists,
    make_host,
    make_multi_hosts,
    delete_host,
    update_host,
    _set_host_personality,
    _set_preferred_array,
    _set_chap_security,
    _set_vlan,
    _update_vlan,
    _update_preferred_array,
    _set_host_initiators,
    _update_host_initiators,
    _update_host_personality,
    _update_chap_security,
)


class TestIsCbs:
    """Test cases for _is_cbs function"""

    def test_is_cbs_true(self):
        """Test CBS detection returns True for CBS model"""
        mock_array = Mock()
        mock_array.get_controllers.return_value = Mock(items=[Mock(model="CBS-V10")])
        result = _is_cbs(mock_array)
        assert result is True

    def test_is_cbs_false(self):
        """Test CBS detection returns False for non-CBS model"""
        mock_array = Mock()
        mock_array.get_controllers.return_value = Mock(items=[Mock(model="FA-X70R3")])
        result = _is_cbs(mock_array)
        assert result is False


class TestGetHost:
    """Test cases for get_host function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_get_host_exists(self, mock_get_with_context):
        """Test get_host returns host when it exists"""
        mock_module = Mock()
        mock_module.params = {"name": "test-host"}
        mock_array = Mock()

        mock_host = Mock()
        mock_host.name = "test-host"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        result = get_host(mock_module, mock_array)

        assert result == mock_host
        assert "allow_errors" not in mock_get_with_context.call_args.kwargs

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_get_host_not_exists(self, mock_get_with_context):
        """Test get_host returns None when host doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent-host"}
        mock_array = Mock()

        mock_get_with_context.return_value = Mock(status_code=200, items=[])

        result = get_host(mock_module, mock_array)

        assert result is None
        assert "allow_errors" not in mock_get_with_context.call_args.kwargs

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_get_host_no_allow_errors_without_context(self, mock_get_with_context):
        """Without a context, allow_errors must NOT be sent (#1016).

        allow_errors only exists on the hosts GET endpoint from REST 2.38;
        sending it unconditionally broke pre-2.38 arrays with
        "get_hosts() got an unexpected keyword argument 'allow_errors'".
        """
        mock_module = Mock()
        mock_module.params = {"name": "test-host", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200, items=[Mock()])

        get_host(mock_module, mock_array)

        assert "allow_errors" not in mock_get_with_context.call_args.kwargs

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_get_host_allow_errors_with_context(self, mock_get_with_context):
        """With a context set, allow_errors is sent so a missing name in the
        context returns partial results instead of a 400 (#1016)."""
        mock_module = Mock()
        mock_module.params = {"name": "test-host", "context": "fleet-member1"}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200, items=[Mock()])

        get_host(mock_module, mock_array)

        assert mock_get_with_context.call_args.kwargs["allow_errors"] is True


class TestGetMultiHosts:
    """Test cases for get_multi_hosts function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_get_multi_hosts_all_exist(self, mock_get_with_context):
        """Test get_multi_hosts returns True when all hosts exist"""
        mock_module = Mock()
        mock_module.params = {
            "name": "host",
            "start": 0,
            "count": 3,
            "digits": 2,
            "suffix": None,
        }
        mock_array = Mock()

        mock_get_with_context.return_value = Mock(
            status_code=200, items=[Mock(), Mock(), Mock()]
        )

        result = get_multi_hosts(mock_module, mock_array)

        assert result is True
        assert "allow_errors" not in mock_get_with_context.call_args.kwargs

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_get_multi_hosts_not_exist(self, mock_get_with_context):
        """Test get_multi_hosts returns False when hosts don't exist"""
        mock_module = Mock()
        mock_module.params = {
            "name": "host",
            "start": 0,
            "count": 3,
            "digits": 2,
            "suffix": None,
        }
        mock_array = Mock()

        mock_get_with_context.return_value = Mock(
            status_code=207, items=[Mock(), Mock()]
        )

        result = get_multi_hosts(mock_module, mock_array)

        assert result is False
        assert "allow_errors" not in mock_get_with_context.call_args.kwargs

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_get_multi_hosts_with_suffix(self, mock_get_with_context):
        """Test get_multi_hosts with suffix"""
        mock_module = Mock()
        mock_module.params = {
            "name": "host",
            "start": 1,
            "count": 2,
            "digits": 3,
            "suffix": "_server",
        }
        mock_array = Mock()

        mock_get_with_context.return_value = Mock(
            status_code=200, items=[Mock(), Mock()]
        )

        result = get_multi_hosts(mock_module, mock_array)

        assert result is True
        # Verify the hosts list includes suffix
        call_args = mock_get_with_context.call_args
        assert "allow_errors" not in call_args.kwargs
        assert "host001_server" in call_args.kwargs["names"]
        assert "host002_server" in call_args.kwargs["names"]


class TestRenameExists:
    """Test cases for rename_exists function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_rename_exists_true(self, mock_get_with_context):
        """Test rename_exists returns True when target exists"""
        mock_module = Mock()
        mock_module.params = {"rename": "new-host-name"}
        mock_array = Mock()

        mock_get_with_context.return_value = Mock(status_code=200, items=[Mock()])

        result = rename_exists(mock_module, mock_array)

        assert result is True
        assert "allow_errors" not in mock_get_with_context.call_args.kwargs

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_rename_exists_false(self, mock_get_with_context):
        """Test rename_exists returns False when target doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"rename": "new-host-name"}
        mock_array = Mock()

        mock_get_with_context.return_value = Mock(status_code=200, items=[])

        result = rename_exists(mock_module, mock_array)

        assert result is False
        assert "allow_errors" not in mock_get_with_context.call_args.kwargs


class TestMakeHost:
    """Test cases for make_host function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.check_response")
    def test_make_host_check_mode(self, mock_check_response, mock_get_with_context):
        """Test make_host in check mode doesn't make API calls"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-host"}
        mock_array = Mock()

        make_host(mock_module, mock_array)

        mock_get_with_context.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host._set_host_initiators")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.check_response")
    def test_make_host_basic(
        self, mock_check_response, mock_get_with_context, mock_set_initiators
    ):
        """Test basic host creation"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "vlan": None,
            "personality": None,
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "volume": None,
            "nqn": None,
            "iqn": None,
            "wwns": None,
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        make_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMakeMultiHosts:
    """Test cases for make_multi_hosts function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.check_response")
    def test_make_multi_hosts_check_mode(
        self, mock_check_response, mock_get_with_context
    ):
        """Test make_multi_hosts in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "host",
            "start": 0,
            "count": 3,
            "digits": 2,
            "suffix": None,
        }
        mock_array = Mock()

        make_multi_hosts(mock_module, mock_array)

        mock_get_with_context.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_make_multi_hosts_with_suffix(
        self, mock_get_with_context, mock_check_response
    ):
        """Test make_multi_hosts with suffix"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "host",
            "start": 1,
            "count": 3,
            "digits": 2,
            "suffix": "-prod",
            "personality": None,
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        make_multi_hosts(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        # Verify host names were created with suffix
        call_args = mock_get_with_context.call_args
        assert "host01-prod" in call_args.kwargs["names"]
        assert "host02-prod" in call_args.kwargs["names"]
        assert "host03-prod" in call_args.kwargs["names"]
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_make_multi_hosts_without_suffix(
        self, mock_get_with_context, mock_check_response
    ):
        """Test make_multi_hosts without suffix"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "server",
            "start": 0,
            "count": 2,
            "digits": 3,
            "suffix": None,
            "personality": None,
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        make_multi_hosts(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        # Verify host names were created without suffix
        call_args = mock_get_with_context.call_args
        assert "server000" in call_args.kwargs["names"]
        assert "server001" in call_args.kwargs["names"]
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_make_multi_hosts_with_personality(
        self, mock_get_with_context, mock_check_response
    ):
        """Test make_multi_hosts with personality set"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "esx",
            "start": 1,
            "count": 2,
            "digits": 2,
            "suffix": None,
            "personality": "esxi",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        make_multi_hosts(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteHost:
    """Test cases for delete_host function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.check_response")
    def test_delete_host_check_mode(self, mock_check_response, mock_get_with_context):
        """Test delete_host in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-host"}
        mock_array = Mock()

        delete_host(mock_module, mock_array)

        mock_get_with_context.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.check_response")
    def test_delete_host_no_volumes(self, mock_check_response, mock_get_with_context):
        """Test delete_host with no connected volumes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-host"}
        mock_array = Mock()

        # Mock host without host group
        mock_host = Mock()
        mock_host.host_group = Mock(spec=[])  # No name attribute
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_host]),  # get_hosts
            Mock(status_code=200, items=[]),  # get_connections (no volumes)
            Mock(status_code=200),  # delete_hosts
        ]

        delete_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateHost:
    """Test cases for update_host function"""

    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host.LooseVersion")
    def test_update_host_no_changes(self, mock_loose_version, mock_get_api_version):
        """Test update_host with no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "state": "present",
            "vlan": None,
            "rename": None,
            "personality": None,
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "target_password": None,
            "volume": None,
            "nqn": None,
            "iqn": None,
            "wwns": None,
        }
        mock_array = Mock()
        mock_get_api_version.return_value = "2.0"
        mock_loose_version.side_effect = float

        update_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once()


class TestSetHostPersonality:
    """Test cases for _set_host_personality function"""

    @patch(
        "plugins.modules.purefa_host.get_with_context",
    )
    @patch("plugins.modules.purefa_host.check_response")
    def test_set_host_personality_success(
        self, mock_check_response, mock_get_with_context
    ):
        """Test setting host personality"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "personality": "hpux",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        mock_check_response.return_value = None

        _set_host_personality(mock_module, mock_array)

        mock_get_with_context.assert_called()


class TestSetPreferredArray:
    """Test cases for _set_preferred_array function"""

    @patch(
        "plugins.modules.purefa_host.get_with_context",
    )
    @patch("plugins.modules.purefa_host.check_response")
    def test_set_preferred_array_success(
        self, mock_check_response, mock_get_with_context
    ):
        """Test setting preferred array list"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "preferred_array": ["array1", "array2"],
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        mock_check_response.return_value = None

        _set_preferred_array(mock_module, mock_array)

        mock_get_with_context.assert_called()

    @patch(
        "plugins.modules.purefa_host.get_with_context",
    )
    @patch("plugins.modules.purefa_host.check_response")
    def test_set_preferred_array_delete(
        self, mock_check_response, mock_get_with_context
    ):
        """Test deleting preferred array list"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "preferred_array": ["delete"],
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        mock_check_response.return_value = None

        _set_preferred_array(mock_module, mock_array)

        # When preferred_array is ["delete"], the function sets an empty list
        mock_get_with_context.assert_called()


class TestSetChapSecurity:
    """Test cases for _set_chap_security function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.check_response")
    def test_set_chap_host_user(self, mock_check_response, mock_get_with_context):
        """Test setting CHAP host user"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "host_user": "hostuser",
            "host_password": "supersecretpassword123",  # 12+ chars
            "target_user": None,
            "target_password": None,
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        mock_check_response.return_value = None

        _set_chap_security(mock_module, mock_array)

        mock_get_with_context.assert_called()

    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.check_response")
    def test_set_chap_target_user(self, mock_check_response, mock_get_with_context):
        """Test setting CHAP target user"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "host_user": None,
            "host_password": None,
            "target_user": "targetuser",
            "target_password": "anothersecretpassword123",  # 12+ chars
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        mock_check_response.return_value = None

        _set_chap_security(mock_module, mock_array)

        mock_get_with_context.assert_called()


class TestSetVlan:
    """Test cases for _set_vlan function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_set_vlan_success(self, mock_get_with_context):
        """Test setting VLAN successfully"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "vlan": "100",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        _set_vlan(mock_module, mock_array)

        mock_get_with_context.assert_called()


class TestUpdateVlan:
    """Test cases for _update_vlan function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_vlan_no_change(self, mock_get_with_context):
        """Test update_vlan when VLAN matches"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "vlan": "100",
            "context": "",
        }
        mock_array = Mock()
        mock_host = Mock()
        mock_host.vlan = "100"
        mock_get_with_context.return_value = Mock(items=[mock_host])

        result = _update_vlan(mock_module, mock_array)

        assert result is False

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_vlan_change_check_mode(self, mock_get_with_context):
        """Test update_vlan in check mode when VLAN differs"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-host",
            "vlan": "200",
            "context": "",
        }
        mock_array = Mock()
        mock_host = Mock()
        mock_host.vlan = "100"
        mock_get_with_context.return_value = Mock(items=[mock_host])

        result = _update_vlan(mock_module, mock_array)

        assert result is True


class TestMoveHost:
    """Test cases for move_host function"""

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_move_host_fail_with_context(self, mock_get_with_context):
        """Test move_host fails when context is provided"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "test-host",
            "context": "realm1",
        }
        mock_array = Mock()

        from plugins.modules.purefa_host import move_host

        with pytest.raises(SystemExit):
            move_host(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_move_host_with_connections_fails(self, mock_get_with_context):
        """Test move_host fails when host has connections"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "test-host",
            "context": "",
            "move": ["realm1"],
        }
        mock_array = Mock()
        # Mock get_arrays
        mock_local_array = Mock()
        mock_local_array.name = "local-array"
        mock_array.get_arrays.return_value.items = [mock_local_array]

        # Mock host with connections
        mock_host = Mock()
        mock_host.connection_count = 5
        mock_get_with_context.return_value = Mock(items=[mock_host])

        from plugins.modules.purefa_host import move_host

        with pytest.raises(SystemExit):
            move_host(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestMakeHostSuccess:
    """Test cases for make_host success paths"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_make_host_success(self, mock_get_with_context, mock_check_response):
        """Test make_host creates host successfully"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "context": "",
            "vlan": None,
            "personality": None,
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "volume": None,
            "lun": None,
            "wwns": None,
            "iqn": None,
            "nqn": None,
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        make_host(mock_module, mock_array)

        mock_get_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host._set_vlan")
    def test_make_host_with_vlan(
        self, mock_set_vlan, mock_get_with_context, mock_check_response
    ):
        """Test make_host creates host with VLAN"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "context": "",
            "vlan": "100",
            "personality": None,
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "volume": None,
            "lun": None,
            "wwns": None,
            "iqn": None,
            "nqn": None,
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        make_host(mock_module, mock_array)

        mock_set_vlan.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteHostSuccess:
    """Test cases for delete_host success paths"""

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_delete_host_success(self, mock_get_with_context):
        """Test delete_host successfully deletes host"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "context": "",
        }
        mock_array = Mock()

        # Mock the host with no host_group
        mock_host = Mock()
        mock_host.host_group = None

        def side_effect(*args, **kwargs):
            if args[1] == "get_hosts":
                return Mock(items=[mock_host], status_code=200)
            elif args[1] == "get_connections":
                return Mock(items=[], status_code=200)
            else:
                return Mock(status_code=200)

        mock_get_with_context.side_effect = side_effect

        delete_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestConnectNewVolume:
    """Test cases for _connect_new_volume function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_connect_new_volume_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test connecting a new volume to a host"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
            "lun": None,
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        from plugins.modules.purefa_host import _connect_new_volume

        result = _connect_new_volume(mock_module, mock_array)

        assert result is True
        mock_get_with_context.assert_called_once()

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_connect_new_volume_with_lun(
        self, mock_get_with_context, mock_check_response
    ):
        """Test connecting a volume with specific LUN"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
            "lun": 10,
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        from plugins.modules.purefa_host import _connect_new_volume

        result = _connect_new_volume(mock_module, mock_array)

        assert result is True
        # Verify ConnectionPost was called with LUN
        call_kwargs = mock_get_with_context.call_args[1]
        assert "connection" in call_kwargs

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_connect_new_volume_check_mode(
        self, mock_get_with_context, mock_check_response
    ):
        """Test connecting volume in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
            "lun": None,
        }
        mock_array = Mock()

        from plugins.modules.purefa_host import _connect_new_volume

        result = _connect_new_volume(mock_module, mock_array)

        assert result is True
        mock_get_with_context.assert_not_called()


class TestDisconnectVolume:
    """Test cases for _disconnect_volume function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_disconnect_volume_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test disconnecting a volume from a host"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        from plugins.modules.purefa_host import _disconnect_volume

        result = _disconnect_volume(mock_module, mock_array)

        assert result is True
        mock_get_with_context.assert_called_once()

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_disconnect_volume_check_mode(
        self, mock_get_with_context, mock_check_response
    ):
        """Test disconnecting volume in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
        }
        mock_array = Mock()

        from plugins.modules.purefa_host import _disconnect_volume

        result = _disconnect_volume(mock_module, mock_array)

        assert result is True
        mock_get_with_context.assert_not_called()


class TestUpdateHostInitiators:
    """Test cases for _update_host_initiators function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_host_initiators_add_wwn(
        self, mock_get_with_context, mock_check_response
    ):
        """Test adding WWN initiators to a host"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "host1",
            "wwns": ["50:01:02:03:04:05:06:07"],
            "iqn": None,
            "nqn": None,
        }
        mock_array = Mock()

        # Mock get_hosts response
        mock_host = Mock()
        mock_host.wwns = []
        mock_host.iqns = []
        mock_host.nqns = []
        mock_get_with_context.return_value = Mock(items=[mock_host], status_code=200)

        from plugins.modules.purefa_host import _update_host_initiators

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_host_initiators_no_changes(
        self, mock_get_with_context, mock_check_response
    ):
        """Test updating host when initiators already match"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "host1",
            "wwns": None,
            "iqn": None,
            "nqn": None,
        }
        mock_array = Mock()

        # Mock get_hosts response
        mock_host = Mock()
        mock_host.wwns = []
        mock_host.iqns = []
        mock_host.nqns = []
        mock_get_with_context.return_value = Mock(items=[mock_host], status_code=200)

        from plugins.modules.purefa_host import _update_host_initiators

        result = _update_host_initiators(mock_module, mock_array)

        assert result is False


class TestDeleteHostSuccessExtended:
    """Test cases for delete_host success paths - extended"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_delete_host_success(self, mock_get_with_context, mock_check_response):
        """Test delete_host successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "host1", "context": ""}
        mock_array = Mock()
        # Mock host that doesn't belong to a host group
        mock_host = Mock()
        mock_host.host_group = None
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        delete_host(mock_module, mock_array)

        mock_get_with_context.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestSetHostPersonalityExtended:
    """Extended test cases for _set_host_personality"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_set_host_personality_linux(
        self, mock_get_with_context, mock_check_response
    ):
        """Test _set_host_personality with linux personality"""
        mock_module = Mock()
        mock_module.params = {"name": "host1", "personality": "linux", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        _set_host_personality(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_called_once()

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_set_host_personality_delete(
        self, mock_get_with_context, mock_check_response
    ):
        """Test _set_host_personality with delete"""
        mock_module = Mock()
        mock_module.params = {"name": "host1", "personality": "delete", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        _set_host_personality(mock_module, mock_array)

        mock_get_with_context.assert_called_once()


class TestSetPreferredArrayExtended:
    """Extended test cases for _set_preferred_array"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_set_preferred_array_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test _set_preferred_array sets arrays"""
        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "preferred_array": ["array1"],
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        _set_preferred_array(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_check_response.assert_called_once()

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_set_preferred_array_delete(
        self, mock_get_with_context, mock_check_response
    ):
        """Test _set_preferred_array with delete"""
        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "preferred_array": ["delete"],
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        _set_preferred_array(mock_module, mock_array)

        mock_get_with_context.assert_called_once()


class TestUpdateChapSecurity:
    """Test cases for _update_chap_security function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_chap_host_user_clear(
        self, mock_get_with_context, mock_check_response
    ):
        """Test clearing CHAP host username"""
        from plugins.modules.purefa_host import _update_chap_security

        mock_chap = Mock()
        mock_chap.host_user = "existing_user"
        mock_host = Mock()
        mock_host.chap = mock_chap
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "host_user": "test_user",
            "host_password": "clear",
            "target_user": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        result = _update_chap_security(mock_module, mock_array)

        assert result is True
        assert mock_get_with_context.call_count >= 2

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_chap_host_password_invalid(
        self, mock_get_with_context, mock_check_response
    ):
        """Test CHAP update with invalid password"""
        import pytest
        from plugins.modules.purefa_host import _update_chap_security

        mock_chap = Mock()
        mock_host = Mock()
        mock_host.chap = mock_chap
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "host_user": "test_user",
            "host_password": "short",  # Less than 12 chars
            "target_user": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()

        with pytest.raises(SystemExit):
            _update_chap_security(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_chap_target_user_clear(
        self, mock_get_with_context, mock_check_response
    ):
        """Test clearing CHAP target username"""
        from plugins.modules.purefa_host import _update_chap_security

        mock_chap = Mock()
        mock_chap.target_user = "existing_target"
        mock_host = Mock()
        mock_host.chap = mock_chap
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "host_user": None,
            "target_user": "target_test",
            "target_password": "clear",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        result = _update_chap_security(mock_module, mock_array)

        assert result is True


class TestUpdateHostPersonality:
    """Test cases for _update_host_personality function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_host_personality_change(
        self, mock_get_with_context, mock_check_response
    ):
        """Test updating host personality"""
        from plugins.modules.purefa_host import _update_host_personality

        mock_host = Mock()
        mock_host.personality = "linux"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "personality": "windows",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        result = _update_host_personality(mock_module, mock_array)

        assert result is True
        assert mock_get_with_context.call_count >= 2

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_host_personality_no_change(self, mock_get_with_context):
        """Test updating host personality when no change needed"""
        from plugins.modules.purefa_host import _update_host_personality

        mock_host = Mock()
        mock_host.personality = "linux"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "personality": "linux",  # Same as current
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        result = _update_host_personality(mock_module, mock_array)

        assert result is False

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_host_personality_delete(
        self, mock_get_with_context, mock_check_response
    ):
        """Test deleting host personality"""
        from plugins.modules.purefa_host import _update_host_personality

        mock_host = Mock()
        mock_host.personality = "linux"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "personality": "delete",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        result = _update_host_personality(mock_module, mock_array)

        assert result is True


class TestConnectVolume:
    """Test cases for _connect_new_volume function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_connect_volume_success(self, mock_get_with_context, mock_check_response):
        """Test connecting volume to host"""
        from plugins.modules.purefa_host import _connect_new_volume

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
            "lun": None,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        result = _connect_new_volume(mock_module, mock_array)

        assert result is True
        mock_get_with_context.assert_called_once()

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_connect_volume_with_lun(self, mock_get_with_context, mock_check_response):
        """Test connecting volume with specific LUN"""
        from plugins.modules.purefa_host import _connect_new_volume

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
            "lun": 10,
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        result = _connect_new_volume(mock_module, mock_array)

        assert result is True
        mock_get_with_context.assert_called_once()

    def test_connect_volume_check_mode(self):
        """Test connecting volume in check mode"""
        from plugins.modules.purefa_host import _connect_new_volume

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
            "lun": None,
        }
        mock_module.check_mode = True
        mock_array = Mock()

        result = _connect_new_volume(mock_module, mock_array)

        assert result is True
        mock_array.post_connections.assert_not_called()


class TestDisconnectVolumeExtended:
    """Test cases for _disconnect_volume function - extended"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_disconnect_volume_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test disconnecting volume from host"""
        from plugins.modules.purefa_host import _disconnect_volume

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
            "context": "",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        result = _disconnect_volume(mock_module, mock_array)

        assert result is True
        mock_get_with_context.assert_called_once()

    def test_disconnect_volume_check_mode(self):
        """Test disconnecting volume in check mode"""
        from plugins.modules.purefa_host import _disconnect_volume

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "volume": "vol1",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        result = _disconnect_volume(mock_module, mock_array)

        assert result is True
        mock_array.delete_connections.assert_not_called()


class TestMoveHostExtended:
    """Test cases for move_host function - extended"""

    def test_move_host_context_not_supported(self):
        """Test move_host fails when context is provided"""
        import pytest
        from plugins.modules.purefa_host import move_host

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "context": "some-context",
            "move": ["realm1"],
        }
        mock_module.fail_json.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            move_host(mock_module, Mock())

        mock_module.fail_json.assert_called_once_with(
            msg="context is not yet supported for host move function"
        )

    def test_move_host_mixed_local_realm(self):
        """Test move_host fails when mixing local with realm"""
        import pytest
        from plugins.modules.purefa_host import move_host

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",
            "context": "",
            "move": ["local", "realm1"],
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_arrays.return_value = Mock(items=[Mock(name="array1")])

        with pytest.raises(SystemExit):
            move_host(mock_module, mock_array)

        mock_module.fail_json.assert_called_once_with(
            msg="Cannot mix local with another realm in move target list"
        )

    def test_move_host_local_without_realm_name(self):
        """Test move_host fails when moving to local without realm in hostname"""
        import pytest
        from plugins.modules.purefa_host import move_host

        mock_module = Mock()
        mock_module.params = {
            "name": "host1",  # No :: in name
            "context": "",
            "move": ["local"],
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_arrays.return_value = Mock(items=[Mock(name="array1")])

        with pytest.raises(SystemExit):
            move_host(mock_module, mock_array)

        mock_module.fail_json.assert_called_once_with(
            msg="host must be provided with current realm name"
        )

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_move_host_with_connections_fails(self, mock_get_with_context):
        """Test move_host fails when host has existing connections"""
        import pytest
        from plugins.modules.purefa_host import move_host

        mock_host = Mock()
        mock_host.connection_count = 5  # Has connections
        mock_get_with_context.return_value = Mock(items=[mock_host])

        mock_module = Mock()
        mock_module.params = {
            "name": "realm1::host1",
            "context": "",
            "move": ["local"],
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_arrays.return_value = Mock(items=[Mock(name="array1")])

        with pytest.raises(SystemExit):
            move_host(mock_module, mock_array)

        assert "allow_errors" not in mock_get_with_context.call_args.kwargs
        mock_module.fail_json.assert_called_once_with(
            msg="Hosts cannot be moved with existing volume connections."
        )

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_move_host_to_local_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test move_host successfully moves host to local"""
        from plugins.modules.purefa_host import move_host

        mock_host = Mock()
        mock_host.connection_count = 0  # No connections
        mock_get_with_context.return_value = Mock(items=[mock_host], status_code=200)

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "realm1::host1",
            "context": "",
            "move": ["local"],
            "modify_resource_access": False,
        }
        mock_array = Mock()
        mock_array.get_arrays.return_value = Mock(items=[Mock(name="array1")])

        move_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_move_host_to_realm_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test move_host successfully moves host to a realm"""
        from plugins.modules.purefa_host import move_host

        mock_host = Mock()
        mock_host.connection_count = 0
        mock_get_with_context.return_value = Mock(items=[mock_host], status_code=200)

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "host1",  # No realm prefix - local host
            "context": "",
            "move": ["realm2"],
            "modify_resource_access": False,
        }
        mock_array = Mock()
        mock_array.get_arrays.return_value = Mock(items=[Mock(name="array1")])

        move_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_move_host_check_mode(self, mock_get_with_context):
        """Test move_host in check mode"""
        from plugins.modules.purefa_host import move_host

        mock_host = Mock()
        mock_host.connection_count = 0
        mock_get_with_context.return_value = Mock(items=[mock_host], status_code=200)

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "realm1::host1",
            "context": "",
            "move": ["local"],
            "modify_resource_access": False,
        }
        mock_array = Mock()
        mock_array.get_arrays.return_value = Mock(items=[Mock(name="array1")])

        move_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        # In check mode, get_with_context should only be called once (to get host)
        assert mock_get_with_context.call_count == 1


class TestUpdatePreferredArray:
    """Test cases for _update_preferred_array function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_preferred_array_add_to_empty(
        self, mock_get_with_context, mock_check_response
    ):
        """Test adding preferred array when none exist"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "preferred_array": ["array1", "array2"],
        }
        mock_array = Mock()

        # Host has no preferred arrays currently
        mock_host = Mock()
        mock_host.preferred_arrays = []
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_host]),  # get_hosts
            Mock(status_code=200),  # patch_hosts
        ]

        result = _update_preferred_array(mock_module, mock_array)

        assert result is True
        assert mock_get_with_context.call_count == 2

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_preferred_array_delete(
        self, mock_get_with_context, mock_check_response
    ):
        """Test deleting preferred array list"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "preferred_array": ["delete"],
        }
        mock_array = Mock()

        # Host has preferred arrays currently
        mock_ref = Mock()
        mock_ref.name = "array1"
        mock_host = Mock()
        mock_host.preferred_arrays = [mock_ref]
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_host]),  # get_hosts
            Mock(status_code=200),  # patch_hosts
        ]

        result = _update_preferred_array(mock_module, mock_array)

        assert result is True
        assert mock_get_with_context.call_count == 2

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_preferred_array_no_change(self, mock_get_with_context):
        """Test no change when preferred arrays match"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "preferred_array": ["array1"],
        }
        mock_array = Mock()

        # Host has same preferred arrays - use spec to set .name as attribute
        mock_ref = Mock()
        mock_ref.name = "array1"
        mock_host = Mock()
        mock_host.preferred_arrays = [mock_ref]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        result = _update_preferred_array(mock_module, mock_array)

        assert result is False
        assert mock_get_with_context.call_count == 1

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_preferred_array_change_list(
        self, mock_get_with_context, mock_check_response
    ):
        """Test changing preferred array list"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "preferred_array": ["array2", "array3"],
        }
        mock_array = Mock()

        # Host has different preferred arrays
        mock_ref = Mock()
        mock_ref.name = "array1"
        mock_host = Mock()
        mock_host.preferred_arrays = [mock_ref]
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_host]),  # get_hosts
            Mock(status_code=200),  # patch_hosts
        ]

        result = _update_preferred_array(mock_module, mock_array)

        assert result is True
        assert mock_get_with_context.call_count == 2

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_preferred_array_delete_when_empty(self, mock_get_with_context):
        """Test delete preferred array when already empty - no change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "preferred_array": ["delete"],
        }
        mock_array = Mock()

        # Host has no preferred arrays
        mock_host = Mock()
        mock_host.preferred_arrays = []
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_host])

        result = _update_preferred_array(mock_module, mock_array)

        assert result is False
        assert mock_get_with_context.call_count == 1


class TestSetHostInitiators:
    """Test cases for _set_host_initiators function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_set_host_initiators_nqn(self, mock_host_patch, mock_get, mock_check):
        """Test setting NQN initiators"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-host",
            "nqn": ["nqn.2014-08.org.nvmexpress:uuid:test"],
            "iqn": None,
            "wwns": None,
        }
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=200)

        _set_host_initiators(mock_module, mock_array)

        mock_get.assert_called_once()
        mock_check.assert_called_once()

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_set_host_initiators_iqn(self, mock_host_patch, mock_get, mock_check):
        """Test setting IQN initiators"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": ["iqn.2021-01.com.example:test"],
            "wwns": None,
        }
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=200)

        _set_host_initiators(mock_module, mock_array)

        mock_get.assert_called_once()
        mock_check.assert_called_once()

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_set_host_initiators_wwns(self, mock_host_patch, mock_get, mock_check):
        """Test setting WWN initiators"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": None,
            "wwns": ["50:00:00:00:00:00:00:01"],
        }
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=200)

        _set_host_initiators(mock_module, mock_array)

        mock_get.assert_called_once()
        mock_check.assert_called_once()


class TestUpdateHostInitiatorsExtended:
    """Extended test cases for _update_host_initiators function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_nqn_change(self, mock_host_patch, mock_get, mock_check):
        """Test updating NQN when different"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": ["nqn.2014-08.org.nvmexpress:uuid:new"],
            "iqn": None,
            "wwns": None,
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = ["nqn.2014-08.org.nvmexpress:uuid:old"]
        mock_host.iqns = []
        mock_host.wwns = []
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True
        assert mock_get.call_count == 2

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_nqn_remove(self, mock_host_patch, mock_get, mock_check):
        """Test removing NQN when empty string provided"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": [""],
            "iqn": None,
            "wwns": None,
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = ["nqn.2014-08.org.nvmexpress:uuid:old"]
        mock_host.iqns = []
        mock_host.wwns = []
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True
        assert mock_get.call_count == 2

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_iqn_change(self, mock_host_patch, mock_get, mock_check):
        """Test updating IQN when different"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": ["iqn.2021-01.com.example:new"],
            "wwns": None,
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = []
        mock_host.iqns = ["iqn.2021-01.com.example:old"]
        mock_host.wwns = []
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True
        assert "allow_errors" not in mock_get.call_args_list[0].kwargs

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_iqn_remove(self, mock_host_patch, mock_get, mock_check):
        """Test removing IQN when empty string provided"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": [""],
            "wwns": None,
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = []
        mock_host.iqns = ["iqn.2021-01.com.example:old"]
        mock_host.wwns = []
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_wwns_change(self, mock_host_patch, mock_get, mock_check):
        """Test updating WWNs when different"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": None,
            "wwns": ["50:00:00:00:00:00:00:02"],
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = []
        mock_host.iqns = []
        mock_host.wwns = ["5000000000000001"]
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_wwns_remove(self, mock_host_patch, mock_get):
        """Test removing WWNs when empty string provided"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": None,
            "wwns": [""],
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = []
        mock_host.iqns = []
        mock_host.wwns = ["5000000000000001"]
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_wwns_remove_specific(self, mock_host_patch, mock_get, mock_check):
        """Dropping one WWN keeps the rest and only disassociates the dropped one"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": None,
            "wwns": ["5000000000000001"],
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = []
        mock_host.iqns = []
        mock_host.wwns = ["5000000000000001", "5000000000000002"]
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True
        assert mock_get.call_count == 2
        assert mock_host_patch.call_args.kwargs == {"remove_wwns": ["5000000000000002"]}

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_wwns_add_keeps_existing(
        self, mock_host_patch, mock_get, mock_check
    ):
        """Adding a WWN only associates the missing one, leaving current ones"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": None,
            "wwns": ["5000000000000001", "5000000000000002"],
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = []
        mock_host.iqns = []
        mock_host.wwns = ["5000000000000001"]
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True
        assert mock_host_patch.call_args.kwargs == {"add_wwns": ["5000000000000002"]}

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_wwns_add_and_remove(self, mock_host_patch, mock_get, mock_check):
        """Adding and removing in one call uses add_wwns/remove_wwns, not wwns.

        Host has wwn1+wwn2; requesting wwn2+wwn3 must add wwn3 and remove wwn1
        while leaving wwn2 untouched (the reported audit-trail regression).
        """
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": None,
            "wwns": ["1000000000000002", "1000000000000003"],
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = []
        mock_host.iqns = []
        mock_host.wwns = ["1000000000000001", "1000000000000002"]
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is True
        assert mock_host_patch.call_args.kwargs == {
            "add_wwns": ["1000000000000003"],
            "remove_wwns": ["1000000000000001"],
        }
        assert "wwns" not in mock_host_patch.call_args.kwargs

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_wwns_no_change(self, mock_host_patch, mock_get, mock_check):
        """No patch is issued when the WWN set already matches (colon/case aware)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "nqn": None,
            "iqn": None,
            "wwns": ["50:00:00:00:00:00:00:01"],
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.nqns = []
        mock_host.iqns = []
        mock_host.wwns = ["5000000000000001"]
        mock_get.side_effect = [Mock(status_code=200, items=[mock_host])]

        result = _update_host_initiators(mock_module, mock_array)

        assert result is False
        assert mock_get.call_count == 1
        mock_host_patch.assert_not_called()


class TestUpdateHostPersonalityExtended:
    """Extended test cases for _update_host_personality function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_personality_add_new(self, mock_host_patch, mock_get, mock_check):
        """Test adding personality when host has none"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "personality": "windows",
        }
        mock_array = Mock()

        mock_host = Mock(spec=[])  # No personality attribute
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_personality(mock_module, mock_array)

        assert result is True
        assert mock_get.call_count == 2

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_personality_delete(self, mock_host_patch, mock_get, mock_check):
        """Test deleting personality when host has one"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "personality": "delete",
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.personality = "windows"
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_personality(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    def test_update_personality_change(self, mock_host_patch, mock_get, mock_check):
        """Test changing personality"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "personality": "linux",
        }
        mock_array = Mock()

        mock_host = Mock()
        mock_host.personality = "windows"
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_host_personality(mock_module, mock_array)

        assert result is True


class TestUpdateChapSecurityExtended:
    """Extended test cases for _update_chap_security function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    @patch("plugins.modules.purefa_host.Chap")
    def test_update_chap_set_host_user(
        self, mock_chap, mock_host_patch, mock_get, mock_check
    ):
        """Test setting CHAP host username and password"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "host_user": "chapuser",
            "host_password": "chapassword123",  # 13 chars, valid
            "target_user": None,
            "target_password": None,
        }
        mock_array = Mock()

        mock_host_chap = Mock(spec=[])  # No host_user attribute
        mock_host = Mock()
        mock_host.chap = mock_host_chap
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_chap_security(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    @patch("plugins.modules.purefa_host.Chap")
    def test_update_chap_clear_host_password(
        self, mock_chap, mock_host_patch, mock_get, mock_check
    ):
        """Test clearing CHAP host password"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "host_user": "chapuser",
            "host_password": "clear",
            "target_user": None,
            "target_password": None,
        }
        mock_array = Mock()

        mock_host_chap = Mock()
        mock_host_chap.host_user = "chapuser"
        mock_host = Mock()
        mock_host.chap = mock_host_chap
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_chap_security(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    @patch("plugins.modules.purefa_host.Chap")
    def test_update_chap_set_target_user(
        self, mock_chap, mock_host_patch, mock_get, mock_check
    ):
        """Test setting CHAP target username and password"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "host_user": None,
            "host_password": None,
            "target_user": "targetuser",
            "target_password": "targetpass1234",  # 14 chars, valid
        }
        mock_array = Mock()

        mock_host_chap = Mock(spec=[])  # No target_user attribute
        mock_host = Mock()
        mock_host.chap = mock_host_chap
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_chap_security(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    @patch("plugins.modules.purefa_host.Chap")
    def test_update_chap_clear_target_password(
        self, mock_chap, mock_host_patch, mock_get, mock_check
    ):
        """Test clearing CHAP target password"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "host_user": None,
            "host_password": None,
            "target_user": "targetuser",
            "target_password": "clear",
        }
        mock_array = Mock()

        mock_host_chap = Mock()
        mock_host_chap.target_user = "targetuser"
        mock_host = Mock()
        mock_host.chap = mock_host_chap
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),
            Mock(status_code=200),
        ]

        result = _update_chap_security(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    @patch("plugins.modules.purefa_host.Chap")
    def test_update_chap_invalid_host_password(
        self, mock_chap, mock_host_patch, mock_get
    ):
        """Test CHAP update fails with invalid host password"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json = Mock(side_effect=SystemExit(1))
        mock_module.params = {
            "name": "test-host",
            "host_user": "chapuser",
            "host_password": "short",  # Too short
            "target_user": None,
            "target_password": None,
        }
        mock_array = Mock()

        mock_host_chap = Mock(spec=[])
        mock_host = Mock()
        mock_host.chap = mock_host_chap
        mock_get.return_value = Mock(status_code=200, items=[mock_host])

        import pytest

        with pytest.raises(SystemExit):
            _update_chap_security(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    @patch("plugins.modules.purefa_host.Chap")
    def test_update_chap_invalid_target_password(
        self, mock_chap, mock_host_patch, mock_get
    ):
        """Test CHAP update fails with invalid target password"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json = Mock(side_effect=SystemExit(1))
        mock_module.params = {
            "name": "test-host",
            "host_user": None,
            "host_password": None,
            "target_user": "targetuser",
            "target_password": "short",  # Too short
        }
        mock_array = Mock()

        mock_host_chap = Mock(spec=[])
        mock_host = Mock()
        mock_host.chap = mock_host_chap
        mock_get.return_value = Mock(status_code=200, items=[mock_host])

        import pytest

        with pytest.raises(SystemExit):
            _update_chap_security(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestMakeHostWithVolume:
    """Test cases for make_host with volume connection"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPost")
    @patch("plugins.modules.purefa_host.ConnectionPost")
    def test_make_host_with_volume_and_lun(
        self, mock_conn_post, mock_host_post, mock_get, mock_check
    ):
        """Test creating host with volume and LUN"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "context": "",
            "vlan": None,
            "nqn": None,
            "iqn": None,
            "wwns": None,
            "personality": None,
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "volume": "test-volume",
            "lun": 10,
        }
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=200)

        make_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        # Should call post for connections with LUN
        assert mock_get.call_count >= 2

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPost")
    def test_make_host_with_volume_no_lun(self, mock_host_post, mock_get, mock_check):
        """Test creating host with volume but no LUN"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "context": "",
            "vlan": None,
            "nqn": None,
            "iqn": None,
            "wwns": None,
            "personality": None,
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "volume": "test-volume",
            "lun": None,
        }
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=200)

        make_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateHostRename:
    """Test cases for update_host with rename"""

    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host.rename_exists")
    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.HostPatch")
    @patch("plugins.modules.purefa_host.LooseVersion", side_effect=lambda x: x)
    def test_update_host_rename_success(
        self,
        mock_lv,
        mock_host_patch,
        mock_get,
        mock_check,
        mock_rename_exists,
        mock_api,
    ):
        """Test renaming a host successfully"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "old-host",
            "state": "present",
            "rename": "new-host",
            "vlan": None,
            "iqn": None,
            "wwns": None,
            "nqn": None,
            "volume": None,
            "personality": None,
            "preferred_array": None,
            "target_user": None,
            "host_user": None,
        }
        mock_array = Mock()
        mock_api.return_value = "2.38"
        mock_rename_exists.return_value = False
        mock_get.side_effect = [
            Mock(status_code=200),  # patch_hosts (rename)
            Mock(status_code=200, items=[]),  # get_connections
        ]

        update_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host.rename_exists")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.LooseVersion", side_effect=lambda x: x)
    def test_update_host_rename_target_exists(
        self, mock_lv, mock_get, mock_rename_exists, mock_api
    ):
        """Test renaming host when target already exists"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.warn = Mock()
        mock_module.params = {
            "name": "old-host",
            "state": "present",
            "rename": "existing-host",
            "vlan": None,
            "iqn": None,
            "wwns": None,
            "nqn": None,
            "volume": None,
            "personality": None,
            "preferred_array": None,
            "target_user": None,
            "host_user": None,
        }
        mock_array = Mock()
        mock_api.return_value = "2.38"
        mock_rename_exists.return_value = True
        mock_get.return_value = Mock(status_code=200, items=[])

        update_host(mock_module, mock_array)

        mock_module.warn.assert_called_once()


class TestUpdateHostDisconnectVolume:
    """Test cases for update_host disconnecting a volume"""

    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host._disconnect_volume")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.LooseVersion", side_effect=lambda x: x)
    def test_update_host_disconnect_volume(
        self, mock_lv, mock_get, mock_disconnect, mock_api
    ):
        """Test disconnecting a volume from host"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "state": "absent",
            "rename": None,
            "vlan": None,
            "iqn": None,
            "wwns": None,
            "nqn": None,
            "volume": "test-volume",
            "personality": None,
            "preferred_array": None,
            "target_user": None,
            "host_user": None,
        }
        mock_array = Mock()
        mock_api.return_value = "2.38"

        mock_vol = Mock()
        mock_vol.volume = Mock()
        mock_vol.volume.name = "test-volume"
        mock_get.return_value = Mock(status_code=200, items=[mock_vol])
        mock_disconnect.return_value = True

        update_host(mock_module, mock_array)

        mock_disconnect.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteHostWithHostGroup:
    """Test cases for delete_host when host is in a host group"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_delete_host_in_hostgroup(self, mock_get, mock_check):
        """Test deleting host that belongs to a host group"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "context": "",
        }
        mock_array = Mock()

        mock_hg = Mock()
        mock_hg.name = "test-hg"
        mock_host = Mock()
        mock_host.host_group = mock_hg
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),  # get_hosts
            Mock(status_code=200),  # delete_host_groups_hosts
            Mock(status_code=200, items=[]),  # get_connections
            Mock(status_code=200),  # delete_hosts
        ]

        delete_host(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        assert mock_get.call_count == 4
        assert "allow_errors" not in mock_get.call_args_list[0].kwargs


class TestSetChapSecurityValidation:
    """Test cases for CHAP password validation in _set_chap_security"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_host_password_too_short_fails(self, mock_get, mock_check):
        """Test that host_password < 12 characters fails validation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-host",
            "host_user": "user1",
            "host_password": "short",  # < 12 chars
            "target_user": None,
            "target_password": None,
            "context": "",
        }
        mock_array = Mock()

        _set_chap_security(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "12" in str(mock_module.fail_json.call_args)

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_target_password_too_short_fails(self, mock_get, mock_check):
        """Test that target_password < 12 characters fails validation"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-host",
            "host_user": None,
            "host_password": None,
            "target_user": "target1",
            "target_password": "tooshort",  # < 12 chars
            "context": "",
        }
        mock_array = Mock()

        _set_chap_security(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "12" in str(mock_module.fail_json.call_args)


class TestSetVlanFailure:
    """Test cases for VLAN set failure path"""

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_set_vlan_failure_warns(self, mock_get):
        """Test that failed VLAN set triggers warning"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-host",
            "vlan": "100",
            "context": "",
        }
        mock_array = Mock()
        mock_error = Mock()
        mock_error.message = "VLAN not supported"
        mock_get.return_value = Mock(status_code=400, errors=[mock_error])

        _set_vlan(mock_module, mock_array)

        mock_module.warn.assert_called_once()
        assert "VLAN" in str(mock_module.warn.call_args)


class TestUpdateVlanPaths:
    """Test cases for _update_vlan function"""

    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_vlan_changes_value(self, mock_get, mock_check):
        """Test VLAN update when value differs"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "vlan": "200",
            "context": "",
        }
        mock_array = Mock()

        # Current host has vlan=100
        mock_host = Mock()
        mock_host.vlan = "100"
        mock_get.side_effect = [
            Mock(status_code=200, items=[mock_host]),  # get_hosts
            Mock(status_code=200),  # patch_hosts
        ]

        result = _update_vlan(mock_module, mock_array)

        assert result is True
        assert mock_get.call_count == 2
        assert "allow_errors" not in mock_get.call_args_list[0].kwargs

    @patch("plugins.modules.purefa_host.get_with_context")
    def test_update_vlan_no_change(self, mock_get):
        """Test VLAN update when value is the same"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "vlan": "100",
            "context": "",
        }
        mock_array = Mock()

        # Current host already has vlan=100
        mock_host = Mock()
        mock_host.vlan = "100"
        mock_get.return_value = Mock(status_code=200, items=[mock_host])

        result = _update_vlan(mock_module, mock_array)

        assert result is False
        mock_get.assert_called_once()


class TestMakeHostWithAllOptions:
    """Test cases for make_host with personality, preferred_array, and CHAP"""

    @patch("plugins.modules.purefa_host._set_chap_security")
    @patch("plugins.modules.purefa_host._set_preferred_array")
    @patch("plugins.modules.purefa_host._set_host_personality")
    @patch("plugins.modules.purefa_host._set_host_initiators")
    @patch("plugins.modules.purefa_host._set_vlan")
    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_make_host_with_personality(
        self,
        mock_get,
        mock_check,
        mock_set_vlan,
        mock_set_init,
        mock_set_pers,
        mock_set_pref,
        mock_set_chap,
    ):
        """Test make_host calls _set_host_personality when personality is set"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "vlan": None,
            "personality": "esxi",
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "volume": None,
            "context": "",
        }
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=200)

        make_host(mock_module, mock_array)

        mock_set_pers.assert_called_once()
        mock_set_pref.assert_not_called()
        mock_set_chap.assert_not_called()

    @patch("plugins.modules.purefa_host._set_chap_security")
    @patch("plugins.modules.purefa_host._set_preferred_array")
    @patch("plugins.modules.purefa_host._set_host_personality")
    @patch("plugins.modules.purefa_host._set_host_initiators")
    @patch("plugins.modules.purefa_host._set_vlan")
    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_make_host_with_preferred_array(
        self,
        mock_get,
        mock_check,
        mock_set_vlan,
        mock_set_init,
        mock_set_pers,
        mock_set_pref,
        mock_set_chap,
    ):
        """Test make_host calls _set_preferred_array when preferred_array is set"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "vlan": None,
            "personality": None,
            "preferred_array": ["array1"],
            "host_user": None,
            "target_user": None,
            "volume": None,
            "context": "",
        }
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=200)

        make_host(mock_module, mock_array)

        mock_set_pers.assert_not_called()
        mock_set_pref.assert_called_once()
        mock_set_chap.assert_not_called()

    @patch("plugins.modules.purefa_host._set_chap_security")
    @patch("plugins.modules.purefa_host._set_preferred_array")
    @patch("plugins.modules.purefa_host._set_host_personality")
    @patch("plugins.modules.purefa_host._set_host_initiators")
    @patch("plugins.modules.purefa_host._set_vlan")
    @patch("plugins.modules.purefa_host.check_response")
    @patch("plugins.modules.purefa_host.get_with_context")
    def test_make_host_with_chap(
        self,
        mock_get,
        mock_check,
        mock_set_vlan,
        mock_set_init,
        mock_set_pers,
        mock_set_pref,
        mock_set_chap,
    ):
        """Test make_host calls _set_chap_security when CHAP is set"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "vlan": None,
            "personality": None,
            "preferred_array": None,
            "host_user": "user1",
            "target_user": None,
            "volume": None,
            "context": "",
        }
        mock_array = Mock()
        mock_get.return_value = Mock(status_code=200)

        make_host(mock_module, mock_array)

        mock_set_pers.assert_not_called()
        mock_set_pref.assert_not_called()
        mock_set_chap.assert_called_once()


class TestUpdateHostWithAllOptions:
    """Test cases for update_host with all update paths"""

    @patch("plugins.modules.purefa_host._update_vlan")
    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.LooseVersion", side_effect=lambda x: x)
    def test_update_host_with_vlan(
        self, mock_lv, mock_get, mock_api_version, mock_update_vlan
    ):
        """Test update_host calls _update_vlan when vlan is set"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "rename": None,
            "state": "present",
            "vlan": "100",
            "iqn": None,
            "wwns": None,
            "nqn": None,
            "volume": None,
            "personality": None,
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "context": "",
        }
        mock_array = Mock()
        mock_api_version.return_value = "2.38"
        mock_get.return_value = Mock(status_code=200, items=[])
        mock_update_vlan.return_value = True

        update_host(mock_module, mock_array)

        mock_update_vlan.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host._update_host_initiators")
    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.LooseVersion", side_effect=lambda x: x)
    def test_update_host_with_initiators(
        self, mock_lv, mock_get, mock_api_version, mock_update_init
    ):
        """Test update_host calls _update_host_initiators when IQN is set"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "rename": None,
            "state": "present",
            "vlan": None,
            "iqn": ["iqn.2020-01.com.example:host1"],
            "wwns": None,
            "nqn": None,
            "volume": None,
            "personality": None,
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "context": "",
        }
        mock_array = Mock()
        mock_api_version.return_value = "2.38"
        mock_get.return_value = Mock(status_code=200, items=[])
        mock_update_init.return_value = True

        update_host(mock_module, mock_array)

        mock_update_init.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host._connect_new_volume")
    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.LooseVersion", side_effect=lambda x: x)
    def test_update_host_connect_new_volume(
        self, mock_lv, mock_get, mock_api_version, mock_connect
    ):
        """Test update_host calls _connect_new_volume when volume not connected"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "rename": None,
            "state": "present",
            "vlan": None,
            "iqn": None,
            "wwns": None,
            "nqn": None,
            "volume": "new-vol",
            "personality": None,
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "context": "",
        }
        mock_array = Mock()
        mock_api_version.return_value = "2.38"
        # No existing volume connections
        mock_get.return_value = Mock(status_code=200, items=[])
        mock_connect.return_value = True

        update_host(mock_module, mock_array)

        mock_connect.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host._update_host_personality")
    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.LooseVersion", side_effect=lambda x: x)
    def test_update_host_with_personality(
        self, mock_lv, mock_get, mock_api_version, mock_update_pers
    ):
        """Test update_host calls _update_host_personality when personality is set"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "rename": None,
            "state": "present",
            "vlan": None,
            "iqn": None,
            "wwns": None,
            "nqn": None,
            "volume": None,
            "personality": "esxi",
            "preferred_array": None,
            "host_user": None,
            "target_user": None,
            "context": "",
        }
        mock_array = Mock()
        mock_api_version.return_value = "2.38"
        mock_get.return_value = Mock(status_code=200, items=[])
        mock_update_pers.return_value = True

        update_host(mock_module, mock_array)

        mock_update_pers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host._update_preferred_array")
    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.LooseVersion", side_effect=lambda x: x)
    def test_update_host_with_preferred_array(
        self, mock_lv, mock_get, mock_api_version, mock_update_pref
    ):
        """Test update_host calls _update_preferred_array when preferred_array is set"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "rename": None,
            "state": "present",
            "vlan": None,
            "iqn": None,
            "wwns": None,
            "nqn": None,
            "volume": None,
            "personality": None,
            "preferred_array": ["array1"],
            "host_user": None,
            "target_user": None,
            "context": "",
        }
        mock_array = Mock()
        mock_api_version.return_value = "2.38"
        mock_get.return_value = Mock(status_code=200, items=[])
        mock_update_pref.return_value = True

        update_host(mock_module, mock_array)

        mock_update_pref.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_host._update_chap_security")
    @patch("plugins.modules.purefa_host.get_cached_api_version")
    @patch("plugins.modules.purefa_host.get_with_context")
    @patch("plugins.modules.purefa_host.LooseVersion", side_effect=lambda x: x)
    def test_update_host_with_chap(
        self, mock_lv, mock_get, mock_api_version, mock_update_chap
    ):
        """Test update_host calls _update_chap_security when CHAP is set"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-host",
            "rename": None,
            "state": "present",
            "vlan": None,
            "iqn": None,
            "wwns": None,
            "nqn": None,
            "volume": None,
            "personality": None,
            "preferred_array": None,
            "host_user": "user1",
            "target_user": None,
            "context": "",
        }
        mock_array = Mock()
        mock_api_version.return_value = "2.38"
        mock_get.return_value = Mock(status_code=200, items=[])
        mock_update_chap.return_value = True

        update_host(mock_module, mock_array)

        mock_update_chap.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)
