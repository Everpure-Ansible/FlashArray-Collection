# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_kmip module."""

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

from plugins.modules.purefa_kmip import (
    delete_kmip,
    test_kmip as kmip_test,
    create_kmip,
    update_kmip,
)


class TestDeleteKmip:
    """Tests for delete_kmip function"""

    def test_delete_kmip_check_mode(self):
        """Test delete_kmip in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "kmip1"}
        mock_module.check_mode = True
        mock_array = Mock()

        delete_kmip(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.delete_kmip.assert_not_called()

    def test_delete_kmip_success(self):
        """Test delete_kmip successfully deletes"""
        mock_module = Mock()
        mock_module.params = {"name": "kmip1"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.delete_kmip.return_value = Mock(status_code=200)

        delete_kmip(mock_module, mock_array)

        mock_array.delete_kmip.assert_called_once_with(names=["kmip1"])
        mock_module.exit_json.assert_called_with(changed=True)


class TestKmipTest:
    """Tests for test_kmip function"""

    def test_kmip_test_success(self):
        """Test test_kmip returns test results"""
        mock_module = Mock()
        mock_module.params = {"name": "kmip1"}
        mock_array = Mock()

        # Create mock test response component
        mock_component = Mock()
        mock_component.enabled = True
        mock_component.success = True
        mock_component.component_address = "192.168.1.100"
        mock_component.component_name = "kmip1"
        mock_component.description = "Test description"
        mock_component.destination = "kmip.example.com"
        mock_component.result_details = "Success"
        mock_component.test_type = "connection"
        mock_component.resource = Mock()
        mock_component.resource.name = "test-resource"

        mock_array.get_kmip_test.return_value.items = [mock_component]

        kmip_test(mock_module, mock_array)

        mock_array.get_kmip_test.assert_called_once_with(names=["kmip1"])
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args
        assert call_args[1]["changed"] is True
        assert len(call_args[1]["test_response"]) == 1
        assert call_args[1]["test_response"][0]["enabled"] == "true"
        assert call_args[1]["test_response"][0]["success"] == "true"

    def test_kmip_test_disabled_failed(self):
        """Test test_kmip with disabled and failed component"""
        mock_module = Mock()
        mock_module.params = {"name": "kmip1"}
        mock_array = Mock()

        mock_component = Mock()
        mock_component.enabled = False
        mock_component.success = False
        mock_component.component_address = "192.168.1.100"
        mock_component.component_name = "kmip1"
        mock_component.description = "Test description"
        mock_component.destination = "kmip.example.com"
        mock_component.test_type = "connection"
        mock_component.resource = Mock()
        mock_component.resource.name = "test-resource"
        # No result_details
        del mock_component.result_details

        mock_array.get_kmip_test.return_value.items = [mock_component]

        kmip_test(mock_module, mock_array)

        call_args = mock_module.exit_json.call_args
        assert call_args[1]["test_response"][0]["enabled"] == "false"
        assert call_args[1]["test_response"][0]["success"] == "false"


class TestCreateKmip:
    """Tests for create_kmip function"""

    def test_create_kmip_check_mode(self):
        """Test create_kmip in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "kmip1",
            "certificate": "cert1",
            "uris": ["kmip://server1:5696"],
            "ca_certificate": "ca-cert",
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_certificates.return_value = Mock(status_code=200)

        create_kmip(mock_module, mock_array)

        mock_array.post_kmip.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_kmip.check_response")
    def test_create_kmip_success(self, mock_check_response):
        """Test create_kmip successfully creates"""
        mock_module = Mock()
        mock_module.params = {
            "name": "kmip1",
            "certificate": "cert1",
            "uris": ["kmip://server1:5696"],
            "ca_certificate": "ca-cert",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_certificates.return_value = Mock(status_code=200)
        mock_array.post_kmip.return_value = Mock(status_code=200)

        create_kmip(mock_module, mock_array)

        mock_array.post_kmip.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateKmip:
    """Tests for update_kmip function"""

    def test_update_kmip_no_change(self):
        """Test update_kmip when no changes needed"""
        mock_module = Mock()
        mock_module.params = {
            "name": "kmip1",
            "certificate": None,
            "uris": None,
            "ca_certificate": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Mock current KMIP config
        mock_cert = Mock()
        mock_cert.name = "cert1"
        mock_kmip = Mock()
        mock_kmip.certificate = mock_cert
        mock_kmip.uris = ["kmip://server1:5696"]
        mock_kmip.ca_certificate = "ca-cert"
        mock_array.get_kmip.return_value.items = [mock_kmip]

        update_kmip(mock_module, mock_array)

        mock_array.patch_kmip.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_kmip.check_response")
    def test_update_kmip_uri_change(self, mock_check_response):
        """Test update_kmip when URIs change"""
        mock_module = Mock()
        mock_module.params = {
            "name": "kmip1",
            "certificate": None,
            "uris": ["kmip://new-server:5696"],
            "ca_certificate": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Mock current KMIP config
        mock_cert = Mock()
        mock_cert.name = "cert1"
        mock_kmip = Mock()
        mock_kmip.certificate = mock_cert
        mock_kmip.uris = ["kmip://server1:5696"]
        mock_kmip.ca_certificate = "ca-cert"
        mock_array.get_kmip.return_value.items = [mock_kmip]
        mock_array.patch_kmip.return_value = Mock(status_code=200)

        update_kmip(mock_module, mock_array)

        mock_array.patch_kmip.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_kmip_check_mode_with_changes(self):
        """Test update_kmip in check mode when changes would be made"""
        mock_module = Mock()
        mock_module.params = {
            "name": "kmip1",
            "certificate": None,
            "uris": ["kmip://new-server:5696"],
            "ca_certificate": None,
        }
        mock_module.check_mode = True
        mock_array = Mock()

        # Mock current KMIP config - different URIs
        mock_cert = Mock()
        mock_cert.name = "cert1"
        mock_kmip = Mock()
        mock_kmip.certificate = mock_cert
        mock_kmip.uris = ["kmip://server1:5696"]
        mock_kmip.ca_certificate = "ca-cert"
        mock_array.get_kmip.return_value.items = [mock_kmip]

        update_kmip(mock_module, mock_array)

        mock_array.patch_kmip.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)
