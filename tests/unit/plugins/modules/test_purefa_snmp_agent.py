# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_snmp_agent module."""

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

from plugins.modules.purefa_snmp_agent import (
    update_agent,
)


class TestUpdateAgent:
    """Tests for update_agent function"""

    def test_update_agent_v2c_check_mode(self):
        """Test update_agent with v2c in check mode"""
        mock_module = Mock()
        mock_module.params = {"version": "v2c", "community": "public"}
        mock_module.check_mode = True
        mock_array = Mock()

        update_agent(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_snmp_agents.assert_not_called()

    @patch("plugins.modules.purefa_snmp_agent.check_response")
    def test_update_agent_v2c_success(self, mock_check_response):
        """Test update_agent with v2c successfully"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v2c",
            "community": "public",
            "state": "present",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_snmp_agents.return_value = Mock(status_code=200)

        update_agent(mock_module, mock_array)

        mock_array.patch_snmp_agents.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snmp_agent.check_response")
    def test_update_agent_v2c_delete(self, mock_check_response):
        """Test update_agent with v2c delete state"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v2c",
            "community": "public",
            "state": "delete",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_snmp_agents.return_value = Mock(status_code=200)

        update_agent(mock_module, mock_array)

        mock_array.patch_snmp_agents.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_agent_v3_check_mode(self):
        """Test update_agent with v3 in check mode"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v3",
            "user": "snmpuser",
            "auth_protocol": "SHA",
            "auth_passphrase": "authpass",
            "privacy_protocol": "AES",
            "privacy_passphrase": "privpass",
            "state": "present",
        }
        mock_module.check_mode = True
        mock_array = Mock()

        update_agent(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_snmp_agents.assert_not_called()

    @patch("plugins.modules.purefa_snmp_agent.check_response")
    def test_update_agent_v3_auth_only(self, mock_check_response):
        """Test update_agent with v3 auth protocol only"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v3",
            "user": "snmpuser",
            "auth_protocol": "SHA",
            "auth_passphrase": "authpass",
            "privacy_protocol": None,
            "privacy_passphrase": None,
            "state": "present",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_snmp_agents.return_value = Mock(status_code=200)

        update_agent(mock_module, mock_array)

        mock_array.patch_snmp_agents.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snmp_agent.check_response")
    def test_update_agent_v3_full(self, mock_check_response):
        """Test update_agent with v3 full auth and privacy"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v3",
            "user": "snmpuser",
            "auth_protocol": "SHA",
            "auth_passphrase": "authpass",
            "privacy_protocol": "AES",
            "privacy_passphrase": "privpass",
            "state": "present",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_snmp_agents.return_value = Mock(status_code=200)

        update_agent(mock_module, mock_array)

        mock_array.patch_snmp_agents.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snmp_agent.check_response")
    def test_update_agent_v3_privacy_only(self, mock_check_response):
        """Test update_agent with v3 privacy protocol only"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v3",
            "user": "snmpuser",
            "auth_protocol": None,
            "auth_passphrase": None,
            "privacy_protocol": "AES",
            "privacy_passphrase": "privpass",
            "state": "present",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_snmp_agents.return_value = Mock(status_code=200)

        update_agent(mock_module, mock_array)

        mock_array.patch_snmp_agents.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snmp_agent.check_response")
    def test_update_agent_v3_user_only(self, mock_check_response):
        """Test update_agent with v3 user only (no auth or privacy)"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v3",
            "user": "snmpuser",
            "auth_protocol": None,
            "auth_passphrase": None,
            "privacy_protocol": None,
            "privacy_passphrase": None,
            "state": "present",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_snmp_agents.return_value = Mock(status_code=200)

        update_agent(mock_module, mock_array)

        mock_array.patch_snmp_agents.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snmp_agent.check_response")
    def test_update_agent_v3_delete(self, mock_check_response):
        """Test update_agent with v3 delete state"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v3",
            "user": "snmpuser",
            "auth_protocol": None,
            "auth_passphrase": None,
            "privacy_protocol": None,
            "privacy_passphrase": None,
            "state": "delete",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_snmp_agents.return_value = Mock(status_code=200)

        update_agent(mock_module, mock_array)

        mock_array.patch_snmp_agents.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_snmp_agent.check_response")
    def test_update_agent_v2c_no_community(self, mock_check_response):
        """Test update_agent with v2c when no community is set"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v2c",
            "community": None,
            "state": "present",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_snmp_agents.return_value = Mock(status_code=200)

        update_agent(mock_module, mock_array)

        mock_array.patch_snmp_agents.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Tests for main function"""

    @patch("plugins.modules.purefa_snmp_agent.AnsibleModule")
    @patch("plugins.modules.purefa_snmp_agent.get_array")
    @patch("plugins.modules.purefa_snmp_agent.update_agent")
    def test_main_v2c_success(
        self, mock_update_agent, mock_get_array, mock_ansible_module
    ):
        """Test main function with v2c version"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v2c",
            "community": "public",
            "state": "present",
            "user": None,
            "auth_passphrase": None,
            "auth_protocol": None,
            "privacy_passphrase": None,
            "privacy_protocol": None,
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_snmp_agent as agent_module

        original_has = agent_module.HAS_PURESTORAGE
        agent_module.HAS_PURESTORAGE = True

        try:
            agent_module.main()
            mock_update_agent.assert_called_once_with(mock_module, mock_array)
        finally:
            agent_module.HAS_PURESTORAGE = original_has

    @patch("plugins.modules.purefa_snmp_agent.AnsibleModule")
    @patch("plugins.modules.purefa_snmp_agent.get_array")
    @patch("plugins.modules.purefa_snmp_agent.update_agent")
    def test_main_v3_success(
        self, mock_update_agent, mock_get_array, mock_ansible_module
    ):
        """Test main function with v3 version and valid user"""
        mock_module = Mock()
        mock_module.params = {
            "version": "v3",
            "community": None,
            "state": "present",
            "user": "snmpuser",
            "auth_passphrase": "authpassphrase",
            "auth_protocol": "SHA",
            "privacy_passphrase": "privpassphrase",
            "privacy_protocol": "AES",
        }
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_snmp_agent as agent_module

        original_has = agent_module.HAS_PURESTORAGE
        agent_module.HAS_PURESTORAGE = True

        try:
            agent_module.main()
            mock_update_agent.assert_called_once_with(mock_module, mock_array)
        finally:
            agent_module.HAS_PURESTORAGE = original_has

    @patch("plugins.modules.purefa_snmp_agent.AnsibleModule")
    @patch("plugins.modules.purefa_snmp_agent.get_array")
    def test_main_v3_missing_user(self, mock_get_array, mock_ansible_module):
        """Test main function fails when v3 is used without user"""
        import pytest

        mock_module = Mock()
        mock_module.params = {
            "version": "v3",
            "community": None,
            "state": "present",
            "user": None,
            "auth_passphrase": None,
            "auth_protocol": None,
            "privacy_passphrase": None,
            "privacy_protocol": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_snmp_agent as agent_module

        original_has = agent_module.HAS_PURESTORAGE
        agent_module.HAS_PURESTORAGE = True

        try:
            with pytest.raises(SystemExit):
                agent_module.main()
            mock_module.fail_json.assert_called_once()
            assert "user" in mock_module.fail_json.call_args[1]["msg"]
        finally:
            agent_module.HAS_PURESTORAGE = original_has

    @patch("plugins.modules.purefa_snmp_agent.AnsibleModule")
    @patch("plugins.modules.purefa_snmp_agent.get_array")
    @patch("plugins.modules.purefa_snmp_agent.LooseVersion")
    def test_main_v3_missing_user(
        self, mock_loose_version, mock_get_array, mock_ansible_module
    ):
        """Test main function fails when v3 is used without user"""
        import pytest

        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "version": "v3",
            "community": None,
            "state": "present",
            "user": None,  # Missing user for v3
            "auth_passphrase": "validpassphrase",
            "auth_protocol": "SHA",
            "privacy_passphrase": None,
            "privacy_protocol": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.38"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_snmp_agent as agent_module

        original_has = agent_module.HAS_PURESTORAGE
        agent_module.HAS_PURESTORAGE = True

        try:
            with pytest.raises(SystemExit):
                agent_module.main()
            mock_module.fail_json.assert_called_once()
            assert "user" in mock_module.fail_json.call_args[1]["msg"]
        finally:
            agent_module.HAS_PURESTORAGE = original_has

    @patch("plugins.modules.purefa_snmp_agent.AnsibleModule")
    @patch("plugins.modules.purefa_snmp_agent.get_array")
    @patch("plugins.modules.purefa_snmp_agent.LooseVersion")
    def test_main_api_version_too_low(
        self, mock_loose_version, mock_get_array, mock_ansible_module
    ):
        """Test main function fails when API version is too low"""
        import pytest

        mock_loose_version.side_effect = lambda x: x
        mock_module = Mock()
        mock_module.params = {
            "version": "v2c",
            "community": "public",
            "state": "present",
            "user": None,
            "auth_passphrase": None,
            "auth_protocol": None,
            "privacy_passphrase": None,
            "privacy_protocol": None,
        }
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "1.0"
        mock_get_array.return_value = mock_array

        import plugins.modules.purefa_snmp_agent as agent_module

        original_has = agent_module.HAS_PURESTORAGE
        agent_module.HAS_PURESTORAGE = True

        try:
            with pytest.raises(SystemExit):
                agent_module.main()
            mock_module.fail_json.assert_called_once()
        finally:
            agent_module.HAS_PURESTORAGE = original_has
