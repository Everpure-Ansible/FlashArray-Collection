# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_smis module."""

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

from plugins.modules.purefa_smis import (
    update_smis,
)


class TestUpdateSmis:
    """Tests for update_smis function"""

    def test_update_smis_no_change(self):
        """Test update_smis when no change needed"""
        mock_module = Mock()
        mock_module.params = {"smis": True, "slp": True}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_smis = Mock()
        mock_smis.slp_enabled = True
        mock_smis.wbem_https_enabled = True
        mock_array.get_smi_s.return_value = Mock(items=[mock_smis])

        update_smis(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_array.patch_smi_s.assert_not_called()

    def test_update_smis_check_mode(self):
        """Test update_smis in check mode when change needed"""
        mock_module = Mock()
        mock_module.params = {"smis": False, "slp": True}
        mock_module.check_mode = True
        mock_array = Mock()
        mock_smis = Mock()
        mock_smis.slp_enabled = True
        mock_smis.wbem_https_enabled = True
        mock_array.get_smi_s.return_value = Mock(items=[mock_smis])

        update_smis(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_smi_s.assert_not_called()
