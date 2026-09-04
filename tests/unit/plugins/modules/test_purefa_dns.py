# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_dns module."""

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
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.error_handlers"
] = MagicMock()

from plugins.modules.purefa_dns import (
    remove,
    delete_dns,
    create_dns,
    _get_source,
    update_multi_dns,
    delete_multi_dns,
    create_multi_dns,
)


class TestRemove:
    """Test cases for remove function"""

    def test_remove_duplicates(self):
        """Test remove function removes duplicates from list"""
        test_list = ["ns1.example.com", "ns2.example.com", "ns1.example.com"]

        result = remove(test_list)

        assert result == ["ns1.example.com", "ns2.example.com"]

    def test_remove_no_duplicates(self):
        """Test remove function with no duplicates"""
        test_list = ["ns1.example.com", "ns2.example.com"]

        result = remove(test_list)

        assert result == ["ns1.example.com", "ns2.example.com"]


class TestDeleteDns:
    """Test cases for delete_dns function"""

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_delete_dns_already_empty(self, mock_get_with_context):
        """Test delete_dns when DNS already empty"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"state": "absent", "context": ""}
        mock_array = Mock()
        # DNS already empty
        mock_dns = Mock()
        mock_dns.domain = ""
        mock_dns.nameservers = [""]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_dns])

        delete_dns(mock_module, mock_array)

        # Note: Module calls exit_json twice when already empty (first at line 166, then at line 178)
        mock_module.exit_json.assert_called_with(changed=False)


class TestCreateDns:
    """Test cases for create_dns function"""

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_create_dns_no_change(self, mock_get_with_context):
        """Test create_dns when config matches"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "domain": "example.com",
            "nameservers": ["ns1.example.com", "ns2.example.com"],
        }
        mock_array = Mock()
        # DNS already matches
        mock_dns = {
            "domain": "example.com",
            "nameservers": ["ns1.example.com", "ns2.example.com"],
        }
        mock_get_with_context.return_value = Mock(items=[mock_dns])

        create_dns(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestGetSource:
    """Test cases for _get_source function"""

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_get_source_exists(self, mock_get_with_context):
        """Test _get_source returns True when source interface exists"""
        mock_module = Mock()
        mock_module.params = {"source": "ct0.eth0"}
        mock_array = Mock()
        mock_get_with_context.return_value.status_code = 200

        result = _get_source(mock_module, mock_array)

        assert result is True

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_get_source_not_exists(self, mock_get_with_context):
        """Test _get_source returns False when source interface doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"source": "ct0.eth0"}
        mock_array = Mock()
        mock_get_with_context.return_value.status_code = 404

        result = _get_source(mock_module, mock_array)

        assert result is False


class TestDeleteDnsExtended:
    """Extended test cases for delete_dns function"""

    @patch("plugins.modules.purefa_dns.check_response")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_delete_dns_success(self, mock_get_with_context, mock_check_response):
        """Test delete_dns successfully deletes DNS config"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"state": "absent", "context": ""}
        mock_array = Mock()
        # DNS has existing config
        mock_dns = Mock()
        mock_dns.domain = "example.com"
        mock_dns.nameservers = ["ns1.example.com"]
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_dns]),  # get_dns
            Mock(status_code=200),  # delete_dns
        ]

        delete_dns(mock_module, mock_array)

        mock_module.exit_json.assert_called_with(changed=True)

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_delete_dns_check_mode(self, mock_get_with_context):
        """Test delete_dns in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"state": "absent", "context": ""}
        mock_array = Mock()
        # DNS has existing config
        mock_dns = Mock()
        mock_dns.domain = "example.com"
        mock_dns.nameservers = ["ns1.example.com"]
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_dns])

        delete_dns(mock_module, mock_array)

        # Should not call delete_dns in check mode
        assert mock_get_with_context.call_count == 1
        mock_module.exit_json.assert_called_with(changed=True)


class TestCreateDnsExtended:
    """Extended test cases for create_dns function"""

    @patch("plugins.modules.purefa_dns.check_response")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_create_dns_success(self, mock_get_with_context, mock_check_response):
        """Test create_dns successfully creates DNS config"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "domain": "example.com",
            "nameservers": ["ns1.example.com", "ns2.example.com"],
        }
        mock_array = Mock()
        # DNS is different - will trigger change
        mock_dns = {
            "domain": "olddomain.com",
            "nameservers": ["old.example.com"],
        }
        mock_get_with_context.side_effect = [
            Mock(items=[mock_dns]),
            Mock(status_code=200),
        ]

        create_dns(mock_module, mock_array)

        assert mock_get_with_context.call_count == 2
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_create_dns_check_mode(self, mock_get_with_context):
        """Test create_dns in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "domain": "example.com",
            "nameservers": ["ns1.example.com", "ns2.example.com"],
        }
        mock_array = Mock()
        # DNS is different - would trigger change
        mock_dns = {
            "domain": "olddomain.com",
            "nameservers": ["old.example.com"],
        }
        mock_get_with_context.return_value = Mock(items=[mock_dns])

        create_dns(mock_module, mock_array)

        assert mock_get_with_context.call_count == 1
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateMultiDns:
    """Test cases for update_multi_dns function"""

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_update_multi_dns_no_changes(self, mock_get_with_context):
        """Test update_multi_dns when no changes needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "file-dns",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "service": None,
            "source": None,
            "context": "",
        }
        mock_array = Mock()
        mock_dns = Mock()
        mock_dns.domain = "example.com"
        mock_dns.nameservers = ["ns1.example.com"]
        mock_dns.services = ["file"]
        mock_dns.source = Mock()
        mock_dns.source.name = ""
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_dns])

        update_multi_dns(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_dns.check_response")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_update_multi_dns_domain_change(
        self, mock_get_with_context, mock_check_response
    ):
        """Test update_multi_dns when domain changes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "file-dns",
            "domain": "newdomain.com",
            "nameservers": None,
            "service": None,
            "source": "",
            "context": "",
        }
        mock_array = Mock()
        mock_dns = Mock()
        mock_dns.domain = "olddomain.com"
        mock_dns.nameservers = ["ns1.example.com"]
        mock_dns.services = ["file"]
        mock_dns.source = Mock()
        mock_dns.source.name = ""
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[mock_dns]),
            Mock(status_code=200),
        ]

        update_multi_dns(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_update_multi_dns_check_mode(self, mock_get_with_context):
        """Test update_multi_dns in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "file-dns",
            "domain": "newdomain.com",
            "nameservers": None,
            "service": None,
            "source": None,
            "context": "",
        }
        mock_array = Mock()
        mock_dns = Mock()
        mock_dns.domain = "olddomain.com"
        mock_dns.nameservers = ["ns1.example.com"]
        mock_dns.services = ["file"]
        mock_dns.source = Mock()
        mock_dns.source.name = ""
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_dns])

        update_multi_dns(mock_module, mock_array)

        # Should not call patch in check mode
        assert mock_get_with_context.call_count == 1
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_update_multi_dns_service_change_fails(self, mock_get_with_context):
        """Test update_multi_dns fails when trying to change service type"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "file-dns",
            "domain": None,
            "nameservers": None,
            "service": "management",  # Trying to change service type
            "source": None,
            "context": "",
        }
        mock_array = Mock()
        mock_dns = Mock()
        mock_dns.domain = "example.com"
        mock_dns.nameservers = ["ns1.example.com"]
        mock_dns.services = ["file"]  # Current service is file
        mock_dns.source = Mock()
        mock_dns.source.name = ""
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_dns])

        with pytest.raises(SystemExit):
            update_multi_dns(mock_module, mock_array)

        mock_module.fail_json.assert_called_once_with(
            msg="Changing service type is not permitted"
        )


class TestDeleteMultiDns:
    """Test cases for delete_multi_dns function"""

    @patch("plugins.modules.purefa_dns.check_response")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_delete_multi_dns_file_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test delete_multi_dns successfully deletes file DNS"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "file-dns", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_multi_dns(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dns.check_response")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_delete_multi_dns_management(
        self, mock_get_with_context, mock_check_response
    ):
        """Test delete_multi_dns clears management DNS (can't delete)"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "management", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_multi_dns(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_delete_multi_dns_check_mode(self, mock_get_with_context):
        """Test delete_multi_dns in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "file-dns", "context": ""}
        mock_array = Mock()

        delete_multi_dns(mock_module, mock_array)

        # Should not call delete in check mode for non-management
        mock_get_with_context.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateMultiDns:
    """Test cases for create_multi_dns function"""

    @patch("plugins.modules.purefa_dns.check_response")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_create_multi_dns_file_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test create_multi_dns successfully creates file DNS"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "file-dns",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "service": "file",
            "source": None,
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        create_multi_dns(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dns.check_response")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_create_multi_dns_file_with_source(
        self, mock_get_with_context, mock_check_response
    ):
        """Test create_multi_dns with source interface"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "file-dns",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "service": "file",
            "source": "ct0.eth0",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        create_multi_dns(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_dns.check_response")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_create_multi_dns_management(
        self, mock_get_with_context, mock_check_response
    ):
        """Test create_multi_dns for management service"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "management",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "service": "management",
            "source": None,
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        create_multi_dns(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_multi_dns_check_mode(self):
        """Test create_multi_dns in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "file-dns",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "service": "file",
            "source": None,
            "context": "",
        }
        mock_array = Mock()

        create_multi_dns(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Tests for main function"""

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    @patch("plugins.modules.purefa_dns.get_with_context")
    @patch("plugins.modules.purefa_dns.update_multi_dns")
    def test_main_multi_dns_update(
        self,
        mock_update_multi_dns,
        mock_get_with_context,
        mock_loose_version,
        mock_get_array,
        mock_ansible_module,
    ):
        """Test main function calls update_multi_dns for existing config"""
        # Configure LooseVersion to behave properly for version comparison
        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "management",
            "service": "management",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "source": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_dns = Mock()
        mock_dns.name = "management"
        mock_get_with_context.return_value = Mock(items=[mock_dns])
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        dns_module.main()

        mock_update_multi_dns.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    @patch("plugins.modules.purefa_dns.get_with_context")
    @patch("plugins.modules.purefa_dns.create_multi_dns")
    def test_main_multi_dns_create(
        self,
        mock_create_multi_dns,
        mock_get_with_context,
        mock_loose_version,
        mock_get_array,
        mock_ansible_module,
    ):
        """Test main function calls create_multi_dns for new config"""
        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "file-dns",
            "service": "file",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "source": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_dns = Mock()
        mock_dns.name = "management"
        mock_get_with_context.return_value = Mock(items=[mock_dns])
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        dns_module.main()

        mock_create_multi_dns.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    @patch("plugins.modules.purefa_dns.get_with_context")
    @patch("plugins.modules.purefa_dns.delete_multi_dns")
    def test_main_multi_dns_delete(
        self,
        mock_delete_multi_dns,
        mock_get_with_context,
        mock_loose_version,
        mock_get_array,
        mock_ansible_module,
    ):
        """Test main function calls delete_multi_dns when state is absent"""
        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "absent",
            "name": "file-dns",
            "service": "file",
            "domain": None,
            "nameservers": None,
            "source": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_dns = Mock()
        mock_dns.name = "file-dns"
        mock_get_with_context.return_value = Mock(items=[mock_dns])
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        dns_module.main()

        mock_delete_multi_dns.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_main_multi_dns_absent_not_exists(
        self,
        mock_get_with_context,
        mock_loose_version,
        mock_get_array,
        mock_ansible_module,
    ):
        """Test main exits unchanged when absent and config doesn't exist"""
        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "absent",
            "name": "file-dns",
            "service": "file",
            "domain": None,
            "nameservers": None,
            "source": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_dns = Mock()
        mock_dns.name = "management"
        mock_get_with_context.return_value = Mock(items=[mock_dns])
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        dns_module.main()

        mock_module.exit_json.assert_called_with(changed=False)

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    @patch("plugins.modules.purefa_dns.get_with_context")
    def test_main_multi_dns_max_configs(
        self,
        mock_get_with_context,
        mock_loose_version,
        mock_get_array,
        mock_ansible_module,
    ):
        """Test main fails when trying to add third DNS config"""
        import pytest

        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "third-dns",
            "service": "file",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "source": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_dns1 = Mock()
        mock_dns1.name = "management"
        mock_dns2 = Mock()
        mock_dns2.name = "file-dns"
        mock_get_with_context.return_value = Mock(items=[mock_dns1, mock_dns2])
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        with pytest.raises(SystemExit):
            dns_module.main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    @patch("plugins.modules.purefa_dns.get_with_context")
    @patch("plugins.modules.purefa_dns._get_source")
    def test_main_multi_dns_invalid_source(
        self,
        mock_get_source,
        mock_get_with_context,
        mock_loose_version,
        mock_get_array,
        mock_ansible_module,
    ):
        """Test main fails when source VIF doesn't exist"""
        import pytest

        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "file-dns",
            "service": "file",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "source": "invalid.eth0",
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_dns = Mock()
        mock_dns.name = "file-dns"
        mock_get_with_context.return_value = Mock(items=[mock_dns])
        mock_get_array.return_value = mock_array
        mock_get_source.return_value = False

        import plugins.modules.purefa_dns as dns_module

        with pytest.raises(SystemExit):
            dns_module.main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    @patch("plugins.modules.purefa_dns.get_with_context")
    @patch("plugins.modules.purefa_dns.update_multi_dns")
    def test_main_multi_dns_override_name_to_management(
        self,
        mock_update_multi_dns,
        mock_get_with_context,
        mock_loose_version,
        mock_get_array,
        mock_ansible_module,
    ):
        """Test main warns and overrides name to management for management service"""
        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "custom-name",
            "service": "management",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "source": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_dns = Mock()
        mock_dns.name = "management"
        mock_get_with_context.return_value = Mock(items=[mock_dns])
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        dns_module.main()

        mock_module.warn.assert_called_once()

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    def test_main_fails_when_context_not_supported(
        self, mock_loose_version, mock_get_array, mock_ansible_module
    ):
        """Test main fails when DNS context is requested on unsupported API."""
        import pytest

        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "management",
            "service": "management",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "source": None,
            "context": "array-b",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        with pytest.raises(SystemExit):
            dns_module.main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    @patch("plugins.modules.purefa_dns.delete_dns")
    def test_main_legacy_dns_delete(
        self, mock_delete_dns, mock_loose_version, mock_get_array, mock_ansible_module
    ):
        """Test main function calls delete_dns for legacy API"""
        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "absent",
            "name": "management",
            "service": "management",
            "domain": None,
            "nameservers": None,
            "source": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.1"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        dns_module.main()

        mock_delete_dns.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    @patch("plugins.modules.purefa_dns.create_dns")
    def test_main_legacy_dns_create(
        self, mock_create_dns, mock_loose_version, mock_get_array, mock_ansible_module
    ):
        """Test main function calls create_dns for legacy API"""
        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "management",
            "service": "management",
            "domain": "example.com",
            "nameservers": ["ns1.example.com"],
            "source": None,
            "context": "",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.1"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        dns_module.main()

        mock_create_dns.assert_called_once_with(mock_module, mock_array)

    @patch("plugins.modules.purefa_dns.AnsibleModule")
    @patch("plugins.modules.purefa_dns.get_array")
    @patch("plugins.modules.purefa_dns.LooseVersion")
    def test_main_legacy_dns_missing_domain(
        self, mock_loose_version, mock_get_array, mock_ansible_module
    ):
        """Test main fails when domain missing for legacy API create"""
        import pytest

        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "state": "present",
            "name": "management",
            "service": "management",
            "domain": None,
            "nameservers": ["ns1.example.com"],
            "source": None,
            "context": "",
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.1"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_dns as dns_module

        with pytest.raises(SystemExit):
            dns_module.main()

        mock_module.fail_json.assert_called_once()
