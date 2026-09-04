# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_server module."""

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

from plugins.modules.purefa_server import (
    _attached_interfaces,
    _reconcile_interfaces,
    _reference_name,
    _requested_references,
    create_server,
    delete_server,
    main,
    rename_server,
    update_server,
)


class FakeServer:
    """Stand-in for the SDK's server model

    py-pure-client models raise AttributeError for any field the array
    returned as null, which is how an unset reference reads.
    """

    def __init__(self, **fields):
        self._fields = fields

    def __getattr__(self, name):
        value = self._fields.get(name)
        if value is None:
            raise AttributeError(name)
        return value


def _ref(name):
    """A FixedReference-like object exposing a .name"""
    reference = Mock()
    reference.name = name
    return reference


def _params(**overrides):
    params = {
        "name": "filesvr1",
        "state": "present",
        "rename": None,
        "dns": None,
        "directory_service": None,
        "local_directory_service": None,
        "create_local_directory_service": None,
        "network_interfaces": None,
        "cascade_delete": None,
        "context": "",
    }
    params.update(overrides)
    return params


def _interface(name, attached_to=None):
    """A network interface record as the array reports it"""
    interface = Mock()
    interface.name = name
    if attached_to is None:
        interface.attached_servers = []
    else:
        reference = Mock()
        reference.name = attached_to
        interface.attached_servers = [reference]
    return interface


class TestReferenceReads:
    """Reading the references off a server the array returned"""

    def test_unset_list_reference_reads_as_none(self):
        """An unset dns raises AttributeError on the model"""
        assert _reference_name(FakeServer(), "dns") is None

    def test_empty_list_reference_reads_as_none(self):
        assert _reference_name(FakeServer(dns=[]), "dns") is None

    def test_list_reference_reads_its_name(self):
        server = FakeServer(dns=[_ref("filesvr1-dns")])
        assert _reference_name(server, "dns") == "filesvr1-dns"

    def test_single_reference_reads_its_name(self):
        server = FakeServer(local_directory_service=_ref("lds1"))
        assert _reference_name(server, "local_directory_service") == "lds1"

    def test_unset_single_reference_reads_as_none(self):
        assert _reference_name(FakeServer(), "local_directory_service") is None


class TestRequestedReferences:
    """Only the options the task supplied are acted on"""

    def test_unmentioned_settings_are_left_alone(self):
        module = Mock()
        module.params = _params()
        assert _requested_references(module) == {}

    def test_supplied_settings_map_to_api_fields(self):
        module = Mock()
        module.params = _params(dns="d1", directory_service="ds1")
        assert _requested_references(module) == {
            "dns": "d1",
            "directory_services": "ds1",
        }

    def test_empty_string_is_a_request_to_detach(self):
        module = Mock()
        module.params = _params(dns="")
        assert _requested_references(module) == {"dns": ""}


class TestCreateServer:
    """Test cases for create_server"""

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_create_bare_server_sends_no_body(
        self, mock_get_with_context, mock_check_response
    ):
        """A create with no references needs only the name"""
        module = Mock()
        module.check_mode = False
        module.params = _params()
        mock_get_with_context.return_value = Mock(status_code=200)

        create_server(module, Mock())

        call = mock_get_with_context.call_args
        assert call[0][1] == "post_servers"
        assert call[1]["names"] == ["filesvr1"]
        assert "server" not in call[1]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_create_passes_local_directory_service_name(
        self, mock_get_with_context, mock_check_response
    ):
        """create_local_directory_service carries a name, not a flag"""
        module = Mock()
        module.check_mode = False
        module.params = _params(dns="d1", create_local_directory_service="lds1")
        mock_get_with_context.return_value = Mock(status_code=200)

        create_server(module, Mock())

        call = mock_get_with_context.call_args
        assert call[1]["create_local_directory_service"] == "lds1"
        assert "server" in call[1]

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_create_check_mode(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = True
        module.params = _params(create_local_directory_service="lds1")

        create_server(module, Mock())

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_create_needs_a_directory_service(
        self, mock_get_with_context, mock_check_response
    ):
        """The array refuses a file server created from a name alone

        Verified on Purity 6.10.6: POST /servers with only a name, or with a
        DNS configuration and nothing else, is refused with "At least one of
        the arguments is required".
        """
        module = Mock()
        module.check_mode = False
        module.params = _params(dns="d1")
        module.fail_json.side_effect = SystemExit("fail_json called")

        try:
            create_server(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        msg = module.fail_json.call_args[1]["msg"]
        assert "requires one of" in msg
        assert "create_local_directory_service" in msg
        mock_get_with_context.assert_not_called()

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_create_guard_applies_in_check_mode_too(
        self, mock_get_with_context, mock_check_response
    ):
        """Check mode predicts the array's refusal rather than reporting a change"""
        module = Mock()
        module.check_mode = True
        module.params = _params()
        module.fail_json.side_effect = SystemExit("fail_json called")

        try:
            create_server(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        module.exit_json.assert_not_called()


class TestUpdateServer:
    """Test cases for update_server"""

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_matching_settings_report_no_change(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(dns="d1", directory_service="ds1")

        server = FakeServer(dns=[_ref("d1")], directory_services=[_ref("ds1")])
        update_server(module, Mock(), server)

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_differing_dns_is_patched(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = False
        module.params = _params(dns="d2")
        mock_get_with_context.return_value = Mock(status_code=200)

        update_server(module, Mock(), FakeServer(dns=[_ref("d1")]))

        call = mock_get_with_context.call_args
        assert call[0][1] == "patch_servers"
        assert call[1]["names"] == ["filesvr1"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_unset_reference_is_attached(
        self, mock_get_with_context, mock_check_response
    ):
        """A server whose dns the array reports as null is patched, not skipped"""
        module = Mock()
        module.check_mode = False
        module.params = _params(dns="d1")
        mock_get_with_context.return_value = Mock(status_code=200)

        update_server(module, Mock(), FakeServer())

        mock_get_with_context.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_detaching_an_already_detached_reference_is_no_change(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(dns="")

        update_server(module, Mock(), FakeServer())

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_update_check_mode(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = True
        module.params = _params(dns="d2")

        update_server(module, Mock(), FakeServer(dns=[_ref("d1")]))

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestRenameServer:
    """Test cases for rename_server"""

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_rename_success(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = False
        module.params = _params(rename="filesvr2")
        # The target does not exist, then the patch succeeds
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[]),
            Mock(status_code=200),
        ]

        rename_server(module, Mock())

        assert mock_get_with_context.call_args_list[1][0][1] == "patch_servers"
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_rename_onto_existing_name_fails(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(rename="filesvr2")
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[FakeServer(name="filesvr2")]
        )

        try:
            rename_server(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "already exists" in module.fail_json.call_args[1]["msg"]


class TestDeleteServer:
    """Test cases for delete_server"""

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_delete_without_cascade(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = False
        module.params = _params(state="absent")
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_server(module, Mock())

        call = mock_get_with_context.call_args
        assert call[0][1] == "delete_servers"
        assert "cascade_delete" not in call[1]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_delete_passes_cascade_resource_types(
        self, mock_get_with_context, mock_check_response
    ):
        """cascade_delete carries resource types, not a flag"""
        module = Mock()
        module.check_mode = False
        module.params = _params(state="absent", cascade_delete=["directory-services"])
        mock_get_with_context.return_value = Mock(status_code=200)

        delete_server(module, Mock())

        call = mock_get_with_context.call_args
        assert call[1]["cascade_delete"] == ["directory-services"]

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_delete_check_mode(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = True
        module.params = _params(state="absent")

        delete_server(module, Mock())

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestNetworkInterfaces:
    """Attaching network interfaces to a file server

    A network interface names the servers it is attached to, so the module
    reads the interfaces and writes attached_servers on each one.
    """

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_reads_the_interfaces_pointing_at_this_server(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.params = _params()
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[
                _interface("filevif2", attached_to="filesvr1"),
                _interface("filevif1", attached_to="filesvr1"),
                _interface("filevif3", attached_to="othersvr"),
                _interface("ct0.eth0"),
            ],
        )

        found = _attached_interfaces(module, Mock(), "filesvr1")

        assert found == ["filevif1", "filevif2"]

    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_omitting_the_option_touches_nothing(
        self, mock_get_with_context, mock_check_response
    ):
        """A task that says nothing about networking must not detach anything"""
        module = Mock()
        module.check_mode = False
        module.params = _params()

        assert _reconcile_interfaces(module, Mock(), "filesvr1") is False
        mock_get_with_context.assert_not_called()

    @patch("plugins.modules.purefa_server.NetworkInterfacePatch")
    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_attaches_what_is_missing(
        self, mock_get_with_context, mock_check_response, mock_patch_model
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(network_interfaces=["filevif1", "filevif2"])
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[_interface("filevif1", "filesvr1")]),
            Mock(status_code=200),
        ]

        assert _reconcile_interfaces(module, Mock(), "filesvr1") is True

        # Only the missing one is patched
        patch_call = mock_get_with_context.call_args_list[1]
        assert patch_call[0][1] == "patch_network_interfaces"
        assert patch_call[1]["names"] == ["filevif2"]

    @patch("plugins.modules.purefa_server.NetworkInterfacePatch")
    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_detaches_what_is_no_longer_listed(
        self, mock_get_with_context, mock_check_response, mock_patch_model
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(network_interfaces=[])
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[_interface("filevif1", "filesvr1")]),
            Mock(status_code=200),
        ]

        assert _reconcile_interfaces(module, Mock(), "filesvr1") is True

        mock_patch_model.assert_called_once_with(attached_servers=[])

    @patch("plugins.modules.purefa_server.NetworkInterfacePatch")
    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_already_attached_is_no_change(
        self, mock_get_with_context, mock_check_response, mock_patch_model
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(network_interfaces=["filevif1"])
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[_interface("filevif1", "filesvr1")]
        )

        assert _reconcile_interfaces(module, Mock(), "filesvr1") is False
        mock_patch_model.assert_not_called()

    @patch("plugins.modules.purefa_server.NetworkInterfacePatch")
    @patch("plugins.modules.purefa_server.check_response")
    @patch("plugins.modules.purefa_server.get_with_context")
    def test_check_mode_reports_but_does_not_patch(
        self, mock_get_with_context, mock_check_response, mock_patch_model
    ):
        module = Mock()
        module.check_mode = True
        module.params = _params(network_interfaces=["filevif1"])
        mock_get_with_context.return_value = Mock(status_code=200, items=[])

        assert _reconcile_interfaces(module, Mock(), "filesvr1") is True
        mock_patch_model.assert_not_called()


class TestMain:
    """Test cases for main"""

    @patch("plugins.modules.purefa_server.get_array")
    @patch("plugins.modules.purefa_server.AnsibleModule")
    @patch("plugins.modules.purefa_server.HAS_PURESTORAGE", False)
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

    @patch("plugins.modules.purefa_server.get_array")
    @patch("plugins.modules.purefa_server.AnsibleModule")
    @patch("plugins.modules.purefa_server.HAS_PURESTORAGE", True)
    def test_main_refuses_clearing_local_directory_service(
        self, mock_ansible_module, mock_get_array
    ):
        """The API documents no way to detach a local directory service"""
        module = Mock()
        module.params = _params(local_directory_service="")
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = module

        try:
            main()
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "empty string" in module.fail_json.call_args[1]["msg"]
        # Refused before the array is contacted
        mock_get_array.assert_not_called()

    @patch("plugins.modules.purefa_server.get_with_context")
    @patch("plugins.modules.purefa_server.check_api_version")
    @patch("plugins.modules.purefa_server.get_array")
    @patch("plugins.modules.purefa_server.AnsibleModule")
    @patch("plugins.modules.purefa_server.HAS_PURESTORAGE", True)
    def test_main_checks_the_api_version(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_api_version,
        mock_get_with_context,
    ):
        """File servers need REST 2.44, and the guard runs before any work"""
        module = Mock()
        module.check_mode = False
        module.params = _params()
        mock_ansible_module.return_value = module
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[FakeServer(name="filesvr1")]
        )

        main()

        mock_check_api_version.assert_called_once()
        args = mock_check_api_version.call_args[0]
        assert args[1] == "2.44"
        assert args[3] == "File servers"

    @patch("plugins.modules.purefa_server.get_with_context")
    @patch("plugins.modules.purefa_server.check_api_version")
    @patch("plugins.modules.purefa_server.get_array")
    @patch("plugins.modules.purefa_server.AnsibleModule")
    @patch("plugins.modules.purefa_server.HAS_PURESTORAGE", True)
    def test_main_absent_server_reports_no_change(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_api_version,
        mock_get_with_context,
    ):
        """Deleting a file server that is not there changes nothing"""
        module = Mock()
        module.check_mode = False
        module.params = _params(state="absent")
        mock_ansible_module.return_value = module
        mock_get_with_context.return_value = Mock(status_code=400, items=[])

        main()

        module.exit_json.assert_called_once_with(changed=False)
