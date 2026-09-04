# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_vnc module."""

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

from plugins.modules.purefa_vnc import (
    disable_vnc,
    enable_vnc,
)


class TestDisableVnc:
    """Tests for disable_vnc function"""

    def test_disable_vnc_already_disabled(self):
        """Test disable_vnc when VNC is already disabled"""
        mock_module = Mock()
        mock_module.params = {"name": "app1"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_app = Mock()
        mock_app.vnc_enabled = False

        disable_vnc(mock_module, mock_array, mock_app)

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_array.patch_apps.assert_not_called()

    def test_disable_vnc_check_mode(self):
        """Test disable_vnc in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "app1"}
        mock_module.check_mode = True
        mock_array = Mock()
        mock_app = Mock()
        mock_app.vnc_enabled = True

        disable_vnc(mock_module, mock_array, mock_app)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_apps.assert_not_called()

    @patch("plugins.modules.purefa_vnc.check_response")
    def test_disable_vnc_success(self, mock_check_response):
        """Test disable_vnc successfully"""
        mock_module = Mock()
        mock_module.params = {"name": "app1"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_apps.return_value = Mock(status_code=200)
        mock_app = Mock()
        mock_app.vnc_enabled = True

        disable_vnc(mock_module, mock_array, mock_app)

        mock_array.patch_apps.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestEnableVnc:
    """Tests for enable_vnc function"""

    def test_enable_vnc_already_enabled(self):
        """Test enable_vnc when VNC is already enabled"""
        mock_module = Mock()
        mock_module.params = {"name": "app1"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_app = Mock()
        mock_app.vnc_enabled = True

        enable_vnc(mock_module, mock_array, mock_app)

        mock_module.exit_json.assert_called_once_with(changed=False, vnc=[])
        mock_array.patch_apps.assert_not_called()

    def test_enable_vnc_check_mode(self):
        """Test enable_vnc in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "app1"}
        mock_module.check_mode = True
        mock_array = Mock()
        mock_app = Mock()
        mock_app.vnc_enabled = False

        enable_vnc(mock_module, mock_array, mock_app)

        mock_module.exit_json.assert_called_once_with(changed=True, vnc=[])
        mock_array.patch_apps.assert_not_called()

    def test_enable_vnc_success(self):
        """Test enable_vnc successfully"""
        mock_module = Mock()
        mock_module.params = {"name": "app1"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_vnc_node = Mock()
        mock_vnc_node.status = "running"
        mock_vnc_node.index = 0
        mock_vnc_node.version = "1.0.0"
        mock_vnc_node.vnc = "192.168.1.100:5900"
        mock_array.patch_apps.return_value = Mock(status_code=200)
        mock_array.get_apps_nodes.return_value = Mock(items=[mock_vnc_node])
        mock_app = Mock()
        mock_app.vnc_enabled = False

        enable_vnc(mock_module, mock_array, mock_app)

        mock_array.patch_apps.assert_called_once()
        assert mock_module.exit_json.call_count == 1
        call_args = mock_module.exit_json.call_args
        assert call_args[1]["changed"] is True
        assert call_args[1]["vnc"]["status"] == "running"

    def test_enable_vnc_failure(self):
        """Test enable_vnc when patch fails"""
        mock_module = Mock()
        mock_module.params = {"name": "app1"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_error = Mock()
        mock_error.message = "Failed to enable VNC"
        mock_array.patch_apps.return_value = Mock(status_code=400, errors=[mock_error])
        mock_app = Mock()
        mock_app.vnc_enabled = False

        enable_vnc(mock_module, mock_array, mock_app)

        mock_module.fail_json.assert_called_once()
