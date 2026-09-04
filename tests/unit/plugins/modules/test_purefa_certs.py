# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_certs module."""

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

from plugins.modules.purefa_certs import (
    delete_cert,
    export_cert,
    import_cert,
    create_csr,
    create_cert,
    update_cert,
)


class TestDeleteCert:
    """Test cases for delete_cert function"""

    def test_delete_cert_check_mode(self):
        """Test delete_cert in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-cert"}
        mock_array = Mock()

        delete_cert(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_certs.check_response")
    def test_delete_cert_success(self, mock_check_response):
        """Test delete_cert successfully deletes certificate"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-cert"}
        mock_array = Mock()
        mock_array.delete_certificates.return_value = Mock(status_code=200)

        delete_cert(mock_module, mock_array)

        mock_array.delete_certificates.assert_called_once_with(names=["test-cert"])
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_delete_cert_management_fails(self):
        """Test delete_cert fails for management certificate"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "management"}
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()

        with pytest.raises(SystemExit):
            delete_cert(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        mock_array.delete_certificates.assert_not_called()


class TestExportCert:
    """Test cases for export_cert function"""

    def test_export_cert_success(self):
        """Test export_cert returns certificate"""
        mock_module = Mock()
        mock_module.params = {"name": "test-cert"}
        mock_array = Mock()
        mock_cert = Mock()
        mock_cert.certificate = (
            "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"
        )
        mock_array.get_certificates.return_value = Mock(
            status_code=200, items=[mock_cert]
        )

        export_cert(mock_module, mock_array)

        mock_module.exit_json.assert_called_once()


class TestImportCert:
    """Test cases for import_cert function"""

    def test_import_cert_check_mode(self):
        """Test import_cert in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-cert",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "intermeadiate_cert": None,
            "key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "passphrase": None,
        }
        mock_array = Mock()

        import_cert(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_certs.flasharray")
    @patch("plugins.modules.purefa_certs.check_response")
    def test_import_cert_success(self, mock_check_response, mock_flasharray):
        """Test import_cert successfully imports certificate"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-cert",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "intermeadiate_cert": None,
            "key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "passphrase": "secret",
        }
        mock_array = Mock()
        mock_array.post_certificates.return_value = Mock(status_code=200)

        import_cert(mock_module, mock_array, reimport=False)

        mock_array.post_certificates.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_certs.flasharray")
    @patch("plugins.modules.purefa_certs.check_response")
    def test_import_cert_reimport(self, mock_check_response, mock_flasharray):
        """Test import_cert with reimport flag"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-cert",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "intermeadiate_cert": "-----BEGIN CERTIFICATE-----\ninter\n-----END CERTIFICATE-----",
            "key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "passphrase": None,
        }
        mock_array = Mock()
        mock_array.patch_certificates.return_value = Mock(status_code=200)

        import_cert(mock_module, mock_array, reimport=True)

        mock_array.patch_certificates.assert_called_once()
        mock_array.post_certificates.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateCsr:
    """Test cases for create_csr function"""

    def test_create_csr_check_mode(self):
        """Test create_csr in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-cert",
            "common_name": "test.example.com",
            "country": "US",
            "email": "test@example.com",
            "locality": "Test City",
            "organization": "Test Org",
            "org_unit": "Test Unit",
            "province": "Test State",
            "csr_export_file": "/tmp/test.csr",
        }
        mock_array = Mock()
        # Mock the current certificate attributes
        mock_cert = Mock()
        mock_cert.common_name = "test.example.com"
        mock_cert.country = "US"
        mock_cert.email = "test@example.com"
        mock_cert.locality = "Test City"
        mock_cert.organization = "Test Org"
        mock_cert.organizational_unit = "Test Unit"
        mock_cert.state = "Test State"
        mock_array.get_certificates.return_value = Mock(items=[mock_cert])

        create_csr(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateCert:
    """Test cases for create_cert function"""

    @patch("plugins.modules.purefa_certs.flasharray")
    def test_create_cert_check_mode(self, mock_flasharray):
        """Test create_cert in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "new-cert",
            "common_name": "test.example.com",
            "country": "US",
            "email": "test@example.com",
            "key_size": 2048,
            "locality": "Test City",
            "organization": "Test Org",
            "org_unit": "Test Unit",
            "province": "Test State",
            "days": 365,
        }
        mock_array = Mock()

        create_cert(mock_module, mock_array)

        mock_array.post_certificates.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_certs.flasharray")
    @patch("plugins.modules.purefa_certs.check_response")
    def test_create_cert_success(self, mock_check_response, mock_flasharray):
        """Test create_cert successfully creates certificate"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "new-cert",
            "common_name": "test.example.com",
            "country": "US",
            "email": "test@example.com",
            "key_size": 4096,
            "locality": "Test City",
            "organization": "Test Org",
            "org_unit": "Test Unit",
            "province": "Test State",
            "days": 730,
        }
        mock_array = Mock()
        mock_array.post_certificates.return_value = Mock(status_code=200)

        create_cert(mock_module, mock_array)

        mock_array.post_certificates.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateCert:
    """Test cases for update_cert function"""

    @patch("plugins.modules.purefa_certs.flasharray")
    def test_update_cert_no_changes(self, mock_flasharray):
        """Test update_cert when no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-cert",
            "common_name": "test.example.com",
            "country": "US",
            "email": "test@example.com",
            "key_size": 2048,
            "locality": "Test City",
            "organization": "Test Org",
            "org_unit": "Test Unit",
            "province": "Test State",
            "generate": False,
        }
        mock_array = Mock()

        # Current cert has same values
        mock_cert = Mock()
        mock_cert.common_name = "test.example.com"
        mock_cert.country = "US"
        mock_cert.email = "test@example.com"
        mock_cert.key_size = 2048
        mock_cert.locality = "Test City"
        mock_cert.organization = "Test Org"
        mock_cert.organizational_unit = "Test Unit"
        mock_cert.state = "Test State"
        mock_array.get_certificates.return_value = Mock(items=[mock_cert])

        update_cert(mock_module, mock_array)

        mock_array.patch_certificates.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_certs.flasharray")
    @patch("plugins.modules.purefa_certs.check_response")
    def test_update_cert_common_name_change(self, mock_check_response, mock_flasharray):
        """Test update_cert when common_name changes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-cert",
            "common_name": "new.example.com",
            "country": None,
            "email": None,
            "key_size": None,
            "locality": None,
            "organization": None,
            "org_unit": None,
            "province": None,
            "generate": True,
        }
        mock_array = Mock()

        # Current cert has different common_name
        mock_cert = Mock()
        mock_cert.common_name = "old.example.com"
        mock_cert.country = "US"
        mock_cert.email = "test@example.com"
        mock_cert.key_size = 2048
        mock_cert.locality = "Test City"
        mock_cert.organization = "Test Org"
        mock_cert.organizational_unit = "Test Unit"
        mock_cert.state = "Test State"
        mock_array.get_certificates.return_value = Mock(items=[mock_cert])
        mock_array.patch_certificates.return_value = Mock(status_code=200)

        update_cert(mock_module, mock_array)

        mock_array.patch_certificates.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_certs.flasharray")
    def test_update_cert_check_mode(self, mock_flasharray):
        """Test update_cert in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-cert",
            "common_name": "new.example.com",
            "country": None,
            "email": None,
            "key_size": None,
            "locality": None,
            "organization": None,
            "org_unit": None,
            "province": None,
            "generate": False,
        }
        mock_array = Mock()

        # Current cert has different common_name
        mock_cert = Mock()
        mock_cert.common_name = "old.example.com"
        mock_cert.country = "US"
        mock_cert.email = "test@example.com"
        mock_cert.key_size = 2048
        mock_cert.locality = "Test City"
        mock_cert.organization = "Test Org"
        mock_cert.organizational_unit = "Test Unit"
        mock_cert.state = "Test State"
        mock_array.get_certificates.return_value = Mock(items=[mock_cert])

        update_cert(mock_module, mock_array)

        mock_array.patch_certificates.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_certs.flasharray")
    @patch("plugins.modules.purefa_certs.check_response")
    def test_update_cert_multiple_field_changes(
        self, mock_check_response, mock_flasharray
    ):
        """Test update_cert when multiple fields change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-cert",
            "common_name": "new.example.com",
            "country": "UK",
            "email": "new@example.com",
            "key_size": 4096,
            "locality": "New City",
            "organization": "New Org",
            "org_unit": "New Unit",
            "province": "New State",
            "generate": True,
        }
        mock_array = Mock()

        # Current cert has different values
        mock_cert = Mock()
        mock_cert.common_name = "old.example.com"
        mock_cert.country = "US"
        mock_cert.email = "old@example.com"
        mock_cert.key_size = 2048
        mock_cert.locality = "Old City"
        mock_cert.organization = "Old Org"
        mock_cert.organizational_unit = "Old Unit"
        mock_cert.state = "Old State"
        mock_array.get_certificates.return_value = Mock(items=[mock_cert])
        mock_array.patch_certificates.return_value = Mock(status_code=200)

        update_cert(mock_module, mock_array)

        mock_array.patch_certificates.assert_called_once()
        call_kwargs = mock_array.patch_certificates.call_args
        assert call_kwargs[1]["generate_new_key"] is True
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestImportCertReimport:
    """Test cases for import_cert reimport functionality"""

    @patch("plugins.modules.purefa_certs.flasharray")
    @patch("plugins.modules.purefa_certs.check_response")
    def test_import_cert_reimport_uses_patch(
        self, mock_check_response, mock_flasharray
    ):
        """Test import_cert with reimport=True uses patch"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "existing-cert",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "intermeadiate_cert": None,
            "key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "passphrase": None,
        }
        mock_array = Mock()
        mock_array.patch_certificates.return_value = Mock(status_code=200)

        import_cert(mock_module, mock_array, reimport=True)

        mock_array.patch_certificates.assert_called_once()
        mock_array.post_certificates.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_certs.flasharray")
    @patch("plugins.modules.purefa_certs.check_response")
    def test_import_cert_new_uses_post(self, mock_check_response, mock_flasharray):
        """Test import_cert with reimport=False uses post"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "new-cert",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "intermeadiate_cert": "-----BEGIN CERTIFICATE-----\nintermediate\n-----END CERTIFICATE-----",
            "key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "passphrase": "secret",
        }
        mock_array = Mock()
        mock_array.post_certificates.return_value = Mock(status_code=200)

        import_cert(mock_module, mock_array, reimport=False)

        mock_array.post_certificates.assert_called_once()
        mock_array.patch_certificates.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_certs.flasharray")
    def test_import_cert_check_mode(self, mock_flasharray):
        """Test import_cert in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-cert",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "intermeadiate_cert": None,
            "key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "passphrase": None,
        }
        mock_array = Mock()

        import_cert(mock_module, mock_array, reimport=False)

        mock_array.post_certificates.assert_not_called()
        mock_array.patch_certificates.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestExportCertFull:
    """Test cases for export_cert function with file operations"""

    @patch("builtins.open", create=True)
    @patch("plugins.modules.purefa_certs.check_response")
    def test_export_cert_success(self, mock_check_response, mock_open):
        """Test export_cert writes certificate to file"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "test-cert", "export_file": "/tmp/cert.pem"}
        mock_array = Mock()
        mock_cert = Mock()
        mock_cert.certificate = (
            "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"
        )
        mock_array.get_certificates.return_value = Mock(
            status_code=200, items=[mock_cert]
        )
        mock_file = Mock()
        mock_open.return_value.__enter__ = Mock(return_value=mock_file)
        mock_open.return_value.__exit__ = Mock(return_value=False)

        export_cert(mock_module, mock_array)

        mock_array.get_certificates.assert_called_once_with(names=["test-cert"])
        mock_file.write.assert_called_once_with(mock_cert.certificate)
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_export_cert_check_mode(self):
        """Test export_cert in check mode doesn't write file"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "test-cert", "export_file": "/tmp/cert.pem"}
        mock_array = Mock()

        export_cert(mock_module, mock_array)

        mock_array.get_certificates.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateCsr:
    """Test cases for create_csr function"""

    @patch("builtins.open", create=True)
    @patch("plugins.modules.purefa_certs.flasharray")
    def test_create_csr_success(self, mock_flasharray, mock_open):
        """Test create_csr generates CSR and writes to file"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-cert",
            "export_file": "/tmp/csr.pem",
            "common_name": "test.example.com",
            "country": "US",
            "email": "test@example.com",
            "locality": "New York",
            "province": "NY",
            "organization": "Test Org",
            "org_unit": "IT",
        }
        mock_array = Mock()
        mock_current_attr = Mock()
        mock_current_attr.common_name = "old.example.com"
        mock_current_attr.country = "UK"
        mock_current_attr.email = "old@example.com"
        mock_current_attr.locality = "London"
        mock_current_attr.state = "England"
        mock_current_attr.organization = "Old Org"
        mock_current_attr.organizational_unit = "Admin"
        mock_array.get_certificates.return_value = Mock(items=[mock_current_attr])
        mock_csr_response = Mock()
        mock_csr_response.certificate_signing_request = [
            "-----BEGIN CSR-----\ntest\n-----END CSR-----"
        ]
        mock_array.post_certificates_certificate_signing_requests.return_value = Mock(
            items=[mock_csr_response]
        )
        mock_file = Mock()
        mock_open.return_value.__enter__ = Mock(return_value=mock_file)
        mock_open.return_value.__exit__ = Mock(return_value=False)

        create_csr(mock_module, mock_array)

        mock_array.get_certificates.assert_called_once()
        mock_array.post_certificates_certificate_signing_requests.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_csr_check_mode(self):
        """Test create_csr in check mode doesn't create CSR"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-cert",
            "export_file": "/tmp/csr.pem",
            "common_name": None,
            "country": None,
            "email": None,
            "locality": None,
            "province": None,
            "organization": None,
            "org_unit": None,
        }
        mock_array = Mock()
        mock_current_attr = Mock()
        mock_array.get_certificates.return_value = Mock(items=[mock_current_attr])

        create_csr(mock_module, mock_array)

        mock_array.post_certificates_certificate_signing_requests.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("builtins.open", create=True)
    @patch("plugins.modules.purefa_certs.flasharray")
    def test_create_csr_with_attribute_errors(self, mock_flasharray, mock_open):
        """Test create_csr handles AttributeError gracefully"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-cert",
            "export_file": "/tmp/csr.pem",
            "common_name": "test.example.com",
            "country": "US",
            "email": "test@example.com",
            "locality": "New York",
            "province": "NY",
            "organization": "Test Org",
            "org_unit": "IT",
        }
        mock_array = Mock()
        # Create mock that raises AttributeError on attribute assignment
        mock_current_attr = Mock(spec=[])  # Empty spec means no attributes allowed
        mock_array.get_certificates.return_value = Mock(items=[mock_current_attr])
        mock_csr_response = Mock()
        mock_csr_response.certificate_signing_request = [
            "-----BEGIN CSR-----\ntest\n-----END CSR-----"
        ]
        mock_array.post_certificates_certificate_signing_requests.return_value = Mock(
            items=[mock_csr_response]
        )
        mock_file = Mock()
        mock_open.return_value.__enter__ = Mock(return_value=mock_file)
        mock_open.return_value.__exit__ = Mock(return_value=False)

        # Should not raise - AttributeError should be caught
        create_csr(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for main() function"""

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.create_cert")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_state_present_create(
        self, mock_ansible_module, mock_get_array, mock_create_cert, mock_loose_version
    ):
        """Test main() creates certificate when state=present and not exists"""
        from plugins.modules.purefa_certs import main

        # Make LooseVersion return comparable values
        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "present",
            "name": "test-cert",
            "common_name": "test.example.com",
            "email": None,
            "country": None,
            "generate": True,
            "key_size": 2048,
            "days": 3650,
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_array.get_certificates.return_value = Mock(status_code=404)  # Not exists
        mock_get_array.return_value = mock_array

        main()

        mock_create_cert.assert_called_once()

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.update_cert")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_state_present_update(
        self, mock_ansible_module, mock_get_array, mock_update_cert, mock_loose_version
    ):
        """Test main() updates certificate when state=present and exists"""
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "present",
            "name": "test-cert",
            "common_name": "test.example.com",
            "email": None,
            "country": None,
            "generate": True,
            "key_size": 2048,
            "days": 3650,
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_array.get_certificates.return_value = Mock(status_code=200)  # Exists
        mock_get_array.return_value = mock_array

        main()

        mock_update_cert.assert_called_once()

    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", False)
    def test_main_no_purestorage_sdk(self, mock_ansible_module, mock_get_array):
        """Test main() fails when purestorage SDK not available"""
        import pytest
        from plugins.modules.purefa_certs import main

        mock_module = Mock()
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", False)
    def test_main_no_pycountry_sdk(self, mock_ansible_module, mock_get_array):
        """Test main() fails when pycountry SDK not available"""
        import pytest
        from plugins.modules.purefa_certs import main

        mock_module = Mock()
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_invalid_email(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails with invalid email format"""
        import pytest
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "present",
            "name": "test-cert",
            "common_name": None,
            "email": "invalid-email",
            "country": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_invalid_country_length(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails with invalid country code length"""
        import pytest
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "present",
            "name": "test-cert",
            "common_name": None,
            "email": None,
            "country": "USA",  # 3 letters, should be 2
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    def test_main_invalid_country_code(self):
        """Test main() fails with invalid ISO country code"""
        import pytest

        # Mock pycountry module in sys.modules
        mock_pycountry = MagicMock()
        mock_pycountry.countries.get.return_value = None  # Invalid code returns None

        with patch.dict(sys.modules, {"pycountry": mock_pycountry}):
            # Reload the module to pick up the mock
            import importlib
            import plugins.modules.purefa_certs as certs_module

            importlib.reload(certs_module)

            with patch.object(
                certs_module,
                "LooseVersion",
                side_effect=lambda x: float(x) if x else 0.0,
            ):
                with patch.object(certs_module, "get_array") as mock_get_array:
                    with patch.object(
                        certs_module, "AnsibleModule"
                    ) as mock_ansible_module:
                        mock_module = Mock()
                        mock_module.check_mode = False
                        mock_module.params = {
                            "state": "present",
                            "name": "test-cert",
                            "common_name": None,
                            "email": None,
                            "country": "XX",  # Invalid ISO code
                        }
                        mock_module.fail_json.side_effect = SystemExit(1)
                        mock_ansible_module.return_value = mock_module
                        mock_array = Mock()
                        mock_array.get_rest_version.return_value = "2.4"
                        mock_get_array.return_value = mock_array

                        with pytest.raises(SystemExit):
                            certs_module.main()

                        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_api_version_too_old(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() fails when API version is too old"""
        import pytest
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "present",
            "name": "test-cert",
            "common_name": None,
            "email": None,
            "country": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "1.0"  # Too old
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called()

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.delete_cert")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_state_absent(
        self, mock_ansible_module, mock_get_array, mock_delete_cert, mock_loose_version
    ):
        """Test main() deletes certificate when state=absent"""
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "absent",
            "name": "test-cert",
            "common_name": None,
            "email": None,
            "country": None,
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_array.get_certificates.return_value = Mock(status_code=200)  # Exists
        mock_get_array.return_value = mock_array

        main()

        mock_delete_cert.assert_called_once()

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.export_cert")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_state_export(
        self, mock_ansible_module, mock_get_array, mock_export_cert, mock_loose_version
    ):
        """Test main() exports certificate when state=export"""
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "export",
            "name": "test-cert",
            "common_name": None,
            "email": None,
            "country": None,
            "export_file": "/tmp/cert.pem",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_array.get_certificates.return_value = Mock(status_code=200)
        mock_get_array.return_value = mock_array

        main()

        mock_export_cert.assert_called_once()

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.create_csr")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_state_sign(
        self, mock_ansible_module, mock_get_array, mock_create_csr, mock_loose_version
    ):
        """Test main() creates CSR when state=sign"""
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "sign",
            "name": "test-cert",
            "common_name": None,
            "email": None,
            "country": None,
            "export_file": "/tmp/csr.pem",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_array.get_certificates.return_value = Mock(status_code=200)
        mock_get_array.return_value = mock_array

        main()

        mock_create_csr.assert_called_once()

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.import_cert")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_state_import_new(
        self, mock_ansible_module, mock_get_array, mock_import_cert, mock_loose_version
    ):
        """Test main() imports new certificate when state=import"""
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "import",
            "name": "test-cert",
            "common_name": None,
            "email": None,
            "country": None,
            "certificate": "-----BEGIN CERTIFICATE-----",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_array.get_certificates.return_value = Mock(status_code=404)  # Not exists
        mock_get_array.return_value = mock_array

        main()

        mock_import_cert.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.import_cert")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_state_import_reimport(
        self, mock_ansible_module, mock_get_array, mock_import_cert, mock_loose_version
    ):
        """Test main() reimports certificate when state=import and exists"""
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "import",
            "name": "test-cert",
            "common_name": None,
            "email": None,
            "country": None,
            "certificate": "-----BEGIN CERTIFICATE-----",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_array.get_certificates.return_value = Mock(status_code=200)  # Exists
        mock_get_array.return_value = mock_array

        main()

        mock_import_cert.assert_called_once_with(mock_module, mock_array, reimport=True)

    @patch("plugins.modules.purefa_certs.LooseVersion")
    @patch("plugins.modules.purefa_certs.get_array")
    @patch("plugins.modules.purefa_certs.AnsibleModule")
    @patch("plugins.modules.purefa_certs.HAS_PURESTORAGE", True)
    @patch("plugins.modules.purefa_certs.HAS_PYCOUNTRY", True)
    def test_main_no_change(
        self, mock_ansible_module, mock_get_array, mock_loose_version
    ):
        """Test main() exits with no change when certificate doesn't exist and state=absent"""
        from plugins.modules.purefa_certs import main

        mock_loose_version.side_effect = lambda x: float(x) if x else 0.0

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "state": "absent",
            "name": "test-cert",
            "common_name": None,
            "email": None,
            "country": None,
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.4"
        mock_array.get_certificates.return_value = Mock(status_code=404)  # Not exists
        mock_get_array.return_value = mock_array

        main()

        mock_module.exit_json.assert_called_once_with(changed=False)
