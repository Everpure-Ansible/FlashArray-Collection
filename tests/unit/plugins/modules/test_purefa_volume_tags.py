# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_volume_tags module."""

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

from plugins.modules.purefa_volume_tags import (
    get_volume,
    get_endpoint,
    create_tag,
    update_tags,
    delete_tags,
)


class TestGetVolume:
    """Test cases for get_volume function"""

    @patch("plugins.modules.purefa_volume_tags.get_with_context")
    def test_get_volume_exists(self, mock_get_with_context):
        """Test get_volume returns volume when it exists"""
        mock_module = Mock()
        mock_module.params = {"name": "test-vol", "context": ""}
        mock_array = Mock()
        mock_vol = Mock()
        mock_vol.name = "test-vol"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_vol])

        result = get_volume(mock_module, mock_array)

        assert result == mock_vol

    @patch("plugins.modules.purefa_volume_tags.get_with_context")
    def test_get_volume_not_exists(self, mock_get_with_context):
        """Test get_volume returns None when volume doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=404, items=[])

        result = get_volume(mock_module, mock_array)

        assert result is None


class TestGetEndpoint:
    """Test cases for get_endpoint function"""

    @patch("plugins.modules.purefa_volume_tags.get_with_context")
    def test_get_endpoint_exists(self, mock_get_with_context):
        """Test get_endpoint returns endpoint when it exists"""
        mock_module = Mock()
        mock_module.params = {"name": "test-endpoint", "context": ""}
        mock_array = Mock()
        mock_vol = Mock()
        mock_vol.name = "test-endpoint"
        mock_vol.subtype = "protocol_endpoint"
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_vol])

        result = get_endpoint(mock_module, mock_array)

        assert result == mock_vol

    @patch("plugins.modules.purefa_volume_tags.get_with_context")
    def test_get_endpoint_not_exists(self, mock_get_with_context):
        """Test get_endpoint returns None when endpoint doesn't exist"""
        mock_module = Mock()
        mock_module.params = {"name": "nonexistent", "context": ""}
        mock_array = Mock()
        mock_vol = Mock()
        # Not a protocol_endpoint - set container_version to None
        mock_vol.protocol_endpoint = Mock()
        mock_vol.protocol_endpoint.container_version = None
        mock_get_with_context.return_value = Mock(status_code=200, items=[mock_vol])

        result = get_endpoint(mock_module, mock_array)

        assert result is None


class TestCreateTag:
    """Tests for create_tag function"""

    def test_create_tag_check_mode(self):
        """Test create_tag in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "context": "",
            "kvp": ["env:prod", "team:devops"],
            "copyable": True,
            "namespace": "default",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        create_tag(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_volume_tags.check_response")
    @patch("plugins.modules.purefa_volume_tags.get_with_context")
    def test_create_tag_success(self, mock_get_with_context, mock_check_response):
        """Test create_tag successfully creates tags"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "context": "",
            "kvp": ["env:prod", "team:devops"],
            "copyable": True,
            "namespace": "default",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        create_tag(mock_module, mock_array)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateTags:
    """Tests for update_tags function"""

    def test_update_tags_no_change(self):
        """Test update_tags when tags already exist"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "context": "",
            "kvp": ["env:prod"],
            "copyable": True,
            "namespace": "default",
        }
        mock_module.check_mode = False
        mock_array = Mock()

        # Current tags already include the new tag
        mock_tag = Mock()
        mock_tag.key = "env"
        mock_tag.value = "prod"
        current_tags = [mock_tag]

        update_tags(mock_module, mock_array, current_tags)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_volume_tags.check_response")
    @patch("plugins.modules.purefa_volume_tags.get_with_context")
    def test_update_tags_with_new_tags(
        self, mock_get_with_context, mock_check_response
    ):
        """Test update_tags when adding new tags"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "context": "",
            "kvp": ["env:prod", "team:devops"],
            "copyable": True,
            "namespace": "default",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_get_with_context.return_value = Mock(status_code=200)

        # Current tags only have one tag
        mock_tag = Mock()
        mock_tag.key = "env"
        mock_tag.value = "prod"
        current_tags = [mock_tag]

        update_tags(mock_module, mock_array, current_tags)

        mock_get_with_context.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_tags_check_mode_with_changes(self):
        """Test update_tags in check mode when changes would be made"""
        mock_module = Mock()
        mock_module.params = {
            "name": "test-vol",
            "context": "",
            "kvp": ["env:prod", "team:devops"],
            "copyable": True,
            "namespace": "default",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        # Current tags are empty
        current_tags = []

        update_tags(mock_module, mock_array, current_tags)

        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteTags:
    """Tests for delete_tags function"""

    @staticmethod
    def _module(**params):
        mock_module = Mock()
        base = {
            "name": "test-vol",
            "context": "",
            "kvp": None,
            "tag": None,
            "namespace": "default",
        }
        base.update(params)
        mock_module.params = base
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        return mock_module

    @staticmethod
    def _tags(*keys):
        out = []
        for key in keys:
            tag = Mock()
            tag.key = key
            out.append(tag)
        return out

    def test_delete_tags_no_match(self):
        """Test delete_tags when tags don't match"""
        mock_module = self._module(kvp=["nonexistent"])

        delete_tags(mock_module, Mock(), self._tags("env"))

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_volume_tags.check_response")
    @patch("plugins.modules.purefa_volume_tags.delete_with_context")
    def test_delete_tags_by_kvp_key(self, mock_delete, mock_check):
        """Test the keys of kvp remove the tags, values ignored

        The old code compared one-element tuples against key strings, so this
        never matched and nothing was ever deleted.
        """
        mock_module = self._module(kvp=["env:whatever"])
        mock_delete.return_value = Mock(status_code=200)

        delete_tags(mock_module, Mock(), self._tags("env", "owner"))

        assert mock_delete.call_args[1]["keys"] == ["env"]
        assert mock_delete.call_args[1]["namespaces"] == ["default"]
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_volume_tags.check_response")
    @patch("plugins.modules.purefa_volume_tags.delete_with_context")
    def test_delete_tags_by_tag_option(self, mock_delete, mock_check):
        """Test the documented tag option removes tags

        It was declared and documented but never read, so it did nothing. With
        kvp left unset the old code also raised TypeError iterating None.
        """
        mock_module = self._module(tag=["env", "owner"])
        mock_delete.return_value = Mock(status_code=200)

        delete_tags(mock_module, Mock(), self._tags("env", "owner", "keep"))

        assert mock_delete.call_args[1]["keys"] == ["env", "owner"]
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_volume_tags.check_response")
    @patch("plugins.modules.purefa_volume_tags.delete_with_context")
    def test_delete_tags_only_removes_what_is_there(self, mock_delete, mock_check):
        """Test a key the volume does not carry is not sent for deletion"""
        mock_module = self._module(tag=["env", "nosuch"])
        mock_delete.return_value = Mock(status_code=200)

        delete_tags(mock_module, Mock(), self._tags("env"))

        assert mock_delete.call_args[1]["keys"] == ["env"]
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_volume_tags.delete_with_context")
    def test_delete_tags_tag_wins_over_kvp(self, mock_delete):
        """Test tag takes precedence over the keys in kvp"""
        mock_module = self._module(tag=["owner"], kvp=["env:x"])
        mock_delete.return_value = Mock(status_code=200)

        with patch("plugins.modules.purefa_volume_tags.check_response"):
            delete_tags(mock_module, Mock(), self._tags("env", "owner"))

        assert mock_delete.call_args[1]["keys"] == ["owner"]

    @patch("plugins.modules.purefa_volume_tags.delete_with_context")
    def test_delete_tags_check_mode(self, mock_delete):
        """Test check mode predicts the removal without making it"""
        mock_module = self._module(tag=["env"])
        mock_module.check_mode = True

        delete_tags(mock_module, Mock(), self._tags("env"))

        mock_delete.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_volume_tags.delete_with_context")
    def test_delete_tags_nothing_requested_fails(self, mock_delete):
        """Test state=absent with neither option says so"""
        import pytest

        mock_module = self._module()

        with pytest.raises(SystemExit):
            delete_tags(mock_module, Mock(), self._tags("env"))

        assert "tag or kvp is required" in mock_module.fail_json.call_args[1]["msg"]
        mock_delete.assert_not_called()
