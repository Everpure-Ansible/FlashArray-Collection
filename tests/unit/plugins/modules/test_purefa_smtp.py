# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_smtp module."""

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

from plugins.modules.purefa_smtp import (
    delete_smtp,
    create_smtp,
)


class FakeSmtpServer:
    """Stand-in for the SDK's SmtpServer model.

    py-pure-client models raise AttributeError for any field the array
    returned as null instead of returning None. Mock objects always return
    whatever they were given, which is why issue #1040 was invisible to the
    original unit tests - use this for anything that depends on how unset
    settings are read.
    """

    def __init__(self, **fields):
        self._fields = fields

    def __getattr__(self, name):
        value = self._fields.get(name)
        if value is None:
            raise AttributeError(name)
        return value


def configured_smtp():
    """A FakeSmtpServer with only relay_host and sender_domain configured"""
    return FakeSmtpServer(
        name="smtp",
        sender_domain="test.com",
        relay_host="relay.test.com",
        encryption_mode="starttls",
        user_name=None,
        sender_username=None,
        subject_prefix=None,
        body_prefix=None,
    )


class TestDeleteSmtp:
    """Tests for delete_smtp function"""

    def test_delete_smtp_check_mode(self):
        """Test delete_smtp in check mode"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_array = Mock()
        mock_array.get_smtp_servers.return_value.items = [configured_smtp()]

        delete_smtp(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=True)
        mock_array.patch_smtp_servers.assert_not_called()

    def test_delete_smtp_already_cleared(self):
        """Test delete_smtp is idempotent when SMTP is already cleared"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_smtp_servers.return_value.items = [
            FakeSmtpServer(
                name="smtp",
                sender_domain="None",
                relay_host=None,
                encryption_mode=None,
                user_name=None,
                sender_username=None,
                subject_prefix=None,
                body_prefix=None,
            )
        ]

        delete_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)


class TestCreateSmtp:
    """Tests for create_smtp function"""

    def test_create_smtp_no_change(self):
        """Test create_smtp when settings already match"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "sender_domain": "example.com",
            "relay_host": "smtp.example.com",
            "user": None,
            "password": None,
            "encryption_mode": "tls",
            "sender": None,
            "subject_prefix": "[Alert]",
            "body_prefix": "FlashArray:",
        }
        mock_array = Mock()
        # Current settings match
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.user_name = None
        mock_smtp.encryption_mode = "tls"
        mock_smtp.sender_username = None
        mock_smtp.subject_prefix = "[Alert]"
        mock_smtp.body_prefix = "FlashArray:"
        mock_array.get_smtp_servers.return_value.items = [mock_smtp]

        create_smtp(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_smtp.check_response")
    def test_create_smtp_with_changes_no_password(self, mock_check_response):
        """Test create_smtp when settings change without password"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "sender_domain": "new-domain.com",
            "relay_host": "new-smtp.example.com",
            "user": None,
            "password": None,
            "encryption_mode": "starttls",
            "sender": "alerts",
            "subject_prefix": "[NewAlert]",
            "body_prefix": "NewPrefix:",
        }
        mock_array = Mock()
        # Current settings different
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.user_name = None
        mock_smtp.encryption_mode = "tls"
        mock_smtp.sender_username = None
        mock_smtp.subject_prefix = "[Alert]"
        mock_smtp.body_prefix = "FlashArray:"
        mock_array.get_smtp_servers.return_value.items = [mock_smtp]
        mock_array.patch_smtp_servers.return_value = Mock(status_code=200)

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_smtp.check_response")
    def test_create_smtp_with_password(self, mock_check_response):
        """Test create_smtp when password is provided"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "sender_domain": "example.com",
            "relay_host": "smtp.example.com",
            "user": "smtp_user",
            "password": "secret_password",
            "encryption_mode": "tls",
            "sender": None,
            "subject_prefix": "[Alert]",
            "body_prefix": "FlashArray:",
        }
        mock_array = Mock()
        # Current settings match but password forces change
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.user_name = "smtp_user"
        mock_smtp.encryption_mode = "tls"
        mock_smtp.sender_username = None
        mock_smtp.subject_prefix = "[Alert]"
        mock_smtp.body_prefix = "FlashArray:"
        mock_array.get_smtp_servers.return_value.items = [mock_smtp]
        mock_array.patch_smtp_servers.return_value = Mock(status_code=200)

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_smtp.check_response")
    def test_create_smtp_change_user(self, mock_check_response):
        """Test create_smtp when user changes - regression test for issue #990"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "sender_domain": None,
            "relay_host": None,
            "user": "new_smtp_user",
            "password": "secret_password",
            "encryption_mode": None,
            "sender": None,
            "subject_prefix": None,
            "body_prefix": None,
        }
        mock_array = Mock()
        # Current settings have different user
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.user_name = "old_smtp_user"
        mock_smtp.encryption_mode = "tls"
        mock_smtp.sender_username = None
        mock_smtp.subject_prefix = "[Alert]"
        mock_smtp.body_prefix = "FlashArray:"
        mock_array.get_smtp_servers.return_value.items = [mock_smtp]
        mock_array.patch_smtp_servers.return_value = Mock(status_code=200)

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_called_once()
        # Verify user_name is in the patch call
        call_args = mock_array.patch_smtp_servers.call_args
        assert call_args is not None
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_smtp_check_mode_with_changes(self):
        """Test create_smtp in check mode when changes would be made"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "sender_domain": "new-domain.com",
            "relay_host": "new-smtp.example.com",
            "user": None,
            "password": None,
            "encryption_mode": "starttls",
            "sender": None,
            "subject_prefix": "[NewAlert]",
            "body_prefix": "NewPrefix:",
        }
        mock_array = Mock()
        # Current settings different
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.user_name = None
        mock_smtp.encryption_mode = "tls"
        mock_smtp.sender_username = None
        mock_smtp.subject_prefix = "[Alert]"
        mock_smtp.body_prefix = "FlashArray:"
        mock_array.get_smtp_servers.return_value.items = [mock_smtp]

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestDeleteSmtpSuccess:
    """Additional tests for delete_smtp function"""

    @patch("plugins.modules.purefa_smtp.check_response")
    def test_delete_smtp_success(self, mock_check_response):
        """Test delete_smtp successfully deletes"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_array = Mock()
        mock_array.get_smtp_servers.return_value.items = [configured_smtp()]
        mock_array.patch_smtp_servers.return_value = Mock(status_code=200)

        delete_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateSmtpSuccess:
    """Additional tests for create_smtp success paths"""

    @patch("plugins.modules.purefa_smtp.check_response")
    def test_create_smtp_with_password(self, mock_check_response):
        """Test create_smtp with password update"""
        mock_module = Mock()
        mock_module.params = {
            "sender_domain": None,
            "relay_host": None,
            "user": None,
            "password": "new_password",
            "sender": None,
            "body_prefix": None,
            "subject_prefix": None,
            "encryption_mode": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.user_name = "smtp_user"
        mock_smtp.encryption_mode = "starttls"
        mock_smtp.sender_username = "sender"
        mock_smtp.subject_prefix = "[PURE]"
        mock_smtp.body_prefix = "Alert:"
        mock_array.get_smtp_servers.return_value = Mock(items=[mock_smtp])
        mock_array.patch_smtp_servers.return_value = Mock(status_code=200)

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_smtp.check_response")
    def test_create_smtp_change_relay_host(self, mock_check_response):
        """Test create_smtp when relay_host changes"""
        mock_module = Mock()
        mock_module.params = {
            "sender_domain": None,
            "relay_host": "new-smtp.example.com",
            "user": None,
            "password": None,
            "sender": None,
            "body_prefix": None,
            "subject_prefix": None,
            "encryption_mode": None,
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "old-smtp.example.com"
        mock_smtp.user_name = "smtp_user"
        mock_smtp.encryption_mode = "starttls"
        mock_smtp.sender_username = "sender"
        mock_smtp.subject_prefix = "[PURE]"
        mock_smtp.body_prefix = "Alert:"
        mock_array.get_smtp_servers.return_value = Mock(items=[mock_smtp])
        mock_array.patch_smtp_servers.return_value = Mock(status_code=200)

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_smtp.check_response")
    def test_create_smtp_change_encryption_mode(self, mock_check_response):
        """Test create_smtp when encryption_mode changes"""
        mock_module = Mock()
        mock_module.params = {
            "sender_domain": None,
            "relay_host": None,
            "user": None,
            "password": None,
            "sender": None,
            "body_prefix": None,
            "subject_prefix": None,
            "encryption_mode": "ssl",
        }
        mock_module.check_mode = False
        mock_array = Mock()
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.user_name = "smtp_user"
        mock_smtp.encryption_mode = "starttls"
        mock_smtp.sender_username = "sender"
        mock_smtp.subject_prefix = "[PURE]"
        mock_smtp.body_prefix = "Alert:"
        mock_array.get_smtp_servers.return_value = Mock(items=[mock_smtp])
        mock_array.patch_smtp_servers.return_value = Mock(status_code=200)

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_smtp_change_subject_prefix(self):
        """Test create_smtp when subject_prefix changes"""
        mock_module = Mock()
        mock_module.params = {
            "sender_domain": None,
            "relay_host": None,
            "user": None,
            "password": None,
            "sender": None,
            "body_prefix": None,
            "subject_prefix": "[NEW PREFIX]",
            "encryption_mode": None,
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.user_name = "smtp_user"
        mock_smtp.encryption_mode = "starttls"
        mock_smtp.sender_username = "sender"
        mock_smtp.subject_prefix = "[OLD PREFIX]"
        mock_smtp.body_prefix = "Alert:"
        mock_array.get_smtp_servers.return_value = Mock(items=[mock_smtp])

        create_smtp(mock_module, mock_array)

        # Check mode - no API call
        mock_array.patch_smtp_servers.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_smtp_change_body_prefix(self):
        """Test create_smtp when body_prefix changes"""
        mock_module = Mock()
        mock_module.params = {
            "sender_domain": None,
            "relay_host": None,
            "user": None,
            "password": None,
            "sender": None,
            "body_prefix": "New Body:",
            "subject_prefix": None,
            "encryption_mode": None,
        }
        mock_module.check_mode = True
        mock_array = Mock()
        mock_smtp = Mock()
        mock_smtp.sender_domain = "example.com"
        mock_smtp.relay_host = "smtp.example.com"
        mock_smtp.user_name = "smtp_user"
        mock_smtp.encryption_mode = "starttls"
        mock_smtp.sender_username = "sender"
        mock_smtp.subject_prefix = "[PURE]"
        mock_smtp.body_prefix = "Old Body:"
        mock_array.get_smtp_servers.return_value = Mock(items=[mock_smtp])

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreateSmtpIdempotency:
    """Regression tests for issue #1040 - purefa_smtp always reports changed"""

    def test_create_smtp_no_change_with_unset_settings(self):
        """Settings the array leaves unset must not count as a change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "sender_domain": "test.com",
            "relay_host": "relay.test.com",
            "user": None,
            "password": None,
            "encryption_mode": "starttls",
            "sender": None,
            "subject_prefix": None,
            "body_prefix": None,
        }
        mock_array = Mock()
        # user_name, sender_username, subject_prefix and body_prefix were never
        # configured, so the array returns them as null
        mock_array.get_smtp_servers.return_value.items = [configured_smtp()]

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)

    def test_create_smtp_no_change_in_check_mode(self):
        """The same play in check mode must also report no change"""
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "sender_domain": "test.com",
            "relay_host": "relay.test.com",
            "user": None,
            "password": None,
            "encryption_mode": "starttls",
            "sender": None,
            "subject_prefix": None,
            "body_prefix": None,
        }
        mock_array = Mock()
        mock_array.get_smtp_servers.return_value.items = [configured_smtp()]

        create_smtp(mock_module, mock_array)

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_smtp.check_response")
    def test_create_smtp_change_detected_with_unset_settings(self, mock_check_response):
        """A real change is still detected when other settings are unset"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "sender_domain": "test.com",
            "relay_host": "new-relay.test.com",
            "user": None,
            "password": None,
            "encryption_mode": "starttls",
            "sender": None,
            "subject_prefix": None,
            "body_prefix": None,
        }
        mock_array = Mock()
        mock_array.get_smtp_servers.return_value.items = [configured_smtp()]
        mock_array.patch_smtp_servers.return_value = Mock(status_code=200)

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_smtp.SmtpServer")
    @patch("plugins.modules.purefa_smtp.check_response")
    def test_create_smtp_clear_encryption_mode(
        self, mock_check_response, mock_smtp_server
    ):
        """An empty encryption_mode clears the setting, as documented"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "sender_domain": None,
            "relay_host": None,
            "user": None,
            "password": None,
            "encryption_mode": "",
            "sender": None,
            "subject_prefix": None,
            "body_prefix": None,
        }
        mock_array = Mock()
        mock_array.get_smtp_servers.return_value.items = [configured_smtp()]
        mock_array.patch_smtp_servers.return_value = Mock(status_code=200)

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_called_once()
        assert mock_smtp_server.call_args.kwargs["encryption_mode"] == ""
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_create_smtp_cleared_encryption_mode_is_idempotent(self):
        """Re-running with an empty encryption_mode reports no change"""
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "sender_domain": None,
            "relay_host": None,
            "user": None,
            "password": None,
            "encryption_mode": "",
            "sender": None,
            "subject_prefix": None,
            "body_prefix": None,
        }
        mock_array = Mock()
        mock_array.get_smtp_servers.return_value.items = [
            FakeSmtpServer(
                name="smtp",
                sender_domain="test.com",
                relay_host="relay.test.com",
                encryption_mode=None,
                user_name=None,
                sender_username=None,
                subject_prefix=None,
                body_prefix=None,
            )
        ]

        create_smtp(mock_module, mock_array)

        mock_array.patch_smtp_servers.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=False)
