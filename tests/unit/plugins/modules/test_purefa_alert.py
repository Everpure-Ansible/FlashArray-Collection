# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_alert module."""

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

from plugins.modules.purefa_alert import (
    create_alert,
    delete_alert,
    update_alert,
)


class TestCreateAlert:
    """Tests for create_alert function"""

    def test_create_alert_check_mode(self):
        """Test create_alert in check mode"""
        mock_module = Mock()
        mock_module.params = {"address": "test@example.com", "enabled": True}
        mock_module.check_mode = True
        mock_array = Mock()

        create_alert(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.post_alert_watchers.assert_not_called()


class TestDeleteAlert:
    """Tests for delete_alert function"""

    def test_delete_alert_check_mode(self):
        """Test delete_alert in check mode"""
        mock_module = Mock()
        mock_module.params = {"address": "test@example.com"}
        mock_module.check_mode = True
        mock_array = Mock()

        delete_alert(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.delete_alert_watchers.assert_not_called()

    def test_delete_alert_builtin_fails(self):
        """Test delete_alert fails for built-in address"""
        mock_module = Mock()
        mock_module.params = {"address": "flasharray-alerts@everpuredata.com"}
        mock_module.check_mode = False
        mock_array = Mock()

        delete_alert(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestUpdateAlert:
    """Tests for update_alert function"""

    def test_update_alert_no_change(self):
        """Test update_alert when no change needed"""
        mock_module = Mock()
        mock_module.params = {"address": "test@example.com", "enabled": True}
        mock_module.check_mode = False
        mock_array = Mock()

        update_alert(mock_module, mock_array, enabled=True)

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_array.patch_alert_watchers.assert_not_called()

    def test_update_alert_check_mode(self):
        """Test update_alert in check mode when change needed"""
        mock_module = Mock()
        mock_module.params = {"address": "test@example.com", "enabled": False}
        mock_module.check_mode = True
        mock_array = Mock()

        update_alert(mock_module, mock_array, enabled=True)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_alert_watchers.assert_not_called()


from unittest.mock import patch


class TestCreateAlertSuccess:
    """Test cases for create_alert success paths"""

    @patch("plugins.modules.purefa_alert.check_response")
    def test_create_alert_success(self, mock_check_response):
        """Test create_alert successfully creates alert"""
        mock_module = Mock()
        mock_module.params = {"address": "new@example.com", "enabled": True}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.post_alert_watchers.return_value = Mock(status_code=200)

        create_alert(mock_module, mock_array)

        mock_array.post_alert_watchers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteAlertSuccess:
    """Test cases for delete_alert success paths"""

    @patch("plugins.modules.purefa_alert.check_response")
    def test_delete_alert_success(self, mock_check_response):
        """Test delete_alert successfully deletes alert"""
        mock_module = Mock()
        mock_module.params = {"address": "remove@example.com"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.delete_alert_watchers.return_value = Mock(status_code=200)

        delete_alert(mock_module, mock_array)

        mock_array.delete_alert_watchers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateAlertSuccess:
    """Test cases for update_alert success paths"""

    @patch("plugins.modules.purefa_alert.check_response")
    def test_update_alert_success(self, mock_check_response):
        """Test update_alert successfully updates alert"""
        mock_module = Mock()
        mock_module.params = {"address": "test@example.com", "enabled": False}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_alert_watchers.return_value = Mock(status_code=200)

        update_alert(mock_module, mock_array, enabled=True)

        mock_array.patch_alert_watchers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestTestAlert:
    """Test cases for test_alert function"""

    def test_test_alert_success(self):
        """Test test_alert successfully tests alert watchers"""
        from plugins.modules.purefa_alert import test_alert

        mock_module = Mock()
        mock_module.params = {"address": "test@example.com"}
        mock_array = Mock()

        # Create mock response items
        mock_component = Mock()
        mock_component.enabled = True
        mock_component.success = True
        mock_component.component_address = "10.0.0.1"
        mock_component.component_name = "controller"
        mock_component.description = "Test description"
        mock_component.destination = "test@example.com"
        mock_component.result_details = "Test passed"
        mock_component.test_type = "email"
        mock_component.resource = Mock(name="array1")

        mock_array.get_alert_watchers_test.return_value = Mock(items=[mock_component])

        test_alert(mock_module, mock_array)

        mock_array.get_alert_watchers_test.assert_called_once_with(
            names=["test@example.com"]
        )
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args
        assert call_args[1]["changed"] is True
        assert "test_response" in call_args[1]

    def test_test_alert_disabled_component(self):
        """Test test_alert with disabled component"""
        from plugins.modules.purefa_alert import test_alert

        mock_module = Mock()
        mock_module.params = {"address": "test@example.com"}
        mock_array = Mock()

        mock_component = Mock()
        mock_component.enabled = False
        mock_component.success = False
        mock_component.component_address = "10.0.0.1"
        mock_component.component_name = "controller"
        mock_component.description = "Test description"
        mock_component.destination = "test@example.com"
        mock_component.test_type = "email"
        mock_component.resource = Mock(name="array1")
        # result_details not present
        del mock_component.result_details

        mock_array.get_alert_watchers_test.return_value = Mock(items=[mock_component])

        test_alert(mock_module, mock_array)

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args
        test_response = call_args[1]["test_response"]
        assert test_response[0]["enabled"] == "false"
        assert test_response[0]["success"] == "false"
