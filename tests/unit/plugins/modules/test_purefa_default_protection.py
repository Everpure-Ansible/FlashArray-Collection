# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_default_protection module."""

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

from plugins.modules.purefa_default_protection import (
    _get_pod,
    _get_pg,
    delete_default,
    create_default,
    update_default,
)


class TestGetPod:
    """Test cases for _get_pod function"""

    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_get_pod_exists(self, mock_get_with_context):
        """Test _get_pod returns pod when it exists"""
        mock_module = Mock()
        mock_module.params = {"pod": "test-pod", "context": ""}
        mock_array = Mock()
        mock_pod = Mock()
        mock_pod.name = "test-pod"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pod])

        result = _get_pod(mock_module, mock_array)

        assert result == mock_pod

    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_get_pod_not_exists(self, mock_get_with_context):
        """Test _get_pod returns None when pod doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"pod": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404, items=[])

        result = _get_pod(mock_module, mock_array)

        assert result is None


class TestGetPg:
    """Test cases for _get_pg function"""

    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_get_pg_exists(self, mock_get_with_context):
        """Test _get_pg returns protection group when it exists"""
        mock_module = Mock()
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_pg = Mock()
        mock_pg.name = "test-pg"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_pg])

        result = _get_pg(mock_module, mock_array, "test-pg")

        assert result == mock_pg

    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_get_pg_not_exists(self, mock_get_with_context):
        """Test _get_pg returns None when protection group doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404, items=[])

        result = _get_pg(mock_module, mock_array, "nonexistent")

        assert result is None


class TestDeleteDefault:
    """Test cases for delete_default function"""

    def test_delete_default_check_mode(self):
        """Test delete_default in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"scope": "array", "name": ["pg1"]}
        mock_array = Mock()

        delete_default(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_default_protection.check_response")
    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_delete_default_array_scope_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test delete_default with array scope"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"scope": "array", "name": ["pg1"], "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_default(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_default_protection.check_response")
    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_delete_default_pod_scope_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test delete_default with pod scope"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "scope": "pod",
            "name": ["pg1"],
            "pod": "test-pod",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_default(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateDefault:
    """Test cases for create_default function"""

    def test_create_default_check_mode(self):
        """Test create_default in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"scope": "array", "name": ["pg1"]}
        mock_array = Mock()

        create_default(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_default_protection.check_response")
    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_create_default_array_scope_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test create_default with array scope"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"scope": "array", "name": ["pg1"], "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        create_default(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_default_protection.check_response")
    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_create_default_pod_scope_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test create_default with pod scope"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "scope": "pod",
            "name": ["pg1"],
            "pod": "test-pod",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        create_default(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateDefault:
    """Test cases for update_default function"""

    def test_update_default_no_change(self):
        """Test update_default when no change needed"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "scope": "array",
            "name": ["pg1"],
            "state": "present",
        }
        mock_array = Mock()
        # Current defaults already match
        mock_default = Mock()
        mock_default.name = "pg1"
        current_default = [mock_default]

        update_default(mock_module, mock_array, current_default)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_default_protection.check_response")
    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_update_default_add_pgroup_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test update_default adding new protection group"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "scope": "array",
            "name": ["pg1", "pg2"],
            "state": "present",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        # Current has only pg1
        mock_default = Mock()
        mock_default.name = "pg1"
        current_default = [mock_default]

        update_default(mock_module, mock_array, current_default)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_default_protection.check_response")
    @patch("plugins.modules.purefa_default_protection.get_with_context")
    def test_update_default_remove_pgroup_success(
        self, mock_get_with_context, mock_check_response
    ):
        """Test update_default removing protection group"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "scope": "array",
            "name": ["pg1"],
            "state": "absent",
            "context": "",
        }
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)
        # Current has pg1 and pg2
        mock_default1 = Mock()
        mock_default1.name = "pg1"
        mock_default2 = Mock()
        mock_default2.name = "pg2"
        current_default = [mock_default1, mock_default2]

        update_default(mock_module, mock_array, current_default)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_default_check_mode(self):
        """Test update_default in check mode when change needed"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "scope": "array",
            "name": ["pg1", "pg2"],
            "state": "present",
        }
        mock_array = Mock()
        # Current has only pg1
        mock_default = Mock()
        mock_default.name = "pg1"
        current_default = [mock_default]

        update_default(mock_module, mock_array, current_default)

        mock_module.exit_json.assert_called_once_with(changed=True)
