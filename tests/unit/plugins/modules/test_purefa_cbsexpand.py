# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_cbsexpand module."""

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

from plugins.modules.purefa_cbsexpand import (
    _is_cbs,
    list_capacity,
)


class TestIsCbs:
    """Tests for _is_cbs function"""

    def test_is_cbs_true(self):
        """Test _is_cbs returns True for CBS model"""
        mock_array = Mock()
        mock_hw = Mock()
        mock_hw.model = "CBS-FA-X50"
        mock_array.get_hardware.return_value = Mock(items=[mock_hw])

        result = _is_cbs(mock_array)

        assert result is True

    def test_is_cbs_false(self):
        """Test _is_cbs returns False for non-CBS model"""
        mock_array = Mock()
        mock_hw = Mock()
        mock_hw.model = "FA-X70"
        mock_array.get_hardware.return_value = Mock(items=[mock_hw])

        result = _is_cbs(mock_array)

        assert result is False


class TestListCapacity:
    """Tests for list_capacity function"""

    def test_list_capacity(self):
        """Test list_capacity returns available capacity steps"""
        mock_module = Mock()
        mock_array = Mock()
        mock_step1 = Mock()
        mock_step1.supported_capacity = 1024
        mock_step2 = Mock()
        mock_step2.supported_capacity = 2048
        mock_array.get_arrays_cloud_capacity_supported_steps.return_value = Mock(
            items=[mock_step1, mock_step2]
        )

        list_capacity(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(
            changed=True, available=[1024, 2048]
        )


from unittest.mock import patch


class TestUpdateCapacity:
    """Tests for update_capacity function"""

    @patch("plugins.modules.purefa_cbsexpand.check_response")
    def test_update_capacity_success(self, mock_check_response):
        """Test update_capacity successfully expands CBS capacity"""
        from plugins.modules.purefa_cbsexpand import update_capacity

        mock_module = Mock()
        mock_module.params = {"capacity": 2048}
        mock_array = Mock()
        mock_step1 = Mock()
        mock_step1.supported_capacity = 1024
        mock_step2 = Mock()
        mock_step2.supported_capacity = 2048
        mock_array.get_arrays_cloud_capacity_supported_steps.return_value = Mock(
            items=[mock_step1, mock_step2]
        )
        mock_array.patch_arrays_cloud_capacity.return_value = Mock(status_code=200)

        update_capacity(mock_module, mock_array)

        mock_array.patch_arrays_cloud_capacity.assert_called_once()
        mock_check_response.assert_called()

    def test_update_capacity_invalid_fails(self):
        """Test update_capacity fails when capacity not available"""
        from plugins.modules.purefa_cbsexpand import update_capacity

        mock_module = Mock()
        mock_module.params = {"capacity": 9999}
        mock_array = Mock()
        mock_step1 = Mock()
        mock_step1.supported_capacity = 1024
        mock_step2 = Mock()
        mock_step2.supported_capacity = 2048
        mock_array.get_arrays_cloud_capacity_supported_steps.return_value = Mock(
            items=[mock_step1, mock_step2]
        )

        update_capacity(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()
        assert "not available" in str(mock_module.fail_json.call_args)
