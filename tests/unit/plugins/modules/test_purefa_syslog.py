# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_syslog module."""

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

from plugins.modules.purefa_syslog import (
    delete_syslog,
    add_syslog,
    test_syslog as syslog_test,
    update_syslog,
)


class TestDeleteSyslog:
    """Tests for delete_syslog function"""

    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_delete_syslog_check_mode(self, mock_get_with_context):
        """Test delete_syslog in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "syslog1", "context": ""}
        mock_module.check_mode = True
        mock_array = Mock()

        delete_syslog(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_get_with_context.assert_not_called()

    @patch("plugins.modules.purefa_syslog.check_response")
    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_delete_syslog_success(self, mock_get_with_context, mock_check_response):
        """Test delete_syslog successfully deletes"""
        mock_module = Mock()
        mock_module.params = {"name": "syslog1", "context": ""}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_syslog(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_with(changed=True)


class TestAddSyslog:
    """Tests for add_syslog function"""

    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_add_syslog_check_mode(self, mock_get_with_context):
        """Test add_syslog in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "syslog1",
            "context": "",
            "protocol": "tcp",
            "address": "syslog.example.com",
            "port": "514",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        add_syslog(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_get_with_context.assert_not_called()

    @patch("plugins.modules.purefa_syslog.check_response")
    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_add_syslog_success(self, mock_get_with_context, mock_check_response):
        """Test add_syslog successfully adds"""
        mock_module = Mock()
        mock_module.params = {
            "name": "syslog1",
            "context": "",
            "protocol": "tcp",
            "address": "syslog.example.com",
            "port": "514",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        add_syslog(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_with(changed=True)


class TestSyslogTest:
    """Tests for test_syslog function"""

    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_syslog_test_success(self, mock_get_with_context):
        """Test syslog_test returns test results"""
        mock_module = Mock()
        mock_module.params = {"name": "syslog1", "context": ""}
        mock_array = Mock()

        # Create mock test response component
        mock_component = Mock()
        mock_component.enabled = True
        mock_component.success = True
        mock_component.component_address = "192.168.1.100"
        mock_component.component_name = "syslog1"
        mock_component.description = "Test description"
        mock_component.destination = "syslog.example.com"
        mock_component.result_details = "Success"
        mock_component.test_type = "tcp"
        mock_component.resource = Mock()
        mock_component.resource.name = "test-resource"

        mock_get_with_context.return_value.items = [mock_component]

        syslog_test(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args
        assert call_args[1]["changed"] is True
        assert len(call_args[1]["test_response"]) == 1
        assert call_args[1]["test_response"][0]["enabled"] == "true"
        assert call_args[1]["test_response"][0]["success"] == "true"

    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_syslog_test_disabled_and_failed(self, mock_get_with_context):
        """Test syslog_test with disabled and failed component"""
        mock_module = Mock()
        mock_module.params = {"name": "syslog1", "context": ""}
        mock_array = Mock()

        mock_component = Mock()
        mock_component.enabled = False
        mock_component.success = False
        mock_component.component_address = "192.168.1.100"
        mock_component.component_name = "syslog1"
        mock_component.description = "Test description"
        mock_component.destination = "syslog.example.com"
        mock_component.test_type = "tcp"
        mock_component.resource = Mock()
        mock_component.resource.name = "test-resource"
        del mock_component.result_details

        mock_get_with_context.return_value.items = [mock_component]

        syslog_test(mock_module, mock_array)

        call_args = mock_module.exit_json.call_args
        assert call_args[1]["test_response"][0]["enabled"] == "false"
        assert call_args[1]["test_response"][0]["success"] == "false"


class TestUpdateSyslog:
    """Tests for update_syslog function"""

    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_update_syslog_no_change(self, mock_get_with_context):
        """Test update_syslog when URI already matches"""
        mock_module = Mock()
        mock_module.params = {
            "name": "syslog1",
            "context": "",
            "protocol": "tcp",
            "address": "syslog.example.com",
            "port": "514",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Current config matches
        mock_config = Mock()
        mock_config.uri = "tcp://syslog.example.com:514"
        mock_get_with_context.return_value.items = [mock_config]

        update_syslog(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)
        # Should only call get_syslog_servers, not patch
        assert mock_get_with_context.call_count == 1

    @patch("plugins.modules.purefa_syslog.check_response")
    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_update_syslog_with_changes(
        self, mock_get_with_context, mock_check_response
    ):
        """Test update_syslog when URI changes"""
        mock_module = Mock()
        mock_module.params = {
            "name": "syslog1",
            "context": "",
            "protocol": "tcp",
            "address": "new-syslog.example.com",
            "port": "514",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Current config is different
        mock_config = Mock()
        mock_config.uri = "tcp://old-syslog.example.com:514"
        mock_get_with_context.return_value.items = [mock_config]

        update_syslog(mock_module, mock_array)

        # Should call both get and patch
        assert mock_get_with_context.call_count == 2
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_update_syslog_check_mode_with_changes(self, mock_get_with_context):
        """Test update_syslog in check mode when URI would change"""
        mock_module = Mock()
        mock_module.params = {
            "name": "syslog1",
            "context": "",
            "protocol": "tcp",
            "address": "new-syslog.example.com",
            "port": "514",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        # Current config is different
        mock_config = Mock()
        mock_config.uri = "tcp://old-syslog.example.com:514"
        mock_get_with_context.return_value.items = [mock_config]

        update_syslog(mock_module, mock_array)

        # Should only call get, not patch (check mode)
        assert mock_get_with_context.call_count == 1
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_syslog.get_with_context")
    def test_update_syslog_no_port(self, mock_get_with_context):
        """Test update_syslog without port specified"""
        mock_module = Mock()
        mock_module.params = {
            "name": "syslog1",
            "context": "",
            "protocol": "udp",
            "address": "syslog.example.com",
            "port": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Current config matches (no port)
        mock_config = Mock()
        mock_config.uri = "udp://syslog.example.com"
        mock_get_with_context.return_value.items = [mock_config]

        update_syslog(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)
