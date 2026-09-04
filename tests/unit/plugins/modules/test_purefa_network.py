# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_network module."""

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
# Mock netaddr module
mock_netaddr = MagicMock()
mock_netaddr.valid_ipv4 = MagicMock(return_value=True)
# Create an IPNetwork mock that is iterable and contains the gateway
mock_ip_network = MagicMock()
mock_ip_network.netmask = "255.255.255.0"
mock_ip_network.__contains__ = MagicMock(return_value=True)
mock_netaddr.IPNetwork = MagicMock(return_value=mock_ip_network)
mock_netaddr.IPAddress = MagicMock()
sys.modules["netaddr"] = mock_netaddr
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

from plugins.modules.purefa_network import (
    delete_interface,
    update_fc_interface,
    update_interface,
    create_interface,
    _check_subinterfaces,
    _create_subordinates,
    _create_subinterfaces,
)


def _subref(name):
    """Build a FixedReferenceNoId-like mock subinterface exposing a .name (#1013)."""
    sub = Mock()
    sub.name = name
    return sub


class TestDeleteInterface:
    """Test cases for delete_interface function"""

    def test_delete_interface_check_mode(self):
        """Test delete_interface in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "ct0.eth2"}
        mock_array = Mock()

        delete_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateFcInterface:
    """Test cases for update_fc_interface function"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_enable_check_mode(self, mock_check_response):
        """Test enabling FC interface in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": None,
        }
        mock_array = Mock()
        mock_interface = Mock(enabled=False, services=[])

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_disable_check_mode(self, mock_check_response):
        """Test disabling FC interface in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "ct0.fc0", "state": "absent", "servicelist": None}
        mock_array = Mock()
        mock_interface = Mock(enabled=True, services=[])

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_no_change(self, mock_check_response):
        """Test FC interface with no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": None,
        }
        mock_array = Mock()
        mock_interface = Mock(enabled=True, services=[])

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestCheckSubinterfaces:
    """Test cases for _check_subinterfaces function"""

    def test_check_subinterfaces_returns_list(self):
        """Test _check_subinterfaces returns the subinterface names (#1013)

        Subinterfaces come back from the API as FixedReferenceNoId objects,
        not strings, so the function must return their .name values.
        """
        mock_module = Mock()
        mock_module.params = {"name": "ct0.eth0"}
        mock_array = Mock()
        mock_interface = Mock()
        sub1 = Mock()
        sub1.name = "sub1"
        sub2 = Mock()
        sub2.name = "sub2"
        mock_interface.eth.subinterfaces = [sub1, sub2]
        mock_array.get_network_interfaces.return_value.items = [mock_interface]

        result = _check_subinterfaces(mock_module, mock_array)

        assert result == ["sub1", "sub2"]


class TestCreateInterface:
    """Test cases for create_interface function"""

    @patch("plugins.modules.purefa_network._create_subordinates")
    def test_create_interface_subnet_not_exists(self, mock_create_subordinates):
        """Test create_interface fails when subnet doesn't exist"""
        mock_create_subordinates.return_value = ([], [])
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "ct0.eth2",
            "subnet": "test-subnet",
            "interface": "lacpbond",
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value.status_code = 404

        create_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_network._create_subordinates")
    def test_create_interface_check_mode(self, mock_create_subordinates):
        """Test create_interface in check mode"""
        mock_create_subordinates.return_value = ([], [])
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "ct0.eth2",
            "subnet": "test-subnet",
            "interface": "lacpbond",
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value.status_code = 200

        create_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteInterface:
    """Test cases for delete_interface function"""

    def test_delete_interface_success(self):
        """Test delete_interface successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "ct0.eth2"}
        mock_array = Mock()
        mock_array.delete_network_interfaces.return_value = Mock(status_code=200)

        delete_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_called_once_with(names=["ct0.eth2"])
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCheckSubinterfacesAdditional:
    """Additional test cases for _check_subinterfaces function"""

    def test_check_subinterfaces_multiple(self):
        """Test _check_subinterfaces returns correct list"""
        mock_module = Mock()
        mock_module.params = {"name": "eth2"}
        mock_array = Mock()

        # Create mock interface with eth.subinterfaces as FixedReferenceNoId-like
        # objects (the API returns objects with a .name, not bare strings) (#1013)
        mock_interface = Mock()
        mock_interface.eth = Mock()
        sub1 = Mock()
        sub1.name = "eth2.100"
        sub2 = Mock()
        sub2.name = "eth2.200"
        mock_interface.eth.subinterfaces = [sub1, sub2]
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])

        result = _check_subinterfaces(mock_module, mock_array)

        assert result == ["eth2.100", "eth2.200"]

    def test_check_subinterfaces_none(self):
        """Test _check_subinterfaces with no subinterfaces"""
        mock_module = Mock()
        mock_module.params = {"name": "eth2"}
        mock_array = Mock()

        # Create mock interface with empty subinterfaces
        mock_interface = Mock()
        mock_interface.eth = Mock()
        mock_interface.eth.subinterfaces = []
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])

        result = _check_subinterfaces(mock_module, mock_array)

        assert result == []


class TestUpdateInterface:
    """Test cases for update_interface function"""

    def test_update_interface_not_found_fails(self):
        """Test update_interface fails when interface not found"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {"name": "eth2"}
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(items=[])

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    def test_update_interface_eth_subinterfaces_idempotent(self):
        """ETH interface with existing subinterfaces is an idempotent no-op (#1013)

        Subinterfaces are returned by the API as FixedReferenceNoId objects.
        Building current_state must sort them by .name (not the bare objects,
        which are not orderable) and must not raise TypeError. When the desired
        subinterfaces match the current ones, no change is made.
        """

        def _sub(name):
            sub = Mock()
            sub.name = name
            return sub

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "ct0.eth8",
            "state": "present",
            "enabled": True,
            "servicelist": None,
            "address": None,
            "gateway": None,
            "mtu": None,
            "subinterfaces": ["ct0.eth1", "ct1.eth1"],
            "subordinates": None,
            "subnet": None,
            "interface": "vif",
        }

        mock_interface = Mock()
        mock_interface.name = "ct0.eth8"
        mock_interface.enabled = True
        mock_interface.services = ["management"]
        mock_interface.eth.mtu = 1500
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        # API returns subinterfaces as objects, deliberately unsorted
        mock_interface.eth.subinterfaces = [_sub("ct1.eth1"), _sub("ct0.eth1")]

        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])

        # Must not raise TypeError, and must be a no-op
        update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_array.patch_network_interfaces.assert_not_called()

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_enable_success(self, mock_check_response):
        """Test update_interface enables FC interface successfully"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = False
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_array.patch_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_disable_success(self, mock_check_response):
        """Test update_interface disables FC interface successfully"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "absent",
            "servicelist": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_array.patch_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_fc_interface_no_change(self):
        """Test update_interface with FC interface already in desired state"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = True  # Already enabled
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_array.patch_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestCreateSubordinates:
    """Test cases for _create_subordinates function"""

    def test_create_subordinates_success(self):
        """Test creating subordinates with valid interfaces"""
        mock_module = Mock()
        mock_module.params = {"subordinates": ["ct0.eth0", "ct1.eth0"]}
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(status_code=200)

        v1, v2 = _create_subordinates(mock_module, mock_array)

        assert len(v1) == 2
        assert "ct0.eth0" in v1
        assert "ct1.eth0" in v1
        assert len(v2) == 2

    def test_create_subordinates_empty(self):
        """Test creating subordinates with no subordinates specified"""
        mock_module = Mock()
        mock_module.params = {"subordinates": None}
        mock_array = Mock()

        v1, v2 = _create_subordinates(mock_module, mock_array)

        assert v1 == []
        assert v2 == []

    def test_create_subordinates_not_exists(self):
        """Test creating subordinates when interface doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"subordinates": ["ct0.eth0"]}
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(status_code=400)

        _create_subordinates(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestCreateSubinterfaces:
    """Test cases for _create_subinterfaces function"""

    def test_create_subinterfaces_lacp(self):
        """Test creating subinterfaces with LACP interfaces"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": ["ct0.lacp0.eth0"]}
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(status_code=200)
        mock_array.get_controllers.return_value = Mock(items=[Mock(), Mock()])

        v1, v2 = _create_subinterfaces(mock_module, mock_array)

        assert len(v1) == 1
        assert "ct0.lacp0.eth0" in v1
        assert len(v2) == 1

    def test_create_subinterfaces_empty(self):
        """Test creating subinterfaces with no subinterfaces specified"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": None}
        mock_array = Mock()
        mock_array.get_controllers.return_value = Mock(items=[Mock(), Mock()])

        v1, v2 = _create_subinterfaces(mock_module, mock_array)

        assert v1 == []
        assert v2 == []

    def test_create_subinterfaces_non_lacp(self):
        """Test creating subinterfaces with non-LACP interfaces (dual controller)"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": ["eth0"]}
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(status_code=200)
        mock_array.get_controllers.return_value = Mock(items=[Mock(), Mock()])

        v1, v2 = _create_subinterfaces(mock_module, mock_array)

        assert len(v1) == 2
        assert "ct0.eth0" in v1
        assert "ct1.eth0" in v1
        assert len(v2) == 2

    def test_create_subinterfaces_single_controller(self):
        """Test creating subinterfaces on single controller (Purity VM)"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": ["eth0"]}
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(status_code=200)
        mock_array.get_controllers.return_value = Mock(
            items=[Mock()]
        )  # Single controller

        v1, v2 = _create_subinterfaces(mock_module, mock_array)

        assert len(v1) == 1
        assert "ct0.eth0" in v1
        assert len(v2) == 1


class TestCreateInterfaceExtended:
    """Extended test cases for create_interface function"""

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    def test_create_interface_vif_check_mode(self, mock_create_subinterfaces):
        """Test creating a VIF interface in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "ct0.vif0",
            "subnet": "test-subnet",
            "interface": "vif",
            "subinterfaces": None,
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=200)
        mock_create_subinterfaces.return_value = ([], [])

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network._create_subordinates")
    def test_create_interface_lacpbond_check_mode(self, mock_create_subordinates):
        """Test creating a LACP bond interface in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "ct0.bond0",
            "subnet": "test-subnet",
            "interface": "lacpbond",
            "subordinates": ["ct0.eth0", "ct1.eth0"],
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=200)
        mock_create_subordinates.return_value = ([], [])

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteInterfaceSuccess:
    """Test cases for delete_interface success paths"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_delete_interface_success(self, mock_check_response):
        """Test delete_interface successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "ct0.eth2.100"}
        mock_array = Mock()
        mock_array.delete_network_interfaces.return_value = Mock(status_code=200)

        delete_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateFcInterfaceExtended:
    """Extended test cases for update_fc_interface"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_disable_success(self, mock_check_response):
        """Test disabling FC interface successfully"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "ct0.fc1", "state": "absent", "servicelist": None}
        mock_array = Mock()
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.enabled = True
        mock_interface.services = []

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_array.patch_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_update_services(self, mock_check_response):
        """Test updating FC interface services"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.fc1",
            "state": "present",
            "servicelist": ["replication"],
        }
        mock_array = Mock()
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.enabled = True
        mock_interface.services = ["management"]

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_array.patch_network_interfaces.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_fc_interface_no_change(self):
        """Test update_fc_interface when no change needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.fc1",
            "state": "present",
            "servicelist": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = True
        mock_interface.services = []

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_array.patch_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdateInterfaceSuccess:
    """Test cases for update_interface success paths"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_change_services(self, mock_check_response):
        """Test update_interface changes FC interface services"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": ["replication"],
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = True
        mock_interface.services = ["management"]
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_array.patch_network_interfaces.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_enable_and_services(self, mock_check_response):
        """Test update_interface enables FC interface and updates services"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": ["replication", "nvme-tcp"],
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = False
        mock_interface.services = []
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        # Should be called twice - once to enable, once to change services
        assert mock_array.patch_network_interfaces.call_count == 2
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_fc_interface_check_mode_enable(self):
        """Test update_interface FC interface check mode for enable"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = False
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_array.patch_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateInterfaceSuccess:
    """Test cases for create_interface function success paths"""

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_vif_interface_success(
        self, mock_check_response, mock_create_subinterfaces
    ):
        """Test creating a VIF interface successfully"""
        mock_create_subinterfaces.return_value = (False, ["ct0.eth8", "ct1.eth8"])
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": None,
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": ["ct0.eth8", "ct1.eth8"],
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    def test_create_vif_interface_check_mode(self, mock_create_subinterfaces):
        """Test creating a VIF interface in check mode"""
        mock_create_subinterfaces.return_value = (False, [])
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": None,
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": None,
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_interface_subnet_not_exists(self):
        """Test create_interface fails when subnet doesn't exist"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": "nonexistent_subnet",
            "address": None,
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)

        with pytest.raises(SystemExit):
            create_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestDeleteInterfaceSuccess:
    """Test cases for delete_interface function success paths"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_delete_interface_success(self, mock_check_response):
        """Test delete_interface successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "ct0.eth8"}
        mock_array = Mock()
        mock_array.delete_network_interfaces.return_value = Mock(status_code=200)

        delete_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_delete_interface_check_mode(self):
        """Test delete_interface in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "ct0.eth8"}
        mock_array = Mock()

        delete_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateEthInterface:
    """Test cases for update_interface with ETH interfaces"""

    @patch("plugins.modules.purefa_network.check_response")
    @patch("plugins.modules.purefa_network._check_subinterfaces")
    def test_update_eth_interface_change_mtu(
        self, mock_check_subinterfaces, mock_check_response
    ):
        """Test updating ETH interface MTU"""
        import pytest

        mock_check_subinterfaces.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.eth8",
            "state": "present",
            "servicelist": None,
            "subinterfaces": None,
            "subordinates": None,
            "enabled": True,
            "address": None,
            "mtu": 9000,
            "gateway": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth8"
        mock_interface.enabled = True
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_eth_interface_no_change(self):
        """Test ETH interface with no changes needed"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.eth8",
            "state": "present",
            "servicelist": None,
            "subinterfaces": None,
            "subordinates": None,
            "enabled": True,
            "address": None,
            "mtu": None,
            "gateway": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth8"
        mock_interface.enabled = True
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_update_eth_interface_mtu_out_of_range(self):
        """Test ETH interface fails with MTU out of range"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "ct0.eth8",
            "state": "present",
            "servicelist": None,
            "subinterfaces": None,
            "subordinates": None,
            "enabled": True,
            "address": None,
            "mtu": 100,  # Out of range
            "gateway": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth8"
        mock_interface.enabled = True
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_network.check_response")
    @patch("plugins.modules.purefa_network._check_subinterfaces")
    def test_update_eth_interface_change_enabled(
        self, mock_check_subinterfaces, mock_check_response
    ):
        """Test updating ETH interface enabled state"""
        import pytest

        mock_check_subinterfaces.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.eth8",
            "state": "present",
            "servicelist": None,
            "subinterfaces": None,
            "subordinates": None,
            "enabled": False,  # Changing from True to False
            "address": None,
            "mtu": None,
            "gateway": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth8"
        mock_interface.enabled = True
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.check_response")
    @patch("plugins.modules.purefa_network._check_subinterfaces")
    def test_update_eth_interface_change_services(
        self, mock_check_subinterfaces, mock_check_response
    ):
        """Test updating ETH interface services"""
        import pytest

        mock_check_subinterfaces.return_value = []
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.eth8",
            "state": "present",
            "servicelist": ["iscsi", "replication"],
            "subinterfaces": None,
            "subordinates": None,
            "enabled": True,
            "address": None,
            "mtu": None,
            "gateway": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth8"
        mock_interface.enabled = True
        mock_interface.services = ["management"]
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateInterfaceLacp:
    """Test cases for create_interface with LACP bonds"""

    @patch("plugins.modules.purefa_network._create_subordinates")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_lacp_interface_success(
        self, mock_check_response, mock_create_subordinates
    ):
        """Test creating LACP bond interface successfully"""
        mock_create_subordinates.return_value = (
            ["ct0.eth0", "ct0.eth1"],
            [Mock(), Mock()],
        )
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "bond0",
            "interface": "lacp",
            "subnet": None,
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subordinates": ["ct0.eth0", "ct0.eth1"],
            "subinterfaces": None,
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network._create_subordinates")
    def test_create_lacp_interface_check_mode(self, mock_create_subordinates):
        """Test creating LACP bond interface in check mode"""
        mock_create_subordinates.return_value = ([], [])
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "bond0",
            "interface": "lacp",
            "subnet": None,
            "subordinates": ["ct0.eth0", "ct0.eth1"],
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateInterfaceWithSubnet:
    """Test cases for create_interface with subnet"""

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_vif_with_subnet_success(
        self, mock_check_response, mock_create_subinterfaces
    ):
        """Test creating VIF interface with subnet successfully"""
        mock_create_subinterfaces.return_value = (
            ["ct0.eth8", "ct1.eth8"],
            [Mock(), Mock()],
        )
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": "test-subnet",
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": ["eth8"],
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=200)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_vif_without_subnet_success(
        self, mock_check_response, mock_create_subinterfaces
    ):
        """Test creating VIF interface without subnet successfully"""
        mock_create_subinterfaces.return_value = (
            ["ct0.eth8", "ct1.eth8"],
            [Mock(), Mock()],
        )
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": None,
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": ["eth8"],
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateInterfaceFailure:
    """Test cases for create_interface failure scenarios"""

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_vif_patch_fails(
        self, mock_check_response, mock_create_subinterfaces
    ):
        """Test creating VIF interface when patch fails"""
        import pytest

        mock_create_subinterfaces.return_value = (
            ["ct0.eth8", "ct1.eth8"],
            [Mock(), Mock()],
        )
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": "test-subnet",
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": ["eth8"],
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=200)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_error = Mock()
        mock_error.message = "Patch failed"
        mock_array.patch_network_interfaces.return_value = Mock(
            status_code=400, errors=[mock_error]
        )

        with pytest.raises(SystemExit):
            create_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_called_once()
        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_vif_no_subnet_patch_fails(
        self, mock_check_response, mock_create_subinterfaces
    ):
        """Test creating VIF interface without subnet when patch fails"""
        import pytest

        mock_create_subinterfaces.return_value = (
            ["ct0.eth8", "ct1.eth8"],
            [Mock(), Mock()],
        )
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": None,
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": ["eth8"],
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_error = Mock()
        mock_error.message = "Patch failed"
        mock_array.patch_network_interfaces.return_value = Mock(
            status_code=400, errors=[mock_error]
        )

        with pytest.raises(SystemExit):
            create_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_called_once()
        mock_module.fail_json.assert_called_once()


class TestCreateSubinterfacesNotExists:
    """Test cases for _create_subinterfaces when interface doesn't exist"""

    def test_create_subinterfaces_not_exists_lacp(self):
        """Test creating subinterfaces when LACP interface doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": ["ct0.lacp0.eth0"]}
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(status_code=404)
        mock_array.get_controllers.return_value = Mock(items=[Mock(), Mock()])

        _create_subinterfaces(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    def test_create_subinterfaces_not_exists_eth(self):
        """Test creating subinterfaces when ETH interface doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": ["eth0"]}
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(status_code=404)
        mock_array.get_controllers.return_value = Mock(items=[Mock(), Mock()])

        _create_subinterfaces(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestUpdateFcInterfaceEnableSuccess:
    """Test cases for update_fc_interface enable with actual API call"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_enable_success(self, mock_check_response):
        """Test enabling FC interface successfully"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": None,
        }
        mock_array = Mock()
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.enabled = False
        mock_interface.services = []

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_array.patch_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateEthInterfaceWithSubinterfaces:
    """Test cases for update_interface with subinterfaces"""

    @patch("plugins.modules.purefa_network.check_response")
    @patch("plugins.modules.purefa_network._check_subinterfaces")
    def test_update_eth_interface_mtu_with_existing_subinterfaces(
        self, mock_check_subinterfaces, mock_check_response
    ):
        """Test updating ETH interface MTU when subinterfaces exist"""
        import pytest

        # Return same subinterfaces to avoid triggering create_interface
        mock_check_subinterfaces.return_value = ["ct0.eth8", "ct1.eth8"]
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "vif1",
            "state": "present",
            "servicelist": None,
            "subinterfaces": ["eth8"],
            "subordinates": None,
            "enabled": True,
            "address": None,
            "mtu": 9000,  # Changed MTU
            "gateway": None,
            "interface": "vif",
            "subnet": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "vif1"
        mock_interface.enabled = True
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = [
            _subref("ct0.eth8"),
            _subref("ct1.eth8"),
        ]  # Same as returned
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateEthInterfaceSubordinates:
    """Test cases for update_interface with subordinates changes"""

    @patch("plugins.modules.purefa_network.check_response")
    @patch("plugins.modules.purefa_network._check_subinterfaces")
    def test_update_eth_interface_change_subordinates(
        self, mock_check_subinterfaces, mock_check_response
    ):
        """Test updating ETH interface subordinates (LACP)"""
        import pytest

        mock_check_subinterfaces.return_value = ["ct0.eth0", "ct0.eth1"]
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "bond0",
            "state": "present",
            "servicelist": None,
            "subinterfaces": None,
            "subordinates": ["ct0.eth0", "ct0.eth1", "ct0.eth2"],  # Adding one
            "enabled": True,
            "address": None,
            "mtu": 9000,  # Changed MTU to trigger update path
            "gateway": None,
            "interface": "lacp",
            "subnet": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "bond0"
        mock_interface.enabled = True
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = [_subref("ct0.eth0"), _subref("ct0.eth1")]
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateInterfaceLacpWithParams:
    """Test cases for create_interface LACP with various parameters"""

    @patch("plugins.modules.purefa_network._create_subordinates")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_lacp_with_mtu_and_enabled(
        self, mock_check_response, mock_create_subordinates
    ):
        """Test creating LACP bond with MTU and enabled settings"""
        mock_create_subordinates.return_value = (
            ["ct0.eth0", "ct0.eth1"],
            [Mock(), Mock()],
        )
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "bond0",
            "interface": "lacp",
            "subnet": None,
            "address": None,
            "gateway": None,
            "mtu": 9000,
            "enabled": False,
            "subordinates": ["ct0.eth0", "ct0.eth1"],
            "subinterfaces": None,
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_called_once()
        mock_array.patch_network_interfaces.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateInterfaceVifWithSubnet:
    """Test cases for create_interface VIF with subnet scenarios"""

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_vif_with_subnet_patch_success(
        self, mock_check_response, mock_create_subinterfaces
    ):
        """Test creating VIF with subnet - patch succeeds"""
        mock_create_subinterfaces.return_value = (
            ["ct0.eth8", "ct1.eth8"],
            [Mock(), Mock()],
        )
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": "management-subnet",
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": ["eth8"],
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=200)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateFcInterfaceDisable:
    """Test cases for update_fc_interface disable"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_disable(self, mock_check_response):
        """Test disabling FC interface (state=absent)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "absent",  # Use absent to disable
            "servicelist": None,
        }
        mock_array = Mock()
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.enabled = True  # Currently enabled
        mock_interface.services = []

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_array.patch_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_fc_interface_no_change(self):
        """Test FC interface with no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = True  # Already enabled, state=present
        mock_interface.services = []

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_array.patch_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_update_fc_interface_check_mode(self):
        """Test FC interface enable in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",  # Want to enable
            "servicelist": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = False  # Currently disabled
        mock_interface.services = []

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_array.patch_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateSubordinatesSuccess:
    """Test cases for _create_subordinates function"""

    def test_create_subordinates_success(self):
        """Test creating subordinates successfully"""
        mock_module = Mock()
        mock_module.params = {"subordinates": ["ct0.eth0", "ct0.eth1"]}
        mock_array = Mock()
        mock_interface1 = Mock()
        mock_interface1.name = "ct0.eth0"
        mock_interface2 = Mock()
        mock_interface2.name = "ct0.eth1"
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface1, mock_interface2]
        )

        result = _create_subordinates(mock_module, mock_array)

        assert len(result[0]) == 2
        assert "ct0.eth0" in result[0]
        assert "ct0.eth1" in result[0]

    def test_create_subordinates_not_found(self):
        """Test creating subordinates when interface not found"""
        mock_module = Mock()
        mock_module.params = {"subordinates": ["ct0.eth99"]}
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(status_code=404)

        _create_subordinates(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestCheckSubinterfacesSuccess:
    """Test cases for _check_subinterfaces with valid data"""

    def test_check_subinterfaces_returns_list(self):
        """Test _check_subinterfaces returns subinterfaces list"""
        mock_module = Mock()
        mock_module.params = {"name": "vif1"}
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.eth = Mock()
        mock_interface.eth.subinterfaces = [_subref("ct0.eth8"), _subref("ct1.eth8")]
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])

        result = _check_subinterfaces(mock_module, mock_array)

        assert result == ["ct0.eth8", "ct1.eth8"]

    def test_check_subinterfaces_empty(self):
        """Test _check_subinterfaces with no subinterfaces"""
        mock_module = Mock()
        mock_module.params = {"name": "vif1"}
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.eth = Mock()
        mock_interface.eth.subinterfaces = []
        mock_array.get_network_interfaces.return_value = Mock(items=[mock_interface])

        result = _check_subinterfaces(mock_module, mock_array)

        assert result == []


class TestCreateSubinterfacesWithLacp:
    """Test cases for _create_subinterfaces with LACP interfaces"""

    def test_create_subinterfaces_lacp_success(self):
        """Test creating subinterfaces with LACP type successfully"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": ["ct0.lacp0.eth0", "ct0.lacp0.eth1"]}
        mock_array = Mock()
        mock_array.get_controllers.return_value = Mock(items=[Mock(), Mock()])
        mock_array.get_network_interfaces.return_value = Mock(status_code=200)

        result = _create_subinterfaces(mock_module, mock_array)

        assert len(result[0]) == 2
        assert "ct0.lacp0.eth0" in result[0]
        assert "ct0.lacp0.eth1" in result[0]

    def test_create_subinterfaces_eth_single_controller(self):
        """Test creating subinterfaces with ETH on single controller (VM)"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": ["eth8"]}
        mock_array = Mock()
        # Single controller = Purity VM
        mock_array.get_controllers.return_value = Mock(items=[Mock()])
        mock_array.get_network_interfaces.return_value = Mock(status_code=200)

        result = _create_subinterfaces(mock_module, mock_array)

        # Should only have ct0 interface, not ct1
        assert len(result[0]) == 1
        assert "ct0.eth8" in result[0]

    def test_create_subinterfaces_eth_dual_controller(self):
        """Test creating subinterfaces with ETH on dual controller"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": ["eth8"]}
        mock_array = Mock()
        # Dual controller = physical array
        mock_array.get_controllers.return_value = Mock(items=[Mock(), Mock()])
        mock_array.get_network_interfaces.return_value = Mock(status_code=200)

        result = _create_subinterfaces(mock_module, mock_array)

        # Should have both ct0 and ct1 interfaces
        assert len(result[0]) == 2
        assert "ct0.eth8" in result[0]
        assert "ct1.eth8" in result[0]

    def test_create_subinterfaces_empty(self):
        """Test creating subinterfaces with empty list"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": []}
        mock_array = Mock()
        mock_array.get_controllers.return_value = Mock(items=[Mock(), Mock()])

        result = _create_subinterfaces(mock_module, mock_array)

        assert result == ([], [])

    def test_create_subinterfaces_none(self):
        """Test creating subinterfaces with None"""
        mock_module = Mock()
        mock_module.params = {"subinterfaces": None}
        mock_array = Mock()
        mock_array.get_controllers.return_value = Mock(items=[Mock(), Mock()])

        result = _create_subinterfaces(mock_module, mock_array)

        assert result == ([], [])


class TestUpdateFcInterfaceServices:
    """Test cases for update_fc_interface with service changes"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_fc_interface_change_services(self, mock_check_response):
        """Test updating FC interface services"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": ["scsi-fc", "nvme-fc"],
        }
        mock_array = Mock()
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.enabled = True
        mock_interface.services = ["scsi-fc"]  # Different from new

        update_fc_interface(mock_module, mock_array, mock_interface)

        # Should call patch for service update
        mock_array.patch_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_fc_interface_same_services(self):
        """Test FC interface with same services (no change)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.fc0",
            "state": "present",
            "servicelist": ["scsi-fc"],
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.enabled = True
        mock_interface.services = ["scsi-fc"]  # Same as requested

        update_fc_interface(mock_module, mock_array, mock_interface)

        mock_array.patch_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestCreateSubordinatesWithMultiple:
    """Test cases for _create_subordinates with multiple interfaces"""

    def test_create_subordinates_multiple(self):
        """Test creating multiple subordinates"""
        mock_module = Mock()
        mock_module.params = {"subordinates": ["ct0.eth0", "ct0.eth1", "ct0.eth2"]}
        mock_array = Mock()
        mock_interface1 = Mock()
        mock_interface1.name = "ct0.eth0"
        mock_interface2 = Mock()
        mock_interface2.name = "ct0.eth1"
        mock_interface3 = Mock()
        mock_interface3.name = "ct0.eth2"
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface1, mock_interface2, mock_interface3]
        )

        result = _create_subordinates(mock_module, mock_array)

        assert len(result[0]) == 3

    def test_create_subordinates_empty(self):
        """Test creating subordinates with empty list"""
        mock_module = Mock()
        mock_module.params = {"subordinates": []}
        mock_array = Mock()

        result = _create_subordinates(mock_module, mock_array)

        assert result == ([], [])

    def test_create_subordinates_none(self):
        """Test creating subordinates with None"""
        mock_module = Mock()
        mock_module.params = {"subordinates": None}
        mock_array = Mock()

        result = _create_subordinates(mock_module, mock_array)

        assert result == ([], [])


class TestDeleteInterfaceError:
    """Test cases for delete_interface error handling"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_delete_interface_api_error(self, mock_check_response):
        """Test delete_interface when API returns error"""
        import pytest

        mock_check_response.side_effect = SystemExit(1)
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "ct0.eth8"}
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_error = Mock()
        mock_error.message = "Delete failed"
        mock_array.delete_network_interfaces.return_value = Mock(
            status_code=400, errors=[mock_error]
        )

        with pytest.raises(SystemExit):
            delete_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_called_once()


class TestCreateInterfaceCheckMode:
    """Test cases for create_interface check mode"""

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    def test_create_vif_check_mode(self, mock_create_subinterfaces):
        """Test creating VIF in check mode"""
        mock_create_subinterfaces.return_value = ([], [])
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": None,
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network._create_subordinates")
    def test_create_lacp_check_mode(self, mock_create_subordinates):
        """Test creating LACP in check mode"""
        mock_create_subordinates.return_value = ([], [])
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "bond0",
            "interface": "lacp",
            "subnet": None,
            "subordinates": ["ct0.eth0", "ct0.eth1"],
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)

        create_interface(mock_module, mock_array)

        mock_array.post_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateInterfaceAddressValidation:
    """Test cases for address/gateway validation in update_interface"""

    @patch("plugins.modules.purefa_network.IPNetwork")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_management_port_ip_removal_blocked(
        self, mock_check_response, mock_ipnetwork
    ):
        """Test that removing IP from management port fails"""
        import pytest

        # Mock IPNetwork to return an object that equals the gateway and is iterable
        mock_network = Mock()
        mock_network.__eq__ = Mock(return_value=True)  # Gateway equals IPNetwork result
        mock_network.__contains__ = Mock(return_value=True)  # For "in" checks
        mock_ipnetwork.return_value = mock_network
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "0.0.0.0/0",
            "gateway": None,
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.eth = Mock()
        mock_interface.eth.address = "10.0.0.1"
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.eth.gateway = "10.0.0.254"
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["management"]
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_once_with(
            msg="Removing IP address from a management or app port is not supported"
        )

    @patch("plugins.modules.purefa_network.IPNetwork")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_app_port_ip_removal_blocked(
        self, mock_check_response, mock_ipnetwork
    ):
        """Test that removing IP from app port fails"""
        import pytest

        # Mock IPNetwork to return an object that equals the gateway and is iterable
        mock_network = Mock()
        mock_network.__eq__ = Mock(return_value=True)  # Gateway equals IPNetwork result
        mock_network.__contains__ = Mock(return_value=True)  # For "in" checks
        mock_ipnetwork.return_value = mock_network
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth1",
            "state": "present",
            "address": "::/0",
            "gateway": None,
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth1"
        mock_interface.eth = Mock()
        mock_interface.eth.address = "10.0.0.2"
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.eth.gateway = "10.0.0.254"
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["app"]
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_once_with(
            msg="Removing IP address from a management or app port is not supported"
        )


class TestUpdateInterfaceMtuValidation:
    """Test cases for MTU validation in update_interface"""

    def test_update_interface_mtu_too_low(self):
        """Test MTU validation when value is too low"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": None,
            "gateway": None,
            "mtu": 1000,  # Below minimum of 1280
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.eth = Mock()
        mock_interface.eth.address = "10.0.0.1"
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.eth.gateway = "10.0.0.254"
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["replication"]
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "MTU 1000 is out of range" in str(mock_module.fail_json.call_args)

    def test_update_interface_mtu_too_high(self):
        """Test MTU validation when value is too high"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": None,
            "gateway": None,
            "mtu": 10000,  # Above maximum of 9216
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.eth = Mock()
        mock_interface.eth.address = "10.0.0.1"
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.eth.gateway = "10.0.0.254"
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["replication"]
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "MTU 10000 is out of range" in str(mock_module.fail_json.call_args)


class TestCreateInterfaceWithSubnetFailure:
    """Test cases for create_interface with subnet that fails"""

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    def test_create_vif_with_subnet_patch_fails(self, mock_create_subinterfaces):
        """Test VIF creation with subnet when patch fails"""
        import pytest

        mock_create_subinterfaces.return_value = ([], [])
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": "subnet1",
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=200)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_error = Mock()
        mock_error.message = "Patch failed"
        mock_array.patch_network_interfaces.return_value = Mock(
            status_code=400, errors=[mock_error]
        )

        with pytest.raises(SystemExit):
            create_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_called_once()
        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    def test_create_vif_without_subinterfaces_with_subnet(
        self, mock_create_subinterfaces
    ):
        """Test VIF creation without subinterfaces but with subnet"""
        import pytest

        mock_create_subinterfaces.return_value = ([], [])
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": "subnet1",
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=200)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_error = Mock()
        mock_error.message = "Subnet patch failed"
        mock_array.patch_network_interfaces.return_value = Mock(
            status_code=400, errors=[mock_error]
        )

        with pytest.raises(SystemExit):
            create_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_called_once()


class TestCreateInterfaceAddressValidation:
    """Test cases for address validation in create_interface"""

    @patch("plugins.modules.purefa_network.IPNetwork")
    @patch("plugins.modules.purefa_network._create_subinterfaces")
    def test_create_vif_gateway_not_in_subnet(
        self, mock_create_subinterfaces, mock_ipnetwork
    ):
        """Test creating VIF with gateway not in subnet"""
        import pytest

        mock_create_subinterfaces.return_value = ([], [])
        # Make IPNetwork return a mock that does NOT contain the gateway
        mock_network = Mock()
        mock_network.netmask = "255.255.255.0"
        mock_network.__contains__ = Mock(return_value=False)  # Gateway NOT in subnet
        mock_ipnetwork.return_value = mock_network
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": None,
            "address": "10.0.0.1/24",
            "gateway": "192.168.1.1",  # Not in 10.0.0.0/24 subnet
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)

        with pytest.raises(SystemExit):
            create_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_with(
            msg="Gateway and subnet are not compatible."
        )


class TestCreateInterfaceNoSubnetNoSubinterfaces:
    """Test cases for create_interface without subnet or subinterfaces"""

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_vif_no_subnet_no_subinterfaces_patch_fails(
        self, mock_check_response, mock_create_subinterfaces
    ):
        """Test VIF creation without subnet fails at patch"""
        import pytest

        mock_create_subinterfaces.return_value = ([], [])
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": None,
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_error = Mock()
        mock_error.message = "Patch error"
        mock_array.patch_network_interfaces.return_value = Mock(
            status_code=400, errors=[mock_error]
        )

        with pytest.raises(SystemExit):
            create_interface(mock_module, mock_array)

        mock_array.delete_network_interfaces.assert_called_once()


class TestUpdateInterfaceGatewayClearing:
    """Test cases for clearing gateway in update_interface"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_clear_ipv4_gateway(self, mock_check_response):
        """Test clearing IPv4 gateway with 0.0.0.0"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "10.0.0.1/24",
            "gateway": "0.0.0.0",  # Clear gateway
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.eth = Mock()
        mock_interface.eth.address = "10.0.0.1"
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.eth.gateway = "10.0.0.254"  # Current gateway
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["replication"]
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class FakeEth:
    """Stand-in for the SDK's eth model.

    py-pure-client models raise AttributeError for any field the array
    returned as null rather than returning None. Mock objects do not, which
    hides code paths that read an unset setting without a getattr default.
    """

    def __init__(self, **fields):
        self._fields = fields

    def __getattr__(self, name):
        value = self._fields.get(name)
        if value is None:
            raise AttributeError(name)
        return value


def _eth_interface(eth, services=None):
    interface = Mock()
    interface.name = "ct0.eth4"
    interface.enabled = True
    interface.services = services if services is not None else ["iscsi"]
    interface.eth = eth
    return interface


class FakeInterface:
    """Stand-in for the SDK's network interface model

    Raises for unset fields the same way FakeEth does, for the settings read
    from the interface itself rather than from its eth member.
    """

    def __init__(self, eth, **fields):
        self.eth = eth
        self._fields = fields

    def __getattr__(self, name):
        value = self._fields.get(name)
        if value is None:
            raise AttributeError(name)
        return value


def _bringup_params(name="ct0.eth4"):
    """Params for the play in issue #1029 - an iSCSI port with no gateway"""
    return {
        "name": name,
        "state": "present",
        "address": "10.21.200.10/24",
        "gateway": None,
        "mtu": 9000,
        "servicelist": None,
        "subinterfaces": None,
        "subordinates": None,
        "enabled": True,
    }


class TestCheckSubinterfacesUnset:
    """Regression tests for issue #1029 - subinterfaces reported as null"""

    def test_no_subinterfaces_returns_empty_list(self):
        """A physical port with no children has subinterfaces unset"""
        mock_module = Mock()
        mock_module.params = {"name": "ct0.eth4"}

        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[_eth_interface(FakeEth(mtu=1500))]
        )

        assert _check_subinterfaces(mock_module, mock_array) == []

    def test_subinterfaces_still_read(self):
        """An interface with children still reports their names"""
        mock_module = Mock()
        mock_module.params = {"name": "ct0.eth4"}

        eth = FakeEth(
            mtu=1500, subinterfaces=[_subref("ct0.eth9"), _subref("ct1.eth9")]
        )
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[_eth_interface(eth)]
        )

        assert _check_subinterfaces(mock_module, mock_array) == [
            "ct0.eth9",
            "ct1.eth9",
        ]


class TestUpdateInterfaceUnsetFields:
    """Regression tests for issue #1029 - unset gateway and subinterfaces"""

    def test_set_address_with_no_gateway_or_subinterfaces(self):
        """Bringing up an iSCSI port that has neither configured"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _bringup_params()

        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[_eth_interface(FakeEth(mtu=1500))]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)
        # The enable patch, then the IP settings patch through the
        # empty-gateway path
        assert mock_array.patch_network_interfaces.call_count == 2

    def test_set_address_with_no_gateway_on_parent_interface(self):
        """The gateway check is reached once subinterfaces are readable

        Isolates the unset gateway read, which the unset subinterfaces read
        above would otherwise mask by failing first.
        """
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _bringup_params()

        eth = FakeEth(mtu=1500, subinterfaces=[_subref("ct0.eth9")])
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[_eth_interface(eth)]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_no_change_when_nothing_differs(self):
        """An interface with no gateway or subinterfaces is idempotent"""
        mock_module = Mock()
        mock_module.check_mode = False
        params = _bringup_params()
        params["address"] = None
        params["mtu"] = None
        mock_module.params = params

        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[_eth_interface(FakeEth(mtu=1500))]
        )

        update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_array.patch_network_interfaces.assert_not_called()

    def test_no_services_assigned(self):
        """An interface with no services reported does not crash"""
        mock_module = Mock()
        mock_module.check_mode = False
        params = _bringup_params()
        params["address"] = None
        params["mtu"] = None
        mock_module.params = params

        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200,
            items=[FakeInterface(FakeEth(mtu=1500), name="ct0.eth4", enabled=True)],
        )

        update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_subinterfaces_read_into_current_state(self):
        """An interface with children is still compared on their names"""
        mock_module = Mock()
        mock_module.check_mode = False
        params = _bringup_params()
        params["address"] = None
        params["mtu"] = None
        mock_module.params = params

        eth = FakeEth(
            mtu=1500, subinterfaces=[_subref("ct1.eth9"), _subref("ct0.eth9")]
        )
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[_eth_interface(eth)]
        )

        update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestUpdateInterfaceKeptGatewayCompatibility:
    """The existing gateway is checked against the new subnet by containment"""

    def test_kept_gateway_inside_new_subnet_is_accepted(self):
        """Readdressing within the same subnet keeps the existing gateway

        The global IPNetwork stand-in reports every address as inside the
        subnet, so a compatible gateway must not be rejected.
        """
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _bringup_params()

        eth = FakeEth(
            mtu=9000,
            address="10.21.200.9",
            netmask="255.255.255.0",
            gateway="10.21.200.1",
        )
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[_eth_interface(eth)]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.IPNetwork")
    def test_kept_gateway_outside_new_subnet_is_rejected(self, mock_ipnetwork):
        """Readdressing into a subnet the existing gateway is not in fails"""
        network = MagicMock()
        network.netmask = "255.255.255.0"
        network.__contains__ = Mock(return_value=False)
        mock_ipnetwork.return_value = network

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _bringup_params()
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        eth = FakeEth(
            mtu=9000,
            address="192.168.1.9",
            netmask="255.255.255.0",
            gateway="192.168.1.1",
        )
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[_eth_interface(eth)]
        )

        try:
            update_interface(mock_module, mock_array)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_with(
            msg="Gateway and subnet are not compatible."
        )

    def test_cleared_gateway_is_not_checked(self):
        """A gateway already cleared to 0.0.0.0 is not validated"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _bringup_params()

        eth = FakeEth(
            mtu=9000,
            address="10.21.200.9",
            netmask="255.255.255.0",
            gateway="0.0.0.0",
        )
        mock_array = Mock()
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[_eth_interface(eth)]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_not_called()

    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_clear_ipv6_gateway(self, mock_check_response):
        """Test clearing IPv6 gateway with ::"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "2001:db8::1/64",
            "gateway": "::",  # Clear IPv6 gateway
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.eth = Mock()
        mock_interface.eth.address = "2001:db8::1"
        mock_interface.eth.netmask = "64"
        mock_interface.eth.gateway = "2001:db8::254"
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["replication"]
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateInterfaceSubinterfacesChange:
    """Test cases for subinterfaces changes in update_interface"""

    @patch("plugins.modules.purefa_network._create_subinterfaces")
    @patch("plugins.modules.purefa_network._check_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_subinterfaces_change(
        self, mock_check_response, mock_check_subinterfaces, mock_create_subinterfaces
    ):
        """Test updating interface with changed subinterfaces"""
        import pytest

        # Return different subinterfaces than current
        mock_check_subinterfaces.return_value = ["ct0.eth1", "ct1.eth1"]
        mock_create_subinterfaces.return_value = ([], [])
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "vif1",
            "state": "present",
            "address": None,
            "gateway": None,
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": ["eth1"],  # Request subinterfaces
            "subordinates": None,
            "subnet": None,
            "interface": "vif",
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "vif1"
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = [
            _subref("ct0.eth0"),
            _subref("ct1.eth0"),
        ]  # Different!
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateInterfaceGatewayValidation:
    """Test cases for gateway validation in update_interface"""

    @patch("plugins.modules.purefa_network.IPNetwork")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_gateway_not_in_address_subnet(
        self, mock_check_response, mock_ipnetwork
    ):
        """Test gateway validation fails when not in address subnet"""
        import pytest

        # Mock IPNetwork to NOT contain the gateway
        mock_network = Mock()
        mock_network.netmask = "255.255.255.0"
        mock_network.__contains__ = Mock(return_value=False)  # Gateway NOT in subnet
        mock_ipnetwork.return_value = mock_network
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "10.0.0.1/24",  # Different from current
            "gateway": "192.168.1.1",  # Not in 10.0.0.0/24
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = "10.0.0.254"
        mock_interface.eth.address = "10.0.0.2"  # Current address different
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_with(
            msg="Gateway and subnet are not compatible."
        )


class TestUpdateInterfaceIpv6Address:
    """Test cases for IPv6 address handling in update_interface"""

    @patch("plugins.modules.purefa_network.valid_ipv4")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_ipv6_address_netmask(
        self, mock_check_response, mock_valid_ipv4
    ):
        """Test IPv6 address sets netmask from CIDR"""
        import pytest

        mock_valid_ipv4.return_value = False  # IPv6 address
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "2001:db8::1/64",  # IPv6 with CIDR
            "gateway": None,
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = None
        mock_interface.eth.address = "2001:db8::2"  # Different address
        mock_interface.eth.netmask = "64"
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateInterfaceIpVersionChange:
    """Test cases for IP version change validation"""

    @patch("plugins.modules.purefa_network.IPAddress")
    @patch("plugins.modules.purefa_network.IPNetwork")
    @patch("plugins.modules.purefa_network.valid_ipv4")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_ip_version_change_incompatible_gateway(
        self, mock_check_response, mock_valid_ipv4, mock_ipnetwork, mock_ipaddress
    ):
        """Test IP version change with incompatible gateway fails"""
        import pytest

        mock_valid_ipv4.return_value = False  # IPv6 address
        # Mock IPAddress to return different versions
        mock_new_addr = Mock()
        mock_new_addr.version = 6
        mock_old_addr = Mock()
        mock_old_addr.version = 4
        mock_gateway = Mock()
        mock_gateway.version = 4  # Gateway still IPv4 - incompatible!

        def mock_ipaddr_side_effect(addr):
            if addr == "2001:db8::1":
                return mock_new_addr
            elif addr == "10.0.0.1":
                return mock_old_addr
            elif addr == "10.0.0.254":
                return mock_gateway
            return Mock(version=4)

        mock_ipaddress.side_effect = mock_ipaddr_side_effect
        mock_network = Mock()
        mock_network.netmask = "64"
        mock_network.__contains__ = Mock(return_value=True)
        mock_ipnetwork.return_value = mock_network
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "2001:db8::1/64",  # Changing to IPv6
            "gateway": "10.0.0.254",  # Still IPv4 gateway - incompatible!
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = "10.0.0.254"
        mock_interface.eth.address = "10.0.0.1"  # Currently IPv4
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_with(
            msg="Changing IP protocol requires gateway to change as well."
        )


class TestUpdateInterfaceNewSubinterfaces:
    """Test cases for adding new subinterfaces in update_interface"""

    @patch("plugins.modules.purefa_network.ReferenceNoId")
    @patch("plugins.modules.purefa_network._check_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_add_subinterfaces(
        self, mock_check_response, mock_check_subinterfaces, mock_reference_no_id
    ):
        """Test adding subinterfaces to an interface with gateway"""
        import pytest

        mock_check_subinterfaces.return_value = ["ct0.eth1", "ct1.eth1"]
        mock_reference_no_id.return_value = Mock()
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "vif1",
            "state": "present",
            "address": "10.0.0.1/24",
            "gateway": "10.0.0.254",
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": ["eth1"],
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "vif1"
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []  # Currently no subinterfaces
        mock_interface.eth.gateway = "10.0.0.254"
        mock_interface.eth.address = "10.0.0.1"
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateInterfaceIpv6:
    """Test cases for IPv6 address in create_interface"""

    @patch("plugins.modules.purefa_network.valid_ipv4")
    @patch("plugins.modules.purefa_network._create_subinterfaces")
    @patch("plugins.modules.purefa_network.check_response")
    def test_create_vif_with_ipv6_address(
        self, mock_check_response, mock_create_subinterfaces, mock_valid_ipv4
    ):
        """Test creating VIF with IPv6 address extracts netmask from CIDR"""
        import pytest

        mock_create_subinterfaces.return_value = ([], [])
        mock_valid_ipv4.return_value = False  # IPv6 address
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "vif1",
            "interface": "vif",
            "subnet": None,
            "address": "2001:db8::1/64",  # IPv6 with CIDR
            "gateway": None,
            "mtu": 1500,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404)
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            create_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateInterfaceGatewayIncompatibleNoGateway:
    """Test cases for gateway incompatibility when no gateway provided"""

    @patch("plugins.modules.purefa_network.IPNetwork")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_existing_gateway_not_in_new_subnet(
        self, mock_check_response, mock_ipnetwork
    ):
        """Test that existing gateway not in new subnet fails"""
        import pytest

        # Mock IPNetwork to NOT contain the existing gateway
        mock_network = Mock()
        mock_network.netmask = "255.255.255.0"
        mock_network.__contains__ = Mock(
            return_value=False
        )  # Existing gateway NOT in subnet
        mock_network.__eq__ = Mock(return_value=False)  # Gateway doesn't equal network
        mock_ipnetwork.return_value = mock_network
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "192.168.1.1/24",  # Changing subnet
            "gateway": None,  # No new gateway - will use existing
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = (
            "10.0.0.254"  # Existing gateway in different subnet
        )
        mock_interface.eth.address = "10.0.0.1"
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_with(
            msg="Gateway and subnet are not compatible."
        )


class TestUpdateInterfaceNetmaskZero:
    """Test cases for netmask zero handling"""

    @patch("plugins.modules.purefa_network.valid_ipv4")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_ipv6_netmask_zero(
        self, mock_check_response, mock_valid_ipv4
    ):
        """Test IPv6 address with /0 netmask sets empty netmask"""
        import pytest

        mock_valid_ipv4.return_value = False  # IPv6 address
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "2001:db8::1/0",  # IPv6 with /0 - remove IP
            "gateway": None,
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = None
        mock_interface.eth.address = "2001:db8::2"
        mock_interface.eth.netmask = "64"
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateInterfaceIpv4GatewayNotInSubnet:
    """Test cases for IPv4 gateway not in subnet validation"""

    @patch("plugins.modules.purefa_network.IPAddress")
    @patch("plugins.modules.purefa_network.IPNetwork")
    @patch("plugins.modules.purefa_network.valid_ipv4")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_ipv4_gateway_not_in_subnet(
        self, mock_check_response, mock_valid_ipv4, mock_ipnetwork, mock_ipaddress
    ):
        """Test IPv4 gateway not in subnet fails"""
        import pytest

        mock_valid_ipv4.return_value = True  # IPv4 address
        # Mock IPAddress for netmask_bits
        mock_netmask_obj = Mock()
        mock_netmask_obj.netmask_bits.return_value = 24
        mock_ipaddress.return_value = mock_netmask_obj
        # Mock IPNetwork to NOT contain the gateway
        mock_network = Mock()
        mock_network.netmask = "255.255.255.0"
        mock_network.__contains__ = Mock(return_value=False)  # Gateway NOT in subnet
        mock_ipnetwork.return_value = mock_network
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "10.0.0.1/24",
            "gateway": "192.168.1.1",  # Gateway in different subnet
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.services = []
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = "10.0.0.254"
        mock_interface.eth.address = "10.0.0.1"
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.fail_json.assert_called_with(
            msg="Gateway and subnet are not compatible."
        )


class TestUpdateInterfaceEmptyGatewayException:
    """Test cases for empty gateway determination with exception"""

    @patch("plugins.modules.purefa_network.valid_ipv4")
    @patch("plugins.modules.purefa_network.check_response")
    def test_update_interface_invalid_address_ipv6_gateway(
        self, mock_check_response, mock_valid_ipv4
    ):
        """Test that invalid address falls back to IPv6 empty gateway"""
        import pytest

        # valid_ipv4 returns False first (for lines 401, 410), then raises exception (for line 501)
        call_count = [0]

        def valid_ipv4_side_effect(addr):
            call_count[0] += 1
            if call_count[0] >= 3:  # Line 501 in the patch_network_interfaces path
                raise Exception("Invalid address")
            return False  # For lines 401 and 410, IPv6 path

        mock_valid_ipv4.side_effect = valid_ipv4_side_effect
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "invalid/24",  # Invalid address
            "gateway": None,  # No gateway - triggers else path at line 499
            "mtu": 1500,
            "servicelist": ["iscsi"],  # Trigger service change
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.services = []  # Different services
        mock_interface.eth = Mock()
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.gateway = None
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateInterfaceGatewayOnlyBugFixes:
    """Test cases for gateway-only operations that previously caused AddrFormatError"""

    @patch("plugins.modules.purefa_network.check_response")
    def test_set_gateway_only_no_existing_address(self, mock_check_response):
        """Test setting gateway when no IP address is configured - should not crash"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": None,
            "gateway": "10.0.0.1",
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.eth = Mock()
        mock_interface.eth.address = None  # No existing address
        mock_interface.eth.netmask = None
        mock_interface.eth.gateway = None  # No existing gateway
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["replication"]
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        # Should not raise AddrFormatError
        update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.valid_ipv4")
    @patch("plugins.modules.purefa_network.IPNetwork")
    @patch("plugins.modules.purefa_network.check_response")
    def test_clear_ipv4_address_without_gateway(
        self, mock_check_response, mock_ipnetwork, mock_valid_ipv4
    ):
        """Test clearing IPv4 address with 0.0.0.0/0 without specifying gateway - should not crash"""
        mock_valid_ipv4.return_value = True
        mock_net = MagicMock()
        mock_net.netmask = "0.0.0.0"
        # 0.0.0.0/0 contains any existing gateway
        mock_net.__contains__ = Mock(return_value=True)
        mock_ipnetwork.return_value = mock_net

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "0.0.0.0/0",  # Clear address
            "gateway": None,  # No gateway specified
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.eth = Mock()
        mock_interface.eth.address = "10.0.0.5"  # Existing address
        mock_interface.eth.netmask = "255.255.255.0"
        mock_interface.eth.gateway = "10.0.0.1"  # Existing gateway
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["replication"]  # Not management/app, so allowed
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        # Should not raise AddrFormatError: failed to detect a valid IP address from ''
        update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.valid_ipv4")
    @patch("plugins.modules.purefa_network.IPNetwork")
    @patch("plugins.modules.purefa_network.check_response")
    def test_clear_ipv6_address_without_gateway(
        self, mock_check_response, mock_ipnetwork, mock_valid_ipv4
    ):
        """Test clearing IPv6 address with ::/0 without specifying gateway - should work"""
        mock_valid_ipv4.return_value = False  # IPv6

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": "::/0",  # Clear IPv6 address
            "gateway": None,  # No gateway specified
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.eth = Mock()
        mock_interface.eth.address = "2001:db8::5"  # Existing IPv6 address
        mock_interface.eth.netmask = "64"
        mock_interface.eth.gateway = "2001:db8::1"  # Existing gateway
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["replication"]
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.check_response")
    def test_set_ipv6_gateway_only_no_existing_address(self, mock_check_response):
        """Test setting IPv6 gateway when no IP address is configured"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "state": "present",
            "address": None,
            "gateway": "2001:db8::1",  # IPv6 gateway
            "mtu": 1500,
            "servicelist": None,
            "enabled": True,
            "subinterfaces": None,
            "subordinates": None,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_interface.eth = Mock()
        mock_interface.eth.address = None
        mock_interface.eth.netmask = None
        mock_interface.eth.gateway = None
        mock_interface.eth.mtu = 1500
        mock_interface.eth.subinterfaces = []
        mock_interface.eth.subordinates = None
        mock_interface.services = ["replication"]
        mock_interface.enabled = True
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class FakeIPNetwork:
    """Minimal IPNetwork stand-in - the real netaddr is mocked out globally.

    The global mock returns a 255.255.255.0 netmask for every input, which
    cannot express the 0.0.0.0/0 used to clear an address.
    """

    _NETMASKS = {"0": "0.0.0.0", "16": "255.255.0.0", "24": "255.255.255.0"}

    def __init__(self, cidr):
        self.cidr = str(cidr)
        self.netmask = self._NETMASKS[self.cidr.split("/", 1)[1]]

    def __contains__(self, item):
        return True


class FakeIPAddress:
    """Minimal IPAddress stand-in, paired with FakeIPNetwork"""

    _NETMASK_BITS = {"0.0.0.0": 0, "255.255.0.0": 16, "255.255.255.0": 24}

    def __init__(self, address):
        self.address = str(address)

    def netmask_bits(self):
        return self._NETMASK_BITS[self.address]

    @property
    def version(self):
        return 6 if ":" in self.address else 4


def _clear_params(name="ct0.eth4"):
    """Params for the play in issue #1042 - remove address and gateway"""
    return {
        "name": name,
        "state": "present",
        "address": "0.0.0.0/0",
        "gateway": "0.0.0.0",
        "mtu": None,
        "servicelist": None,
        "subinterfaces": None,
        "subordinates": None,
        "enabled": True,
    }


class TestUpdateEthInterfaceClearAddress:
    """Regression tests for issue #1042 - clearing an address reports changed"""

    @patch("plugins.modules.purefa_network.IPAddress", FakeIPAddress)
    @patch("plugins.modules.purefa_network.IPNetwork", FakeIPNetwork)
    def test_clear_address_is_idempotent(self):
        """Re-running the clear play on a cleared interface reports no change"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = _clear_params()
        mock_array = Mock()
        # An interface with no IP settings - the array reports them as null
        interface = _eth_interface(
            FakeEth(
                mtu=1500,
                subinterfaces=[],
                address=None,
                netmask=None,
                gateway=None,
            )
        )
        mock_array.get_network_interfaces.return_value = Mock(items=[interface])

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_array.patch_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_network.IPAddress", FakeIPAddress)
    @patch("plugins.modules.purefa_network.IPNetwork", FakeIPNetwork)
    def test_clear_address_is_idempotent_when_array_reports_zeros(self):
        """A cleared interface reported as 0.0.0.0 also reports no change"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = _clear_params()
        mock_array = Mock()
        interface = _eth_interface(
            FakeEth(
                mtu=1500,
                subinterfaces=[],
                address="0.0.0.0",
                netmask="",
                gateway="0.0.0.0",
            )
        )
        mock_array.get_network_interfaces.return_value = Mock(items=[interface])

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_array.patch_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_network.check_response")
    @patch("plugins.modules.purefa_network.IPAddress", FakeIPAddress)
    @patch("plugins.modules.purefa_network.IPNetwork", FakeIPNetwork)
    def test_clear_address_on_configured_interface_changes(self, mock_check_response):
        """The first run against a configured interface still clears it"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = _clear_params()
        mock_array = Mock()
        interface = _eth_interface(
            FakeEth(
                mtu=1500,
                subinterfaces=[],
                address="10.21.200.18",
                netmask="255.255.255.0",
                gateway="10.21.200.1",
            )
        )
        mock_array.get_network_interfaces.return_value = Mock(items=[interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_array.patch_network_interfaces.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.check_response")
    @patch("plugins.modules.purefa_network.IPAddress", FakeIPAddress)
    @patch("plugins.modules.purefa_network.IPNetwork", FakeIPNetwork)
    def test_set_address_on_cleared_interface_changes(self, mock_check_response):
        """Setting an address on a cleared interface is still a change"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = _clear_params()
        mock_module.params["address"] = "10.21.200.18/24"
        mock_module.params["gateway"] = "10.21.200.1"
        mock_array = Mock()
        interface = _eth_interface(
            FakeEth(
                mtu=1500,
                subinterfaces=[],
                address=None,
                netmask=None,
                gateway=None,
            )
        )
        mock_array.get_network_interfaces.return_value = Mock(items=[interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_array.patch_network_interfaces.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_network.check_response")
    @patch("plugins.modules.purefa_network.IPAddress", FakeIPAddress)
    @patch("plugins.modules.purefa_network.IPNetwork", FakeIPNetwork)
    def test_set_address_without_gateway_on_interface_with_no_gateway(
        self, mock_check_response
    ):
        """Setting an address with no gateway must not raise AttributeError

        The gateway compatibility check read interface.eth.gateway directly,
        which raises AttributeError when the interface has no gateway.
        """
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = _clear_params()
        mock_module.params["address"] = "10.21.200.18/24"
        mock_module.params["gateway"] = None
        mock_array = Mock()
        interface = _eth_interface(
            FakeEth(
                mtu=1500,
                subinterfaces=[],
                address=None,
                netmask=None,
                gateway=None,
            )
        )
        mock_array.get_network_interfaces.return_value = Mock(items=[interface])
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            update_interface(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
