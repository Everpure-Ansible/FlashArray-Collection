# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_saml module."""

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

from plugins.modules.purefa_saml import (
    delete_saml,
    test_saml as saml_test_func,
    create_saml,
    update_saml,
)


class TestDeleteSaml:
    """Tests for delete_saml function"""

    def test_delete_saml_check_mode(self):
        """Test delete_saml in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "saml1"}
        mock_module.check_mode = True
        mock_array = Mock()

        delete_saml(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.delete_sso_saml2_idps.assert_not_called()

    def test_delete_saml_success(self):
        """Test delete_saml successfully deletes"""
        mock_module = Mock()
        mock_module.params = {"name": "saml1"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.delete_sso_saml2_idps.return_value = Mock(status_code=200)

        delete_saml(mock_module, mock_array)

        mock_array.delete_sso_saml2_idps.assert_called_once_with(names=["saml1"])
        mock_module.exit_json.assert_called_with(changed=True)


class TestSamlTest:
    """Tests for test_saml function"""

    def test_saml_test_returns_response(self):
        """Test test_saml returns test response"""
        mock_module = Mock()
        mock_module.params = {"name": "saml1"}
        mock_array = Mock()

        # Create mock test result
        mock_result = Mock()
        mock_result.enabled = True
        mock_result.success = True
        mock_result.component_address = "10.0.0.1"
        mock_result.component_name = "saml1"
        mock_result.description = "SAML test"
        mock_result.destination = "https://idp.example.com"
        mock_result.result_details = "OK"
        mock_result.test_type = "connectivity"
        mock_result.resource = Mock()
        mock_result.resource.name = "array1"
        mock_array.get_sso_saml2_idps_test.return_value = Mock(items=[mock_result])

        saml_test_func(mock_module, mock_array)

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is True
        assert len(call_args["test_response"]) == 1
        assert call_args["test_response"][0]["enabled"] == "true"
        assert call_args["test_response"][0]["success"] == "true"


class TestCreateSaml:
    """Tests for create_saml function"""

    def test_create_saml_check_mode(self):
        """Test create_saml in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "saml1",
            "array_url": "https://array.example.com",
            "url": "https://idp.example.com",
            "metadata_url": "https://idp.example.com/metadata",
            "sign_request": True,
            "encrypt_asserts": True,
            "x509_cert": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "decryption_credential": "cred1",
            "signing_credential": "cred2",
            "enabled": False,
        }
        mock_array = Mock()

        create_saml(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_saml.check_response")
    def test_create_saml_success(self, mock_check_response):
        """Test create_saml successfully creates"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "saml1",
            "array_url": "https://array.example.com",
            "url": "https://idp.example.com",
            "metadata_url": "https://idp.example.com/metadata",
            "sign_request": True,
            "encrypt_asserts": True,
            "x509_cert": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "decryption_credential": "cred1",
            "signing_credential": "cred2",
            "enabled": False,
        }
        mock_array = Mock()
        mock_array.post_sso_saml2_idps.return_value = Mock(status_code=200)

        create_saml(mock_module, mock_array)

        mock_array.post_sso_saml2_idps.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateSaml:
    """Tests for update_saml function"""

    def test_update_saml_no_changes(self):
        """Test update_saml when no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "saml1",
            "array_url": None,
            "url": None,
            "metadata_url": None,
            "sign_request": True,
            "encrypt_asserts": False,
            "x509_cert": None,
            "decryption_credential": None,
            "signing_credential": None,
            "enabled": True,
        }
        mock_array = Mock()

        # Create mock current IDP
        mock_sp = Mock()
        mock_sp.signing_credential = Mock(name="cred1")
        mock_sp.decryption_credential = Mock(name="cred2")
        mock_idp = Mock()
        mock_idp.metadata_url = "https://idp.example.com/metadata"
        mock_idp.url = "https://idp.example.com"
        mock_idp.sign_request_enabled = True
        mock_idp.encrypt_assertion_enabled = False
        mock_idp.verification_certificate = "cert"
        mock_current = Mock()
        mock_current.array_url = "https://array.example.com"
        mock_current.enabled = True
        mock_current.sp = mock_sp
        mock_current.idp = mock_idp
        mock_array.get_sso_saml2_idps.return_value = Mock(items=[mock_current])

        update_saml(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_saml.check_response")
    def test_update_saml_with_changes(self, mock_check_response):
        """Test update_saml when changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "saml1",
            "array_url": "https://new-array.example.com",
            "url": None,
            "metadata_url": None,
            "sign_request": True,
            "encrypt_asserts": False,
            "x509_cert": None,
            "decryption_credential": None,
            "signing_credential": None,
            "enabled": True,
        }
        mock_array = Mock()

        # Create mock current IDP with different array_url
        mock_sp = Mock()
        mock_sp.signing_credential = Mock(name="cred1")
        mock_sp.decryption_credential = Mock(name="cred2")
        mock_idp = Mock()
        mock_idp.metadata_url = "https://idp.example.com/metadata"
        mock_idp.url = "https://idp.example.com"
        mock_idp.sign_request_enabled = True
        mock_idp.encrypt_assertion_enabled = False
        mock_idp.verification_certificate = "cert"
        mock_current = Mock()
        mock_current.array_url = "https://old-array.example.com"  # Different
        mock_current.enabled = True
        mock_current.sp = mock_sp
        mock_current.idp = mock_idp
        mock_array.get_sso_saml2_idps.return_value = Mock(items=[mock_current])
        mock_array.patch_sso_saml2_idps.return_value = Mock(status_code=200)

        update_saml(mock_module, mock_array)

        mock_array.patch_sso_saml2_idps.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_saml_check_mode_with_changes(self):
        """Test update_saml in check mode when changes would be made"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "saml1",
            "array_url": "https://new-array.example.com",
            "url": None,
            "metadata_url": None,
            "sign_request": True,
            "encrypt_asserts": False,
            "x509_cert": None,
            "decryption_credential": None,
            "signing_credential": None,
            "enabled": True,
        }
        mock_array = Mock()

        # Create mock current IDP with different array_url
        mock_sp = Mock()
        mock_sp.signing_credential = Mock(name="cred1")
        mock_sp.decryption_credential = Mock(name="cred2")
        mock_idp = Mock()
        mock_idp.metadata_url = "https://idp.example.com/metadata"
        mock_idp.url = "https://idp.example.com"
        mock_idp.sign_request_enabled = True
        mock_idp.encrypt_assertion_enabled = False
        mock_idp.verification_certificate = "cert"
        mock_current = Mock()
        mock_current.array_url = "https://old-array.example.com"  # Different
        mock_current.enabled = True
        mock_current.sp = mock_sp
        mock_current.idp = mock_idp
        mock_array.get_sso_saml2_idps.return_value = Mock(items=[mock_current])

        update_saml(mock_module, mock_array)

        mock_array.patch_sso_saml2_idps.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)
