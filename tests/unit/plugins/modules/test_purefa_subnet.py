# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_subnet module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import ipaddress
from unittest.mock import Mock, MagicMock, patch


# Create a mock IPNetwork class that behaves like netaddr.IPNetwork
class MockIPNetwork:
    """Mock IPNetwork class for testing"""

    def __init__(self, cidr):
        self.network = ipaddress.ip_network(cidr, strict=False)

    def __contains__(self, item):
        try:
            return ipaddress.ip_address(item) in self.network
        except ValueError:
            return False


def mock_valid_ipv4(addr):
    """Mock valid_ipv4 function"""
    try:
        ip = ipaddress.ip_address(addr)
        return ip.version == 4
    except ValueError:
        return False


def mock_valid_ipv6(addr):
    """Mock valid_ipv6 function"""
    try:
        ip = ipaddress.ip_address(addr)
        return ip.version == 6
    except ValueError:
        return False


# Create mock netaddr module
mock_netaddr = MagicMock()
mock_netaddr.IPNetwork = MockIPNetwork
mock_netaddr.valid_ipv4 = mock_valid_ipv4
mock_netaddr.valid_ipv6 = mock_valid_ipv6
sys.modules["netaddr"] = mock_netaddr

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
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.common"] = (
    MagicMock()
)
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.error_handlers"
] = MagicMock()

# Create a mock version module with real LooseVersion
mock_version_module = MagicMock()
from packaging.version import Version as LooseVersion

mock_version_module.LooseVersion = LooseVersion
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    mock_version_module
)

from plugins.modules.purefa_subnet import (
    _get_subnet,
    delete_subnet,
    create_subnet,
    update_subnet,
)


class TestGetSubnet:
    """Tests for _get_subnet function"""

    def test_get_subnet_exists(self):
        """Test _get_subnet returns subnet when it exists"""
        mock_module = Mock()
        mock_module.params = {"name": "subnet1"}
        mock_array = Mock()
        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_array.get_subnets.return_value = Mock(status_code=200, items=[mock_subnet])

        result = _get_subnet(mock_module, mock_array)

        assert result == mock_subnet
        mock_array.get_subnets.assert_called_once_with(names=["subnet1"])

    def test_get_subnet_not_exists(self):
        """Test _get_subnet returns None when subnet doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent"}
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=400, items=[])

        result = _get_subnet(mock_module, mock_array)

        assert result is None


class TestDeleteSubnet:
    """Tests for delete_subnet function"""

    def test_delete_subnet_check_mode(self):
        """Test delete_subnet in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "subnet1"}
        mock_module.check_mode = True
        mock_array = Mock()

        delete_subnet(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.delete_subnets.assert_not_called()

    def test_delete_subnet_success(self):
        """Test delete_subnet successfully deletes"""
        mock_module = Mock()
        mock_module.params = {"name": "subnet1"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.delete_subnets.return_value = Mock(status_code=200)

        delete_subnet(mock_module, mock_array)

        mock_array.delete_subnets.assert_called_once_with(names=["subnet1"])
        mock_module.exit_json.assert_called_with(changed=True)


class TestCreateSubnet:
    """Test cases for create_subnet function"""

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_no_prefix_fails(self, mock_check_response):
        """Test create_subnet fails without prefix"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "subnet1",
            "prefix": None,
        }
        mock_array = Mock()

        with pytest.raises(SystemExit):
            create_subnet(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_check_mode(self, mock_check_response):
        """Test create_subnet in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "subnet1",
            "prefix": "10.0.0.0/24",
            "gateway": None,
            "vlan": None,
            "mtu": None,
            "enabled": True,
        }
        mock_array = Mock()

        create_subnet(mock_module, mock_array)

        mock_array.post_subnets.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_success(self, mock_check_response):
        """Test create_subnet successfully creates"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "subnet1",
            "prefix": "10.0.0.0/24",
            "gateway": None,
            "vlan": None,
            "mtu": None,
            "enabled": True,
        }
        mock_array = Mock()
        mock_array.post_subnets.return_value = Mock(status_code=200)

        create_subnet(mock_module, mock_array)

        mock_array.post_subnets.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_vlan_out_of_range(self, mock_check_response):
        """Test create_subnet fails with invalid VLAN"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "subnet1",
            "prefix": "10.0.0.0/24",
            "gateway": None,
            "vlan": 5000,  # Out of range
            "mtu": None,
            "enabled": True,
        }
        mock_array = Mock()

        with pytest.raises(SystemExit):
            create_subnet(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_mtu_out_of_range(self, mock_check_response):
        """Test create_subnet fails with invalid MTU"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "subnet1",
            "prefix": "10.0.0.0/24",
            "gateway": None,
            "vlan": None,
            "mtu": 10000,  # Out of range
            "enabled": True,
        }
        mock_array = Mock()

        with pytest.raises(SystemExit):
            create_subnet(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestUpdateSubnet:
    """Tests for update_subnet function"""

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_no_change(self, mock_check_response):
        """Test update_subnet when no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": None,
            "vlan": None,
            "mtu": None,
            "gateway": None,
            "enabled": True,
        }

        # Use dict for subnet because function accesses subnet["gateway"]
        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True
        # Make subnet subscriptable for subnet["gateway"]
        mock_subnet.__getitem__ = Mock(return_value="10.0.0.1")

        mock_array = Mock()

        update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_array.patch_subnets.assert_not_called()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_change_mtu(self, mock_check_response):
        """Test update_subnet with MTU change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": None,
            "vlan": None,
            "mtu": 9000,  # Change MTU
            "gateway": None,
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True
        # Make subnet subscriptable for subnet["gateway"]
        mock_subnet.__getitem__ = Mock(return_value="10.0.0.1")

        mock_array = Mock()
        mock_array.patch_subnets.return_value = Mock(status_code=200)

        update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_subnets.assert_called_once()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_check_mode(self, mock_check_response):
        """Test update_subnet in check mode with changes"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "prefix": None,
            "vlan": 200,  # Change VLAN
            "mtu": None,
            "gateway": None,
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True
        # Make subnet subscriptable for subnet["gateway"]
        mock_subnet.__getitem__ = Mock(return_value="10.0.0.1")

        mock_array = Mock()

        update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_subnets.assert_not_called()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_vlan_out_of_range(self, mock_check_response):
        """Test update_subnet fails with invalid VLAN"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "prefix": None,
            "vlan": 5000,  # Out of range
            "mtu": None,
            "gateway": None,
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True

        mock_array = Mock()

        with pytest.raises(SystemExit):
            update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_mtu_out_of_range(self, mock_check_response):
        """Test update_subnet fails with invalid MTU"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "prefix": None,
            "vlan": None,
            "mtu": 500,  # Out of range - minimum is 568
            "gateway": None,
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True

        mock_array = Mock()

        with pytest.raises(SystemExit):
            update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_change_enabled(self, mock_check_response):
        """Test update_subnet changes enabled state"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": None,
            "vlan": None,
            "mtu": None,
            "gateway": None,
            "enabled": False,  # Change from True to False
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True
        mock_subnet.__getitem__ = Mock(return_value="10.0.0.1")

        mock_array = Mock()
        mock_array.patch_subnets.return_value = Mock(status_code=200)

        update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_subnets.assert_called()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_change_mtu(self, mock_check_response):
        """Test update_subnet changes MTU"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": None,
            "vlan": None,
            "mtu": 9000,  # Change MTU
            "gateway": None,
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True
        mock_subnet.__getitem__ = Mock(return_value="10.0.0.1")

        mock_array = Mock()
        mock_array.patch_subnets.return_value = Mock(status_code=200)

        update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_subnets.assert_called()


class TestUpdateSubnetGateway:
    """Tests for update_subnet function gateway validation"""

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_with_gateway(self, mock_check_response):
        """Test update_subnet with gateway change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": "10.0.0.0/24",
            "vlan": None,
            "mtu": None,
            "gateway": "10.0.0.254",
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True

        mock_array = Mock()
        mock_array.patch_subnets.return_value = Mock(status_code=200)

        update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_subnets.assert_called()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_gateway_incompatible(self, mock_check_response):
        """Test update_subnet fails with incompatible gateway"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "prefix": "10.0.0.0/24",
            "vlan": None,
            "mtu": None,
            "gateway": "192.168.1.1",  # Not in subnet
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True

        mock_array = Mock()

        with pytest.raises(SystemExit):
            update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_prefix_change_with_new_gateway(self, mock_check_response):
        """Test update_subnet when prefix changes with a new gateway provided"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": "192.168.1.0/24",  # New prefix
            "vlan": None,
            "mtu": None,
            "gateway": "192.168.1.1",  # New gateway matching new prefix
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True

        mock_array = Mock()
        mock_array.patch_subnets.return_value = Mock(status_code=200)

        update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_subnets.assert_called()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_no_gateway_ipv4_sets_default(self, mock_check_response):
        """Test update_subnet with no gateway for IPv4 subnet sets default 0.0.0.0"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": None,
            "vlan": None,
            "mtu": None,
            "gateway": None,
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = None  # No gateway set - will be set to 0.0.0.0
        mock_subnet.enabled = True

        mock_array = Mock()
        mock_array.patch_subnets.return_value = Mock(status_code=200)

        update_subnet(mock_module, mock_array, mock_subnet)

        # Changed is True because gateway is set from None to 0.0.0.0
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_no_gateway_ipv6_sets_default(self, mock_check_response):
        """Test update_subnet with no gateway for IPv6 subnet sets default ::"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": None,
            "vlan": None,
            "mtu": None,
            "gateway": None,
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "2001:db8::/64"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = None  # No gateway set - will be set to ::
        mock_subnet.enabled = True

        mock_array = Mock()
        mock_array.patch_subnets.return_value = Mock(status_code=200)

        update_subnet(mock_module, mock_array, mock_subnet)

        # Changed is True because gateway is set from None to ::
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_already_has_ipv4_gateway(self, mock_check_response):
        """Test update_subnet with existing IPv4 gateway - no change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": None,
            "vlan": None,
            "mtu": None,
            "gateway": None,
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = 100
        mock_subnet.gateway = "10.0.0.1"  # Has existing gateway
        mock_subnet.enabled = True

        mock_array = Mock()

        update_subnet(mock_module, mock_array, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_array.patch_subnets.assert_not_called()


class TestCreateSubnetGateway:
    """Tests for create_subnet function with gateway"""

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_gateway_incompatible(self, mock_check_response):
        """Test create_subnet fails with incompatible gateway"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "subnet1",
            "prefix": "10.0.0.0/24",
            "gateway": "192.168.1.1",  # Not in subnet
            "vlan": None,
            "mtu": None,
            "enabled": True,
        }
        mock_array = Mock()

        with pytest.raises(SystemExit):
            create_subnet(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_with_valid_vlan(self, mock_check_response):
        """Test create_subnet with valid VLAN"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "subnet1",
            "prefix": "10.0.0.0/24",
            "gateway": None,
            "vlan": 100,  # Valid VLAN
            "mtu": None,
            "enabled": True,
        }
        mock_array = Mock()
        mock_array.post_subnets.return_value = Mock(status_code=200)

        create_subnet(mock_module, mock_array)

        mock_array.post_subnets.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_with_valid_mtu(self, mock_check_response):
        """Test create_subnet with valid MTU"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "subnet1",
            "prefix": "10.0.0.0/24",
            "gateway": None,
            "vlan": None,
            "mtu": 9000,  # Valid MTU
            "enabled": True,
        }
        mock_array = Mock()
        mock_array.post_subnets.return_value = Mock(status_code=200)

        create_subnet(mock_module, mock_array)

        mock_array.post_subnets.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_with_gateway(self, mock_check_response):
        """Test create_subnet with valid gateway"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "subnet1",
            "prefix": "10.0.0.0/24",
            "gateway": "10.0.0.1",  # Valid gateway in subnet
            "vlan": None,
            "mtu": None,
            "enabled": True,
        }
        mock_array = Mock()
        mock_array.post_subnets.return_value = Mock(status_code=200)

        create_subnet(mock_module, mock_array)

        mock_array.post_subnets.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSubnetVlan:
    """Tests for update_subnet function with VLAN handling"""

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_update_subnet_vlan_not_set_normalizes_to_zero(self, mock_check_response):
        """Test update_subnet when vlan is not set normalizes None to 0"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "prefix": None,
            "vlan": None,  # Not changing
            "mtu": None,
            "gateway": None,
            "enabled": True,
        }

        mock_subnet = Mock()
        mock_subnet.name = "subnet1"
        mock_subnet.prefix = "10.0.0.0/24"
        mock_subnet.mtu = 1500
        mock_subnet.vlan = None  # VLAN not set - will be normalized to 0
        mock_subnet.gateway = "10.0.0.1"
        mock_subnet.enabled = True

        mock_array = Mock()
        mock_array.patch_subnets.return_value = Mock(status_code=200)

        update_subnet(mock_module, mock_array, mock_subnet)

        # Changed is True because vlan is normalized from None to 0
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateSubnetGatewayValidation:
    """Additional tests for create_subnet gateway validation"""

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_gateway_with_zero_address(self, mock_check_response):
        """Test create_subnet with zero gateway address"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "subnet1",
            "prefix": "10.0.0.0/24",
            "gateway": "0.0.0.0",  # Zero gateway - should be allowed
            "vlan": None,
            "mtu": None,
            "enabled": True,
        }
        mock_array = Mock()
        mock_array.post_subnets.return_value = Mock(status_code=200)

        create_subnet(mock_module, mock_array)

        mock_array.post_subnets.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_subnet.check_response")
    def test_create_subnet_gateway_ipv6_zero(self, mock_check_response):
        """Test create_subnet with IPv6 zero gateway"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "subnet1",
            "prefix": "2001:db8::/64",
            "gateway": "::",  # IPv6 zero gateway
            "vlan": None,
            "mtu": None,
            "enabled": True,
        }
        mock_array = Mock()
        mock_array.post_subnets.return_value = Mock(status_code=200)

        create_subnet(mock_module, mock_array)

        mock_array.post_subnets.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)
