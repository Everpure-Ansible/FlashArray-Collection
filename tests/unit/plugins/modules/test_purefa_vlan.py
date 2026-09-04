# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_vlan module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock, patch

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

from plugins.modules.purefa_vlan import (
    _get_subnet,
    _get_interface,
    _get_vif,
    delete_vif,
    create_vif,
)


class TestGetSubnet:
    """Test cases for _get_subnet function"""

    def test_get_subnet_exists(self):
        """Test _get_subnet returns subnet when it exists"""
        mock_module = Mock()
        mock_module.params = {"subnet": "test-subnet"}
        mock_array = Mock()
        mock_subnet = Mock()
        mock_subnet.name = "test-subnet"
        mock_array.get_subnets.return_value = Mock(status_code=200, items=[mock_subnet])

        result = _get_subnet(mock_module, mock_array)

        assert result == mock_subnet

    def test_get_subnet_not_exists(self):
        """Test _get_subnet returns None when subnet doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"subnet": "nonexistent"}
        mock_array = Mock()
        mock_array.get_subnets.return_value = Mock(status_code=404, items=[])

        result = _get_subnet(mock_module, mock_array)

        assert result is None


class TestGetInterface:
    """Test cases for _get_interface function"""

    def test_get_interface_exists(self):
        """Test _get_interface returns interface when it exists"""
        mock_module = Mock()
        mock_module.params = {"name": "ct0.eth0"}
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_interface]
        )

        result = _get_interface(mock_module, mock_array)

        assert result == mock_interface


class TestDeleteVif:
    """Test cases for delete_vif function"""

    def test_delete_vif_check_mode(self):
        """Test delete_vif in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "ct0.eth0", "subnet": "test-subnet"}
        mock_array = Mock()
        mock_subnet = {"vlan": 100}

        delete_vif(mock_module, mock_array, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestGetVif:
    """Test cases for _get_vif function"""

    def test_get_vif_exists(self):
        """Test _get_vif returns vif when it exists"""
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100
        mock_vif = Mock()
        mock_vif.name = "ct0.eth0.100"
        mock_array.get_network_interfaces.return_value = Mock(
            status_code=200, items=[mock_vif]
        )

        result = _get_vif(mock_array, mock_interface, mock_subnet)

        assert result == mock_vif

    def test_get_vif_not_exists(self):
        """Test _get_vif returns None when vif doesn't exist"""
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100
        mock_array.get_network_interfaces.return_value = Mock(status_code=404)

        result = _get_vif(mock_array, mock_interface, mock_subnet)

        assert result is None


class TestCreateVif:
    """Test cases for create_vif function"""

    def test_create_vif_check_mode(self):
        """Test create_vif in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "ct0.eth0",
            "subnet": "test-subnet",
            "address": "10.0.0.1",
            "enabled": True,
        }
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100

        create_vif(mock_module, mock_array, mock_interface, mock_subnet)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vlan.check_response")
    def test_create_vif_with_address(self, mock_check_response):
        """Test create_vif with address specified"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "subnet": "test-subnet",
            "address": "10.0.0.1",
            "enabled": True,
        }
        mock_array = Mock()
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100

        create_vif(mock_module, mock_array, mock_interface, mock_subnet)

        mock_array.post_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vlan.check_response")
    def test_create_vif_without_address(self, mock_check_response):
        """Test create_vif without address specified"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "subnet": "test-subnet",
            "address": None,
            "enabled": True,
        }
        mock_array = Mock()
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100

        create_vif(mock_module, mock_array, mock_interface, mock_subnet)

        mock_array.post_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vlan.check_response")
    def test_create_vif_disabled(self, mock_check_response):
        """Test create_vif with disabled interface"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "ct0.eth0",
            "subnet": "test-subnet",
            "address": "10.0.0.1",
            "enabled": False,
        }
        mock_array = Mock()
        mock_array.post_network_interfaces.return_value = Mock(status_code=200)
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100

        create_vif(mock_module, mock_array, mock_interface, mock_subnet)

        # Should call patch to disable the interface
        assert mock_array.patch_network_interfaces.call_count == 1
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteVifSuccess:
    """Additional test cases for delete_vif function"""

    @patch("plugins.modules.purefa_vlan.check_response")
    def test_delete_vif_success(self, mock_check_response):
        """Test delete_vif successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "ct0.eth0", "subnet": "test-subnet"}
        mock_array = Mock()
        mock_array.delete_network_interfaces.return_value = Mock(status_code=200)
        mock_subnet = Mock()
        mock_subnet.vlan = 100

        delete_vif(mock_module, mock_array, mock_subnet)

        mock_array.delete_network_interfaces.assert_called_once_with(
            names=["ct0.eth0.100"]
        )
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateVif:
    """Test cases for update_vif function"""

    @patch("plugins.modules.purefa_vlan._get_vif")
    def test_update_vif_no_changes(self, mock_get_vif):
        """Test update_vif with no changes needed"""
        from plugins.modules.purefa_vlan import update_vif

        mock_vif_info = Mock()
        mock_vif_info.name = "ct0.eth0.100"
        mock_vif_info.enabled = True
        mock_vif_info.eth = Mock()
        mock_vif_info.eth.address = "10.0.0.10"
        mock_get_vif.return_value = mock_vif_info
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"address": "10.0.0.10", "enabled": True}
        mock_array = Mock()
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100

        update_vif(mock_module, mock_array, mock_interface, mock_subnet)

        mock_array.patch_network_interfaces.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_vlan.check_response")
    @patch("plugins.modules.purefa_vlan._get_vif")
    def test_update_vif_change_address(self, mock_get_vif, mock_check_response):
        """Test update_vif changes IP address"""
        from plugins.modules.purefa_vlan import update_vif

        mock_vif_info = Mock()
        mock_vif_info.name = "ct0.eth0.100"
        mock_vif_info.enabled = True
        mock_vif_info.eth = Mock()
        mock_vif_info.eth.address = "10.0.0.10"
        mock_get_vif.return_value = mock_vif_info
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"address": "10.0.0.20", "enabled": True}
        mock_array = Mock()
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100

        update_vif(mock_module, mock_array, mock_interface, mock_subnet)

        mock_array.patch_network_interfaces.assert_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vlan.check_response")
    @patch("plugins.modules.purefa_vlan._get_vif")
    def test_update_vif_enable(self, mock_get_vif, mock_check_response):
        """Test update_vif enables disabled interface"""
        from plugins.modules.purefa_vlan import update_vif

        mock_vif_info = Mock()
        mock_vif_info.name = "ct0.eth0.100"
        mock_vif_info.enabled = False
        mock_vif_info.eth = Mock()
        mock_vif_info.eth.address = "10.0.0.10"
        mock_get_vif.return_value = mock_vif_info
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"address": None, "enabled": True}
        mock_array = Mock()
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100

        update_vif(mock_module, mock_array, mock_interface, mock_subnet)

        mock_array.patch_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_vlan.check_response")
    @patch("plugins.modules.purefa_vlan._get_vif")
    def test_update_vif_disable(self, mock_get_vif, mock_check_response):
        """Test update_vif disables enabled interface"""
        from plugins.modules.purefa_vlan import update_vif

        mock_vif_info = Mock()
        mock_vif_info.name = "ct0.eth0.100"
        mock_vif_info.enabled = True
        mock_vif_info.eth = Mock()
        mock_vif_info.eth.address = "10.0.0.10"
        mock_get_vif.return_value = mock_vif_info
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"address": None, "enabled": False}
        mock_array = Mock()
        mock_array.patch_network_interfaces.return_value = Mock(status_code=200)
        mock_interface = Mock()
        mock_interface.name = "ct0.eth0"
        mock_subnet = Mock()
        mock_subnet.vlan = 100

        update_vif(mock_module, mock_array, mock_interface, mock_subnet)

        mock_array.patch_network_interfaces.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)
