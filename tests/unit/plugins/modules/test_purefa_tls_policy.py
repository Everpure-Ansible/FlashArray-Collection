# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_tls_policy module."""

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
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()

from plugins.modules.purefa_tls_policy import (
    _attached_servers,
    _build_post_kwargs,
    _read_policy,
    _reconcile_servers,
    _tls_enforced_for,
    create_policy,
    delete_policy,
    main,
    rename_policy,
    update_policy,
)


class FakePolicy:
    """Stand-in for the SDK's TLS policy model

    py-pure-client models raise AttributeError for any field the array
    returned as null, which is how an unset value reads.
    """

    def __init__(self, **fields):
        self._fields = fields

    def __getattr__(self, name):
        value = self._fields.get(name)
        if value is None:
            raise AttributeError(name)
        return value


class FakeMembership:
    """A servers/policies/tls membership as the array reports it

    The array returns PolicyMember objects, which name the server as C(member)
    and the policy as C(policy).
    """

    def __init__(self, server=None, policy=None):
        self.member = _ref(server) if server else None
        self.policy = _ref(policy) if policy else None


def _ref(name):
    """A reference-like object exposing a .name"""
    reference = Mock()
    reference.name = name
    return reference


def _params(**overrides):
    params = {
        "name": "nfs_tls",
        "state": "present",
        "enabled": None,
        "rename": None,
        "appliance_certificate": None,
        "min_tls_version": None,
        "enabled_tls_ciphers": None,
        "disabled_tls_ciphers": None,
        "tls_enforced_for": None,
        "client_certificates_required": None,
        "verify_client_certificate_trust": None,
        "trusted_client_certificate_authority": None,
        "servers": None,
        "context": "",
    }
    params.update(overrides)
    return params


class TestTlsEnforcedFor:
    """Validation and normalisation of tls_enforced_for"""

    def test_none_stays_none(self):
        module = Mock()
        module.params = _params()
        assert _tls_enforced_for(module) is None

    def test_nfs_is_lowercased(self):
        module = Mock()
        module.params = _params(tls_enforced_for=["NFS"])
        assert _tls_enforced_for(module) == ["nfs"]

    def test_empty_list_stays_empty(self):
        module = Mock()
        module.params = _params(tls_enforced_for=[])
        assert _tls_enforced_for(module) == []

    def test_non_nfs_protocol_fails(self):
        module = Mock()
        module.params = _params(tls_enforced_for=["smb"])
        module.fail_json.side_effect = SystemExit("fail_json called")

        try:
            _tls_enforced_for(module)
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "only supports" in module.fail_json.call_args[1]["msg"]


class TestReadPolicy:
    """Reading a policy by name"""

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_found_returns_the_item(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        policy = FakePolicy(name="nfs_tls")
        mock_get_with_context.return_value = Mock(status_code=200, items=[policy])

        assert _read_policy(module, Mock(), "nfs_tls") is policy

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_missing_returns_none(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        mock_get_with_context.return_value = Mock(status_code=400, items=[])

        assert _read_policy(module, Mock(), "nfs_tls") is None


class TestAttachedServers:
    """Reading the servers a policy is attached to"""

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_lists_member_servers_sorted(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[
                FakeMembership(server="filesvr2", policy="nfs_tls"),
                FakeMembership(server="filesvr1", policy="nfs_tls"),
            ],
        )

        assert _attached_servers(module, Mock()) == ["filesvr1", "filesvr2"]
        call = mock_get_with_context.call_args
        assert call[0][1] == "get_servers_policies_tls"
        assert call[1]["policy_names"] == ["nfs_tls"]

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_error_reads_as_empty(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        mock_get_with_context.return_value = Mock(status_code=400, items=[])

        assert _attached_servers(module, Mock()) == []


class TestBuildPostKwargs:
    """Only the options the task supplied end up in the POST body"""

    def test_nothing_supplied_defaults_enabled_true(self):
        """The array requires enabled on create, so it defaults to true"""
        module = Mock()
        module.params = _params()
        assert _build_post_kwargs(module) == {"enabled": True}

    def test_supplied_values_are_included(self):
        module = Mock()
        module.params = _params(
            min_tls_version="1.3",
            appliance_certificate="cert1",
            tls_enforced_for=["NFS"],
            client_certificates_required=True,
        )
        kwargs = _build_post_kwargs(module)

        assert kwargs["min_tls_version"] == "1.3"
        assert "appliance_certificate" in kwargs
        assert kwargs["tls_enforced_for"] == ["nfs"]
        assert kwargs["client_certificates_required"] is True

    def test_enabled_false_is_included(self):
        """enabled False is a real request, not the same as omitting it"""
        module = Mock()
        module.params = _params(enabled=False)
        assert _build_post_kwargs(module)["enabled"] is False

    def test_empty_cipher_list_is_included(self):
        """An empty list is distinct from an omitted option"""
        module = Mock()
        module.params = _params(enabled_tls_ciphers=[])
        assert _build_post_kwargs(module)["enabled_tls_ciphers"] == []


class TestCreatePolicy:
    """Test cases for create_policy"""

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_requires_appliance_certificate(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params()
        module.fail_json.side_effect = SystemExit("fail_json called")

        try:
            create_policy(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "appliance_certificate" in module.fail_json.call_args[1]["msg"]
        mock_get_with_context.assert_not_called()

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_creates_with_certificate(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = False
        module.params = _params(appliance_certificate="cert1")
        mock_get_with_context.return_value = Mock(status_code=200)

        create_policy(module, Mock())

        call = mock_get_with_context.call_args
        assert call[0][1] == "post_policies_tls"
        assert call[1]["names"] == ["nfs_tls"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_check_mode_makes_no_write(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = True
        module.params = _params(appliance_certificate="cert1")

        create_policy(module, Mock())

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_create_with_servers_validates_then_attaches(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(appliance_certificate="cert1", servers=["s1"])
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[_ref("s1")]),  # server exists
            Mock(status_code=200, items=[]),  # no conflicting policy
            Mock(status_code=200),  # create
            Mock(status_code=200),  # attach
        ]

        create_policy(module, Mock())

        methods = [c[0][1] for c in mock_get_with_context.call_args_list]
        assert methods == [
            "get_servers",
            "get_servers_policies_tls",
            "post_policies_tls",
            "post_servers_policies_tls",
        ]
        module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePolicy:
    """Test cases for update_policy"""

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_matching_settings_report_no_change(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(min_tls_version="1.3", enabled=True)
        policy = FakePolicy(min_tls_version="1.3", enabled=True)

        update_policy(module, Mock(), policy)

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_min_tls_version_change_is_patched(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(min_tls_version="1.3")
        mock_get_with_context.return_value = Mock(status_code=200)

        update_policy(module, Mock(), FakePolicy(min_tls_version="1.2"))

        call = mock_get_with_context.call_args
        assert call[0][1] == "patch_policies_tls"
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_disabling_an_enabled_policy_is_patched(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(enabled=False)
        mock_get_with_context.return_value = Mock(status_code=200)

        update_policy(module, Mock(), FakePolicy(enabled=True))

        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_cipher_reorder_is_no_change(
        self, mock_get_with_context, mock_check_response
    ):
        """Cipher lists are compared as sets, so order alone is no change"""
        module = Mock()
        module.check_mode = False
        module.params = _params(enabled_tls_ciphers=["b", "a"])

        update_policy(module, Mock(), FakePolicy(enabled_tls_ciphers=["a", "b"]))

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_empty_string_clears_trusted_ca(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(trusted_client_certificate_authority="")
        mock_get_with_context.return_value = Mock(status_code=200)

        policy = FakePolicy(trusted_client_certificate_authority=_ref("old_ca"))
        update_policy(module, Mock(), policy)

        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tls_policy.PolicyTlsPatch")
    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_omitting_trusted_ca_leaves_it_alone(
        self, mock_get_with_context, mock_check_response, mock_patch_model
    ):
        """A task that does not mention the CA must not touch it"""
        module = Mock()
        module.check_mode = False
        module.params = _params(min_tls_version="1.3")
        mock_get_with_context.return_value = Mock(status_code=200)

        policy = FakePolicy(
            min_tls_version="1.2",
            trusted_client_certificate_authority=_ref("keep_me"),
        )
        update_policy(module, Mock(), policy)

        # PolicyTlsPatch is built only from the fields that actually changed
        kwargs = mock_patch_model.call_args.kwargs
        assert "trusted_client_certificate_authority" not in kwargs
        assert kwargs["min_tls_version"] == "1.3"

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_check_mode_reports_but_does_not_patch(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = True
        module.params = _params(min_tls_version="1.3")

        update_policy(module, Mock(), FakePolicy(min_tls_version="1.2"))

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestRenamePolicy:
    """Test cases for rename_policy"""

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_rename_success(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = False
        module.params = _params(rename="nfs_tls_v2")
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[]),  # target does not exist
            Mock(status_code=200),  # patch
        ]

        rename_policy(module, Mock())

        assert mock_get_with_context.call_args_list[1][0][1] == "patch_policies_tls"
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_rename_onto_existing_name_fails(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(rename="nfs_tls_v2")
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[FakePolicy(name="nfs_tls_v2")]
        )

        try:
            rename_policy(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "already exists" in module.fail_json.call_args[1]["msg"]


class TestDeletePolicy:
    """Test cases for delete_policy"""

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_delete_unattached_policy(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = False
        module.params = _params(state="absent")
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[]),  # no attachments
            Mock(status_code=200),  # delete
        ]

        delete_policy(module, Mock())

        assert mock_get_with_context.call_args_list[1][0][1] == "delete_policies_tls"
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_delete_attached_policy_fails(
        self, mock_get_with_context, mock_check_response
    ):
        """A policy still attached to a server is not deleted"""
        module = Mock()
        module.check_mode = False
        module.params = _params(state="absent")
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[FakeMembership(server="filesvr1", policy="nfs_tls")]
        )

        try:
            delete_policy(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        msg = module.fail_json.call_args[1]["msg"]
        assert "filesvr1" in msg
        # Only the attachment read happened - no delete was attempted
        assert [c[0][1] for c in mock_get_with_context.call_args_list] == [
            "get_servers_policies_tls"
        ]

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_delete_check_mode(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = True
        module.params = _params(state="absent")
        mock_get_with_context.return_value = Mock(status_code=200, items=[])

        delete_policy(module, Mock())

        # The attachment is still read, but nothing is deleted
        assert [c[0][1] for c in mock_get_with_context.call_args_list] == [
            "get_servers_policies_tls"
        ]
        module.exit_json.assert_called_once_with(changed=True)


class TestReconcileServers:
    """Attaching and detaching the policy's file servers"""

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_omitting_the_option_touches_nothing(self, mock_get_with_context):
        module = Mock()
        module.check_mode = False
        module.params = _params()

        assert _reconcile_servers(module, Mock()) is False
        mock_get_with_context.assert_not_called()

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_attaches_what_is_missing(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = False
        module.params = _params(servers=["s1", "s2"])
        mock_get_with_context.side_effect = [
            Mock(
                status_code=200, items=[FakeMembership(server="s1", policy="nfs_tls")]
            ),
            Mock(status_code=200, items=[_ref("s2")]),  # s2 exists
            Mock(status_code=200, items=[]),  # s2 has no policy
            Mock(status_code=200),  # attach s2
        ]

        assert _reconcile_servers(module, Mock()) is True

        attach = mock_get_with_context.call_args_list[-1]
        assert attach[0][1] == "post_servers_policies_tls"
        assert attach[1]["member_names"] == ["s2"]

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_detaches_what_is_no_longer_listed(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(servers=[])
        mock_get_with_context.side_effect = [
            Mock(
                status_code=200, items=[FakeMembership(server="s1", policy="nfs_tls")]
            ),
            Mock(status_code=200),  # detach s1
        ]

        assert _reconcile_servers(module, Mock()) is True

        detach = mock_get_with_context.call_args_list[-1]
        assert detach[0][1] == "delete_servers_policies_tls"
        assert detach[1]["member_names"] == ["s1"]

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_already_attached_is_no_change(self, mock_get_with_context):
        module = Mock()
        module.check_mode = False
        module.params = _params(servers=["s1"])
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[FakeMembership(server="s1", policy="nfs_tls")]
        )

        assert _reconcile_servers(module, Mock()) is False

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_conflict_with_a_different_policy_fails(self, mock_get_with_context):
        module = Mock()
        module.check_mode = False
        module.params = _params(servers=["s1"])
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[]),  # not attached to us yet
            Mock(status_code=200, items=[_ref("s1")]),  # s1 exists
            Mock(
                status_code=200,
                items=[FakeMembership(server="s1", policy="other_policy")],
            ),
        ]

        try:
            _reconcile_servers(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "different TLS policy" in module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_missing_server_fails(self, mock_get_with_context):
        module = Mock()
        module.check_mode = False
        module.params = _params(servers=["ghost"])
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[]),  # not attached
            Mock(status_code=200, items=[]),  # get_servers finds nothing
        ]

        try:
            _reconcile_servers(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "not found" in module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_tls_policy.check_response")
    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    def test_check_mode_reports_but_does_not_write(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = True
        module.params = _params(servers=["s1"])
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[]),  # not attached
            Mock(status_code=200, items=[_ref("s1")]),  # s1 exists
            Mock(status_code=200, items=[]),  # s1 has no policy
        ]

        assert _reconcile_servers(module, Mock()) is True

        methods = [c[0][1] for c in mock_get_with_context.call_args_list]
        assert "post_servers_policies_tls" not in methods


class TestMain:
    """Test cases for main"""

    @patch("plugins.modules.purefa_tls_policy.get_array")
    @patch("plugins.modules.purefa_tls_policy.AnsibleModule")
    @patch("plugins.modules.purefa_tls_policy.HAS_PURESTORAGE", False)
    def test_main_missing_sdk(self, mock_ansible_module, mock_get_array):
        module = Mock()
        module.params = _params()
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = module

        try:
            main()
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "py-pure-client sdk is required" in module.fail_json.call_args[1]["msg"]
        mock_get_array.assert_not_called()

    @patch("plugins.modules.purefa_tls_policy.get_array")
    @patch("plugins.modules.purefa_tls_policy.AnsibleModule")
    @patch("plugins.modules.purefa_tls_policy.HAS_PURESTORAGE", True)
    def test_main_invalid_protocol_fails_before_array(
        self, mock_ansible_module, mock_get_array
    ):
        module = Mock()
        module.params = _params(tls_enforced_for=["smb"])
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = module

        try:
            main()
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        mock_get_array.assert_not_called()

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    @patch("plugins.modules.purefa_tls_policy.check_api_version")
    @patch("plugins.modules.purefa_tls_policy.get_array")
    @patch("plugins.modules.purefa_tls_policy.AnsibleModule")
    @patch("plugins.modules.purefa_tls_policy.HAS_PURESTORAGE", True)
    def test_main_checks_the_api_version(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_api_version,
        mock_get_with_context,
    ):
        """TLS policies need REST 2.54, and the guard runs before any work"""
        module = Mock()
        module.check_mode = False
        module.params = _params()
        mock_ansible_module.return_value = module
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[FakePolicy(name="nfs_tls")]
        )

        main()

        mock_check_api_version.assert_called_once()
        args = mock_check_api_version.call_args[0]
        assert args[1] == "2.54"
        assert args[3] == "TLS policies"

    @patch("plugins.modules.purefa_tls_policy.get_with_context")
    @patch("plugins.modules.purefa_tls_policy.check_api_version")
    @patch("plugins.modules.purefa_tls_policy.get_array")
    @patch("plugins.modules.purefa_tls_policy.AnsibleModule")
    @patch("plugins.modules.purefa_tls_policy.HAS_PURESTORAGE", True)
    def test_main_absent_policy_reports_no_change(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_api_version,
        mock_get_with_context,
    ):
        """Deleting a policy that is not there changes nothing"""
        module = Mock()
        module.check_mode = False
        module.params = _params(state="absent")
        mock_ansible_module.return_value = module
        mock_get_with_context.return_value = Mock(status_code=400, items=[])

        main()

        module.exit_json.assert_called_once_with(changed=False)
