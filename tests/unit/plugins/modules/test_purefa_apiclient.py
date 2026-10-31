# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_apiclient module."""

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

from plugins.modules.purefa_apiclient import (
    delete_client,
    update_client,
)

PEM_KEY = (
    "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEF\n-----END PUBLIC KEY-----"
)
OTHER_PEM_KEY = (
    "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEG\n-----END PUBLIC KEY-----"
)


def _existing_client(**overrides):
    """Mock of the ApiClient object the array returns for an existing client"""
    client = Mock()
    client.enabled = True
    client.public_key = PEM_KEY
    client.issuer = "my-issuer"
    client.max_role = "readonly"
    client.access_token_ttl_in_ms = 3600000
    for key, value in overrides.items():
        setattr(client, key, value)
    return client


def _update_params(**overrides):
    """Module params that match _existing_client() exactly"""
    params = {
        "name": "client1",
        "enabled": True,
        "public_key": PEM_KEY,
        "issuer": "my-issuer",
        "role": "readonly",
        "token_ttl": 3600,
    }
    params.update(overrides)
    return params


class TestDeleteClient:
    """Tests for delete_client function"""

    def test_delete_client_check_mode(self):
        """Test delete_client in check mode"""
        mock_module = Mock()
        mock_module.params = {"name": "client1"}
        mock_module.check_mode = True
        mock_array = Mock()

        delete_client(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.delete_api_clients.assert_not_called()

    def test_delete_client_success(self):
        """Test delete_client successfully deletes"""
        mock_module = Mock()
        mock_module.params = {"name": "client1"}
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.delete_api_clients.return_value = Mock(status_code=200)

        delete_client(mock_module, mock_array)

        mock_array.delete_api_clients.assert_called_once_with(names=["client1"])
        mock_module.exit_json.assert_called_with(changed=True)


class TestUpdateClient:
    """Tests for update_client function"""

    def test_update_client_no_change(self):
        """Test an identical client reports changed=False with no warning"""
        mock_module = Mock()
        mock_module.params = _update_params()
        mock_module.check_mode = False
        mock_array = Mock()

        update_client(mock_module, mock_array, _existing_client())

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_module.warn.assert_not_called()
        mock_array.patch_api_clients.assert_not_called()

    def test_update_client_unset_options_not_compared(self):
        """Test options left unset are not compared against the array"""
        mock_module = Mock()
        mock_module.params = _update_params(
            public_key=None, issuer=None, role=None, token_ttl=None
        )
        mock_module.check_mode = False
        mock_array = Mock()
        mock_client = _existing_client(
            public_key=OTHER_PEM_KEY,
            issuer="other-issuer",
            max_role="array_admin",
            access_token_ttl_in_ms=86400000,
        )

        update_client(mock_module, mock_array, mock_client)

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_module.warn.assert_not_called()
        mock_array.patch_api_clients.assert_not_called()

    def test_update_client_check_mode(self):
        """Test update_client in check mode when change needed"""
        mock_module = Mock()
        mock_module.params = _update_params(enabled=False)
        mock_module.check_mode = True
        mock_array = Mock()

        update_client(mock_module, mock_array, _existing_client())

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_api_clients.assert_not_called()

    @patch("plugins.modules.purefa_apiclient.flasharray")
    @patch("plugins.modules.purefa_apiclient.check_response")
    def test_update_client_enable_success(self, mock_check_response, mock_flasharray):
        """Test update_client enables the client with an enabled-only PATCH"""
        mock_module = Mock()
        mock_module.params = _update_params(enabled=True)
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_api_clients.return_value = Mock(status_code=200)

        update_client(mock_module, mock_array, _existing_client(enabled=False))

        mock_flasharray.ApiClientPatch.assert_called_once_with(enabled=True)
        mock_array.patch_api_clients.assert_called_once_with(
            names=["client1"],
            api_clients=mock_flasharray.ApiClientPatch.return_value,
        )
        mock_module.warn.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_update_client_public_key_differs_warns(self):
        """Test a different public_key warns and is not applied"""
        mock_module = Mock()
        mock_module.params = _update_params(public_key=OTHER_PEM_KEY)
        mock_module.check_mode = False
        mock_array = Mock()

        update_client(mock_module, mock_array, _existing_client())

        mock_module.warn.assert_called_once()
        message = mock_module.warn.call_args[0][0]
        assert message.startswith("API Client client1: public_key cannot be changed")
        assert "Delete and recreate the client" in message
        mock_array.patch_api_clients.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_update_client_public_key_whitespace_ignored(self):
        """Test CRLF line endings and a trailing newline are not a key change"""
        mock_module = Mock()
        mock_module.params = _update_params(
            public_key=PEM_KEY.replace("\n", "\r\n") + "\n"
        )
        mock_module.check_mode = False
        mock_array = Mock()

        update_client(mock_module, mock_array, _existing_client())

        mock_module.warn.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_update_client_issuer_differs_warns(self):
        """Test a different issuer warns"""
        mock_module = Mock()
        mock_module.params = _update_params(issuer="new-issuer")
        mock_module.check_mode = False
        mock_array = Mock()

        update_client(mock_module, mock_array, _existing_client())

        mock_module.warn.assert_called_once()
        assert mock_module.warn.call_args[0][0].startswith(
            "API Client client1: issuer cannot be changed"
        )
        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_update_client_role_differs_warns(self):
        """Test a role different from the array max_role warns"""
        mock_module = Mock()
        mock_module.params = _update_params(role="array_admin")
        mock_module.check_mode = False
        mock_array = Mock()

        update_client(mock_module, mock_array, _existing_client())

        mock_module.warn.assert_called_once()
        assert mock_module.warn.call_args[0][0].startswith(
            "API Client client1: role cannot be changed"
        )
        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_update_client_role_warns_when_array_max_role_is_none(self):
        """Test a role warns when the array reports no legacy max_role"""
        mock_module = Mock()
        mock_module.params = _update_params(role="readonly")
        mock_module.check_mode = False
        mock_array = Mock()

        update_client(mock_module, mock_array, _existing_client(max_role=None))

        mock_module.warn.assert_called_once()
        assert mock_module.warn.call_args[0][0].startswith(
            "API Client client1: role cannot be changed"
        )

    def test_update_client_token_ttl_differs_warns(self):
        """Test token_ttl is compared in milliseconds against the array"""
        mock_module = Mock()
        mock_module.params = _update_params(token_ttl=86400)
        mock_module.check_mode = False
        mock_array = Mock()

        update_client(mock_module, mock_array, _existing_client())

        mock_module.warn.assert_called_once()
        assert mock_module.warn.call_args[0][0].startswith(
            "API Client client1: token_ttl cannot be changed"
        )
        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_update_client_all_differ_warns_once_naming_all(self):
        """Test one warning names every differing option"""
        mock_module = Mock()
        mock_module.params = _update_params(
            public_key=OTHER_PEM_KEY,
            issuer="new-issuer",
            role="array_admin",
            token_ttl=60,
        )
        mock_module.check_mode = False
        mock_array = Mock()

        update_client(mock_module, mock_array, _existing_client())

        mock_module.warn.assert_called_once_with(
            "API Client client1: public_key, issuer, role, token_ttl cannot be "
            "changed on an existing client and will remain as currently set on "
            "the array. Delete and recreate the client to apply the new value(s)."
        )
        mock_array.patch_api_clients.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_apiclient.flasharray")
    @patch("plugins.modules.purefa_apiclient.check_response")
    def test_update_client_warns_and_still_patches_enabled(
        self, mock_check_response, mock_flasharray
    ):
        """Test an immutable difference does not block the enabled change"""
        mock_module = Mock()
        mock_module.params = _update_params(enabled=False, issuer="new-issuer")
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.patch_api_clients.return_value = Mock(status_code=200)

        update_client(mock_module, mock_array, _existing_client(enabled=True))

        mock_module.warn.assert_called_once()
        assert mock_module.warn.call_args[0][0].startswith(
            "API Client client1: issuer cannot be changed"
        )
        mock_flasharray.ApiClientPatch.assert_called_once_with(enabled=False)
        mock_array.patch_api_clients.assert_called_once_with(
            names=["client1"],
            api_clients=mock_flasharray.ApiClientPatch.return_value,
        )
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateClient:
    """Tests for create_client function"""

    def test_create_client_check_mode(self):
        """Test create_client in check mode"""
        from plugins.modules.purefa_apiclient import create_client

        mock_module = Mock()
        mock_module.params = {
            "name": "new-client",
            "token_ttl": 3600,
            "issuer": "my-issuer",
            "role": "readonly",
            "public_key": "ssh-rsa AAAA...",
            "enabled": True,
        }
        mock_module.check_mode = True
        mock_array = Mock()

        create_client(mock_module, mock_array)

        mock_array.post_api_clients.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_client_ttl_out_of_range(self):
        """Test create_client fails when token_ttl out of range"""
        import pytest
        from plugins.modules.purefa_apiclient import create_client

        mock_module = Mock()
        mock_module.params = {
            "name": "new-client",
            "token_ttl": 100000,  # Out of range
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()

        with pytest.raises(SystemExit):
            create_client(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_apiclient.check_response")
    def test_create_client_success(self, mock_check_response):
        """Test create_client successfully creates client"""
        from plugins.modules.purefa_apiclient import create_client

        mock_module = Mock()
        mock_module.params = {
            "name": "new-client",
            "token_ttl": 3600,
            "issuer": None,  # Will default to name
            "role": "readonly",
            "public_key": "ssh-rsa AAAA...",
            "enabled": False,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.post_api_clients.return_value = Mock(status_code=200)

        create_client(mock_module, mock_array)

        mock_array.post_api_clients.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_apiclient.check_response")
    def test_create_client_with_enabled_true(self, mock_check_response):
        """Test create_client with enabled=True triggers patch"""
        from plugins.modules.purefa_apiclient import create_client

        mock_module = Mock()
        mock_module.params = {
            "name": "new-client",
            "token_ttl": 3600,
            "issuer": "my-issuer",
            "role": "readonly",
            "public_key": "ssh-rsa AAAA...",
            "enabled": True,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.post_api_clients.return_value = Mock(status_code=200)
        mock_array.patch_api_clients.return_value = Mock(status_code=200)

        create_client(mock_module, mock_array)

        mock_array.post_api_clients.assert_called_once()
        mock_array.patch_api_clients.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_client_enable_fails(self):
        """Test create_client when enabling fails - should delete and fail"""
        import pytest
        from plugins.modules.purefa_apiclient import create_client

        mock_module = Mock()
        mock_module.params = {
            "name": "new-client",
            "token_ttl": 3600,
            "issuer": "my-issuer",
            "role": "readonly",
            "public_key": "ssh-rsa AAAA...",
            "enabled": True,
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()
        mock_array.post_api_clients.return_value = Mock(status_code=200)
        mock_error = Mock()
        mock_error.message = "Enable failed"
        mock_array.patch_api_clients.return_value = Mock(
            status_code=400, errors=[mock_error]
        )

        with pytest.raises(SystemExit):
            create_client(mock_module, mock_array)

        mock_array.post_api_clients.assert_called_once()
        mock_array.patch_api_clients.assert_called_once()
        mock_array.delete_api_clients.assert_called_once_with(names=["new-client"])
        mock_module.fail_json.assert_called_once()

    def test_create_client_ttl_zero_out_of_range(self):
        """Test create_client fails when token_ttl is 0"""
        import pytest
        from plugins.modules.purefa_apiclient import create_client

        mock_module = Mock()
        mock_module.params = {
            "name": "new-client",
            "token_ttl": 0,
        }
        mock_module.check_mode = False
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_array = Mock()

        with pytest.raises(SystemExit):
            create_client(mock_module, mock_array)

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_apiclient.flasharray")
    @patch("plugins.modules.purefa_apiclient.check_response")
    def test_create_client_sends_ttl_in_milliseconds(
        self, mock_check_response, mock_flasharray
    ):
        """Test token_ttl seconds are sent as access_token_ttl_in_ms"""
        from plugins.modules.purefa_apiclient import create_client

        mock_module = Mock()
        mock_module.params = {
            "name": "new-client",
            "token_ttl": 3600,
            "issuer": "my-issuer",
            "role": "readonly",
            "public_key": PEM_KEY,
            "enabled": False,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.post_api_clients.return_value = Mock(status_code=200)

        create_client(mock_module, mock_array)

        mock_flasharray.ApiClientPost.assert_called_once_with(
            max_role="readonly",
            issuer="my-issuer",
            access_token_ttl_in_ms=3600000,
            public_key=PEM_KEY,
        )
        mock_array.post_api_clients.assert_called_once_with(
            names=["new-client"],
            api_clients=mock_flasharray.ApiClientPost.return_value,
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_apiclient.flasharray")
    @patch("plugins.modules.purefa_apiclient.check_response")
    def test_create_client_default_ttl_when_unset(
        self, mock_check_response, mock_flasharray
    ):
        """Test an unset token_ttl defaults to one day on creation"""
        from plugins.modules.purefa_apiclient import create_client

        mock_module = Mock()
        mock_module.params = {
            "name": "new-client",
            "token_ttl": None,
            "issuer": "my-issuer",
            "role": "readonly",
            "public_key": PEM_KEY,
            "enabled": False,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.post_api_clients.return_value = Mock(status_code=200)

        create_client(mock_module, mock_array)

        mock_flasharray.ApiClientPost.assert_called_once_with(
            max_role="readonly",
            issuer="my-issuer",
            access_token_ttl_in_ms=86400000,
            public_key=PEM_KEY,
        )
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMainFunction:
    """Tests for main function"""

    @patch("plugins.modules.purefa_apiclient.AnsibleModule")
    @patch("plugins.modules.purefa_apiclient.get_array")
    @patch("plugins.modules.purefa_apiclient.create_client")
    def test_main_create_client(self, mock_create, mock_get_array, mock_ansible_module):
        """Test main() creates client when not exists"""
        from plugins.modules.purefa_apiclient import main

        mock_module = Mock()
        mock_module.params = {
            "name": "test-client",
            "state": "present",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_array.get_api_clients.return_value = Mock(items=[])
        mock_get_array.return_value = mock_array

        main()

        mock_create.assert_called_once()

    @patch("plugins.modules.purefa_apiclient.AnsibleModule")
    @patch("plugins.modules.purefa_apiclient.get_array")
    @patch("plugins.modules.purefa_apiclient.update_client")
    def test_main_update_client(self, mock_update, mock_get_array, mock_ansible_module):
        """Test main() updates client when exists"""
        from plugins.modules.purefa_apiclient import main

        mock_module = Mock()
        mock_module.params = {
            "name": "test-client",
            "state": "present",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_client = Mock()
        mock_client.name = "test-client"
        mock_array.get_api_clients.return_value = Mock(items=[mock_client])
        mock_get_array.return_value = mock_array

        main()

        mock_update.assert_called_once()

    @patch("plugins.modules.purefa_apiclient.AnsibleModule")
    @patch("plugins.modules.purefa_apiclient.get_array")
    @patch("plugins.modules.purefa_apiclient.delete_client")
    def test_main_delete_client(self, mock_delete, mock_get_array, mock_ansible_module):
        """Test main() deletes client when exists and state=absent"""
        from plugins.modules.purefa_apiclient import main

        mock_module = Mock()
        mock_module.params = {
            "name": "test-client",
            "state": "absent",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_client = Mock()
        mock_client.name = "test-client"
        mock_array.get_api_clients.return_value = Mock(items=[mock_client])
        mock_get_array.return_value = mock_array

        main()

        mock_delete.assert_called_once()

    @patch("plugins.modules.purefa_apiclient.AnsibleModule")
    @patch("plugins.modules.purefa_apiclient.get_array")
    def test_main_absent_not_exists(self, mock_get_array, mock_ansible_module):
        """Test main() does nothing when state=absent and client doesn't exist"""
        from plugins.modules.purefa_apiclient import main

        mock_module = Mock()
        mock_module.params = {
            "name": "test-client",
            "state": "absent",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.10"
        mock_array.get_api_clients.return_value = Mock(items=[])
        mock_get_array.return_value = mock_array

        main()

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_apiclient.HAS_PURESTORAGE", False)
    @patch("plugins.modules.purefa_apiclient.AnsibleModule")
    def test_main_no_purestorage(self, mock_ansible_module):
        """Test main() fails when py-pure-client is not installed"""
        import pytest
        from plugins.modules.purefa_apiclient import main

        mock_module = Mock()
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_apiclient.AnsibleModule")
    @patch("plugins.modules.purefa_apiclient.get_array")
    def test_main_api_version_too_low(self, mock_get_array, mock_ansible_module):
        """Test main() fails when API version is too low"""
        import pytest
        from plugins.modules.purefa_apiclient import main

        mock_module = Mock()
        mock_module.params = {"name": "test-client", "state": "present"}
        mock_module.fail_json.side_effect = SystemExit(1)
        mock_ansible_module.return_value = mock_module
        mock_array = Mock()
        mock_array.get_rest_version.return_value = "1.0"
        mock_get_array.return_value = mock_array

        with pytest.raises(SystemExit):
            main()

        mock_module.fail_json.assert_called_once()
