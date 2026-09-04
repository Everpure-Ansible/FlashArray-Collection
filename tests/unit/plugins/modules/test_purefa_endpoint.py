# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_endpoint module."""

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

from plugins.modules.purefa_endpoint import (
    get_volume,
    delete_endpoint,
    eradicate_endpoint,
    recover_endpoint,
    rename_endpoint,
    _volfact,
)


class TestGetVolume:
    """Test cases for get_volume function"""

    @patch("plugins.modules.purefa_endpoint.get_with_context")
    def test_get_volume_exists(self, mock_get_with_context):
        """Test get_volume returns volume when it exists"""
        mock_module = Mock()
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_vol = Mock()
        mock_vol.name = "vol1"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_vol])

        result = get_volume(mock_module, "vol1", mock_array)

        assert result == mock_vol

    @patch("plugins.modules.purefa_endpoint.get_with_context")
    def test_get_volume_not_exists(self, mock_get_with_context):
        """Test get_volume returns None when volume doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404)

        result = get_volume(mock_module, "nonexistent", mock_array)

        assert result is None


class TestDeleteEndpoint:
    """Test cases for delete_endpoint function"""

    def test_delete_endpoint_check_mode(self):
        """Test delete_endpoint in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-endpoint",
            "eradicate": False,
            "hgroup": None,
            "host": None,
            "pgroup": None,
        }
        mock_array = Mock()

        delete_endpoint(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True, volume={})


class TestEradicateEndpoint:
    """Test cases for eradicate_endpoint function"""

    def test_eradicate_endpoint_check_mode(self):
        """Test eradicate_endpoint in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-endpoint"}
        mock_array = Mock()

        eradicate_endpoint(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True, volume=[])


class TestRecoverEndpoint:
    """Test cases for recover_endpoint function"""

    def test_recover_endpoint_check_mode(self):
        """Test recover_endpoint in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"name": "deleted-endpoint", "pgroup": None}
        mock_array = Mock()

        recover_endpoint(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True, volume={})


class TestVolfact:
    """Test cases for _volfact function"""

    def test_volfact_check_mode_returns_empty(self):
        """Test _volfact returns empty dict in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_array = Mock()

        result = _volfact(mock_module, mock_array, "test-vol")

        assert result == {}


class TestRenameEndpoint:
    """Test cases for rename_endpoint function"""

    @patch("plugins.modules.purefa_endpoint.get_volume")
    def test_rename_endpoint_check_mode(self, mock_get_volume):
        """Test rename_endpoint in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "test-endpoint",
            "rename": "new-name",
            "context": "",
        }
        mock_array = Mock()
        # Target does not exist
        mock_get_volume.return_value = None

        rename_endpoint(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True, volume={})

    @patch("plugins.modules.purefa_endpoint.get_volume")
    def test_rename_endpoint_target_exists(self, mock_get_volume):
        """Test rename_endpoint fails when target exists"""
        import pytest

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_module.params = {
            "name": "test-endpoint",
            "rename": "existing-name",
            "context": "",
        }
        mock_array = Mock()
        # Target exists
        mock_get_volume.return_value = Mock()

        with pytest.raises(SystemExit):
            rename_endpoint(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()


class TestDeleteEndpointSuccess:
    """Test cases for delete_endpoint success paths"""

    @patch("plugins.modules.purefa_endpoint._volfact")
    @patch("plugins.modules.purefa_endpoint.patch_with_context")
    @patch("plugins.modules.purefa_endpoint.check_response")
    def test_delete_endpoint_success(
        self, mock_check_response, mock_patch_with_context, mock_volfact
    ):
        """Test delete_endpoint successfully deletes"""
        mock_volfact.return_value = {}
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "test-endpoint",
            "eradicate": False,
            "hgroup": None,
            "host": None,
            "pgroup": None,
            "context": "",
        }
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        delete_endpoint(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True, volume={})

    @patch("plugins.modules.purefa_endpoint._volfact")
    @patch("plugins.modules.purefa_endpoint.delete_with_context")
    @patch("plugins.modules.purefa_endpoint.patch_with_context")
    @patch("plugins.modules.purefa_endpoint.check_response")
    def test_delete_endpoint_with_eradicate(
        self,
        mock_check_response,
        mock_patch_with_context,
        mock_delete_with_context,
        mock_volfact,
    ):
        """Test delete_endpoint with eradicate=True"""
        import pytest

        mock_volfact.return_value = {}
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_module.params = {
            "name": "test-endpoint",
            "eradicate": True,
            "hgroup": None,
            "host": None,
            "pgroup": None,
            "context": "",
        }
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)
        mock_delete_with_context.return_value = Mock(status_code=200)

        with pytest.raises(SystemExit):
            delete_endpoint(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_with(changed=True, volume=[])


class TestEradicateEndpointSuccess:
    """Test cases for eradicate_endpoint success paths"""

    @patch("plugins.modules.purefa_endpoint.delete_with_context")
    @patch("plugins.modules.purefa_endpoint.check_response")
    def test_eradicate_endpoint_success(
        self, mock_check_response, mock_delete_with_context
    ):
        """Test eradicate_endpoint successfully eradicates"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "deleted-endpoint",
            "context": "",
            "eradicate": True,
        }
        mock_array = Mock()
        mock_delete_with_context.return_value = Mock(status_code=200)

        eradicate_endpoint(mock_module, mock_array)

        mock_delete_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True, volume=[])


class TestRecoverEndpointSuccess:
    """Test cases for recover_endpoint success paths"""

    @patch("plugins.modules.purefa_endpoint._volfact")
    @patch("plugins.modules.purefa_endpoint.patch_with_context")
    @patch("plugins.modules.purefa_endpoint.check_response")
    def test_recover_endpoint_success(
        self, mock_check_response, mock_patch_with_context, mock_volfact
    ):
        """Test recover_endpoint successfully recovers"""
        mock_volfact.return_value = {"name": "recovered-endpoint"}
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"name": "deleted-endpoint", "pgroup": None, "context": ""}
        mock_array = Mock()
        mock_patch_with_context.return_value = Mock(status_code=200)

        recover_endpoint(mock_module, mock_array)

        mock_patch_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once()


class TestCreateEndpoint:
    """Test cases for create_endpoint function"""

    @patch("plugins.modules.purefa_endpoint.get_with_context")
    def test_create_endpoint_check_mode(self, mock_get_with_context):
        """Test create_endpoint in check mode"""
        from plugins.modules.purefa_endpoint import create_endpoint

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "name": "vg/new-endpoint",
            "context": "",
            "container_version": 1,
            "host": None,
            "hgroup": None,
        }
        mock_array = Mock()
        # Volume group exists
        mock_get_with_context.return_value = Mock(status_code=200)

        create_endpoint(mock_module, mock_array)

        mock_module.exit_json.assert_called_once()
