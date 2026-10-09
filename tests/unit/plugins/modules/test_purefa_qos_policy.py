# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_qos_policy module."""

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

from plugins.modules.purefa_qos_policy import (
    _attached_directories,
    _build_post_kwargs,
    _read_policy,
    _reconcile_directories,
    _validate_attachable,
    _validate_directories,
    _validate_limit,
    create_policy,
    delete_policy,
    main,
    rename_policy,
    update_policy,
)


class FakePolicy:
    """Stand-in for the SDK's QoS policy model

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
    """A policies/qos/members membership as the array reports it

    The array returns PolicyMember objects, which name the managed directory
    as C(member) and the policy as C(policy).
    """

    def __init__(self, directory=None, policy=None):
        self.member = _ref(directory) if directory else None
        self.policy = _ref(policy) if policy else None


def _ref(name):
    """A reference-like object exposing a .name"""
    reference = Mock()
    reference.name = name
    return reference


def _params(**overrides):
    params = {
        "name": "qos_gold",
        "state": "present",
        "enabled": None,
        "rename": None,
        "max_total_bytes_per_sec": None,
        "max_total_ops_per_sec": None,
        "directories": None,
        "context": "",
    }
    params.update(overrides)
    return params


class TestValidateLimit:
    """Local range validation for the two aggregate limits"""

    def test_none_passes(self):
        module = Mock()
        _validate_limit(module, "max_total_bytes_per_sec", None, 1048576, 549755813888)
        module.fail_json.assert_not_called()

    def test_zero_passes_as_clear(self):
        module = Mock()
        _validate_limit(module, "max_total_ops_per_sec", 0, 100, 100000000)
        module.fail_json.assert_not_called()

    def test_in_range_passes(self):
        module = Mock()
        _validate_limit(module, "max_total_ops_per_sec", 10000, 100, 100000000)
        module.fail_json.assert_not_called()

    def test_below_minimum_fails(self):
        module = Mock()
        module.fail_json.side_effect = SystemExit("fail_json called")

        try:
            _validate_limit(module, "max_total_ops_per_sec", 1, 100, 100000000)
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "out of range" in module.fail_json.call_args[1]["msg"]

    def test_above_maximum_fails(self):
        module = Mock()
        module.fail_json.side_effect = SystemExit("fail_json called")

        try:
            _validate_limit(
                module, "max_total_bytes_per_sec", 2**60, 1048576, 549755813888
            )
        except SystemExit:
            pass

        module.fail_json.assert_called_once()


class TestValidateDirectories:
    """Local dedup validation for the directories option"""

    def test_none_stays_none(self):
        module = Mock()
        module.params = _params()
        assert _validate_directories(module) is None

    def test_sorted_and_deduplicated(self):
        module = Mock()
        module.params = _params(directories=["b", "a"])
        assert _validate_directories(module) == ["a", "b"]

    def test_empty_list_stays_empty(self):
        module = Mock()
        module.params = _params(directories=[])
        assert _validate_directories(module) == []

    def test_duplicate_fails(self):
        module = Mock()
        module.params = _params(directories=["fs1:dir1", "fs1:dir1"])
        module.fail_json.side_effect = SystemExit("fail_json called")

        try:
            _validate_directories(module)
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "duplicate" in module.fail_json.call_args[1]["msg"]


class TestReadPolicy:
    """Reading a policy by name"""

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_found_returns_the_item(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        policy = FakePolicy(name="qos_gold")
        mock_get_with_context.return_value = Mock(status_code=200, items=[policy])

        assert _read_policy(module, Mock(), "qos_gold") is policy

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_missing_returns_none(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        mock_get_with_context.return_value = Mock(status_code=400, items=[])

        assert _read_policy(module, Mock(), "qos_gold") is None


class TestAttachedDirectories:
    """Reading the managed directories a policy is attached to"""

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_lists_member_directories_sorted(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[
                FakeMembership(directory="fs1:dir2", policy="qos_gold"),
                FakeMembership(directory="fs1:dir1", policy="qos_gold"),
            ],
        )

        assert _attached_directories(module, Mock()) == ["fs1:dir1", "fs1:dir2"]
        call = mock_get_with_context.call_args
        assert call[0][1] == "get_policies_qos_members"
        assert call[1]["policy_names"] == ["qos_gold"]

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_error_reads_as_empty(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        mock_get_with_context.return_value = Mock(status_code=400, items=[])

        assert _attached_directories(module, Mock()) == []


class TestValidateAttachable:
    """Existence and conflict checks for the to-attach subset"""

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_empty_list_is_a_no_op(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        _validate_attachable(module, Mock(), [])
        mock_get_with_context.assert_not_called()

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_missing_directory_fails(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.return_value = Mock(status_code=200, items=[])

        try:
            _validate_attachable(module, Mock(), ["ghost"])
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "not found" in module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_conflict_with_a_different_policy_fails(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[_ref("fs1:dir1")]),  # directory exists
            Mock(
                status_code=200,
                items=[FakeMembership(directory="fs1:dir1", policy="other_policy")],
            ),
        ]

        try:
            _validate_attachable(module, Mock(), ["fs1:dir1"])
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "different QoS policy" in module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_no_conflict_passes(self, mock_get_with_context):
        module = Mock()
        module.params = _params()
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[_ref("fs1:dir1")]),
            Mock(status_code=200, items=[]),
        ]

        _validate_attachable(module, Mock(), ["fs1:dir1"])

        module.fail_json.assert_not_called()


class TestBuildPostKwargs:
    """Only the options the task supplied end up in the POST body"""

    def test_nothing_supplied_defaults_enabled_true(self):
        """The array requires enabled on create, so it defaults to true"""
        module = Mock()
        module.params = _params()
        assert _build_post_kwargs(module) == {"enabled": True}

    def test_supplied_limits_are_included(self):
        module = Mock()
        module.params = _params(
            max_total_bytes_per_sec=107374182400, max_total_ops_per_sec=10000
        )
        kwargs = _build_post_kwargs(module)

        assert kwargs["max_total_bytes_per_sec"] == 107374182400
        assert kwargs["max_total_ops_per_sec"] == 10000

    def test_enabled_false_is_included(self):
        """enabled False is a real request, not the same as omitting it"""
        module = Mock()
        module.params = _params(enabled=False)
        assert _build_post_kwargs(module)["enabled"] is False

    def test_zero_limit_is_included(self):
        """0 is the documented clear value, distinct from omitted"""
        module = Mock()
        module.params = _params(max_total_bytes_per_sec=0)
        assert _build_post_kwargs(module)["max_total_bytes_per_sec"] == 0


class TestCreatePolicy:
    """Test cases for create_policy"""

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.post_with_context")
    def test_creates_with_no_directories(
        self, mock_post_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(max_total_bytes_per_sec=107374182400)
        mock_post_with_context.return_value = Mock(status_code=200)

        create_policy(module, Mock())

        call = mock_post_with_context.call_args
        assert call[0][1] == "post_policies_qos"
        assert call[1]["names"] == ["qos_gold"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_check_mode_makes_no_write(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = True
        module.params = _params()

        create_policy(module, Mock())

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.post_with_context")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_create_with_directories_validates_then_attaches(
        self, mock_get_with_context, mock_post_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(directories=["fs1:dir1"])
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[_ref("fs1:dir1")]),  # directory exists
            Mock(status_code=200, items=[]),  # no conflicting policy
        ]
        mock_post_with_context.side_effect = [
            Mock(status_code=200),  # create
            Mock(status_code=200),  # attach
        ]

        create_policy(module, Mock())

        reads = [c[0][1] for c in mock_get_with_context.call_args_list]
        writes = [c[0][1] for c in mock_post_with_context.call_args_list]
        assert reads == ["get_directories", "get_policies_qos_members"]
        assert writes == ["post_policies_qos", "post_policies_qos_members"]
        module.exit_json.assert_called_once_with(changed=True)


class TestUpdatePolicy:
    """Test cases for update_policy"""

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_matching_settings_report_no_change(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(enabled=True, max_total_bytes_per_sec=1048576)
        policy = FakePolicy(enabled=True, max_total_bytes_per_sec=1048576)

        update_policy(module, Mock(), policy)

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.patch_with_context")
    def test_bandwidth_change_is_patched(
        self, mock_patch_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(max_total_bytes_per_sec=2097152)
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_policy(module, Mock(), FakePolicy(max_total_bytes_per_sec=1048576))

        call = mock_patch_with_context.call_args
        assert call[0][1] == "patch_policies_qos"
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.patch_with_context")
    def test_disabling_an_enabled_policy_is_patched(
        self, mock_patch_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(enabled=False)
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_policy(module, Mock(), FakePolicy(enabled=True))

        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.patch_with_context")
    def test_clearing_a_limit_with_zero_is_patched(
        self, mock_patch_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(max_total_ops_per_sec=0)
        mock_patch_with_context.return_value = Mock(status_code=200)

        update_policy(module, Mock(), FakePolicy(max_total_ops_per_sec=10000))

        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_already_cleared_limit_is_idempotent(
        self, mock_get_with_context, mock_check_response
    ):
        """An already-unset limit reads back as a missing field, not 0

        A task that keeps asking to clear it (max_total_*=0) must not PATCH
        every run just because 0 != None.
        """
        module = Mock()
        module.check_mode = False
        module.params = _params(max_total_bytes_per_sec=0, max_total_ops_per_sec=0)

        update_policy(module, Mock(), FakePolicy())

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_qos_policy.PolicyQosPatch")
    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.patch_with_context")
    def test_omitting_a_field_leaves_it_alone(
        self, mock_patch_with_context, mock_check_response, mock_patch_model
    ):
        """A task that does not mention max_total_ops_per_sec must not touch it"""
        module = Mock()
        module.check_mode = False
        module.params = _params(max_total_bytes_per_sec=2097152)
        mock_patch_with_context.return_value = Mock(status_code=200)

        policy = FakePolicy(max_total_bytes_per_sec=1048576, max_total_ops_per_sec=5000)
        update_policy(module, Mock(), policy)

        kwargs = mock_patch_model.call_args.kwargs
        assert "max_total_ops_per_sec" not in kwargs
        assert kwargs["max_total_bytes_per_sec"] == 2097152

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_check_mode_reports_but_does_not_patch(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = True
        module.params = _params(max_total_bytes_per_sec=2097152)

        update_policy(module, Mock(), FakePolicy(max_total_bytes_per_sec=1048576))

        mock_get_with_context.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestRenamePolicy:
    """Test cases for rename_policy"""

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.patch_with_context")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_rename_success(
        self, mock_get_with_context, mock_patch_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(rename="qos_platinum")
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[]
        )  # target does not exist
        mock_patch_with_context.return_value = Mock(status_code=200)  # patch

        rename_policy(module, Mock())

        assert mock_patch_with_context.call_args[0][1] == "patch_policies_qos"
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_rename_onto_existing_name_fails(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(rename="qos_platinum")
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[FakePolicy(name="qos_platinum")]
        )

        try:
            rename_policy(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "already exists" in module.fail_json.call_args[1]["msg"]


class TestDeletePolicy:
    """Test cases for delete_policy"""

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.delete_with_context")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_delete_unattached_policy(
        self, mock_get_with_context, mock_delete_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(state="absent")
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[]
        )  # no attachments
        mock_delete_with_context.return_value = Mock(status_code=200)  # delete

        delete_policy(module, Mock())

        assert mock_delete_with_context.call_args[0][1] == "delete_policies_qos"
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_delete_attached_policy_fails(
        self, mock_get_with_context, mock_check_response
    ):
        """A policy still attached to a managed directory is not deleted"""
        module = Mock()
        module.check_mode = False
        module.params = _params(state="absent")
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[FakeMembership(directory="fs1:dir1", policy="qos_gold")],
        )

        try:
            delete_policy(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        msg = module.fail_json.call_args[1]["msg"]
        assert "fs1:dir1" in msg
        # Only the attachment read happened - no delete was attempted
        assert [c[0][1] for c in mock_get_with_context.call_args_list] == [
            "get_policies_qos_members"
        ]

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_delete_check_mode(self, mock_get_with_context, mock_check_response):
        module = Mock()
        module.check_mode = True
        module.params = _params(state="absent")
        mock_get_with_context.return_value = Mock(status_code=200, items=[])

        delete_policy(module, Mock())

        assert [c[0][1] for c in mock_get_with_context.call_args_list] == [
            "get_policies_qos_members"
        ]
        module.exit_json.assert_called_once_with(changed=True)


class TestReconcileDirectories:
    """Attaching and detaching the policy's managed directories"""

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_omitting_the_option_touches_nothing(self, mock_get_with_context):
        module = Mock()
        module.check_mode = False
        module.params = _params()

        assert _reconcile_directories(module, Mock()) is False
        mock_get_with_context.assert_not_called()

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.post_with_context")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_attaches_what_is_missing(
        self, mock_get_with_context, mock_post_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(directories=["fs1:dir1", "fs1:dir2"])
        mock_get_with_context.side_effect = [
            Mock(
                status_code=200,
                items=[FakeMembership(directory="fs1:dir1", policy="qos_gold")],
            ),
            Mock(status_code=200, items=[_ref("fs1:dir2")]),  # dir2 exists
            Mock(status_code=200, items=[]),  # dir2 has no policy
        ]
        mock_post_with_context.return_value = Mock(status_code=200)  # attach dir2

        assert _reconcile_directories(module, Mock()) is True

        attach = mock_post_with_context.call_args_list[-1]
        assert attach[0][1] == "post_policies_qos_members"
        assert attach[1]["policy_names"] == ["qos_gold"]

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.delete_with_context")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_detaches_what_is_no_longer_listed(
        self, mock_get_with_context, mock_delete_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = False
        module.params = _params(directories=[])
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[FakeMembership(directory="fs1:dir1", policy="qos_gold")],
        )
        mock_delete_with_context.return_value = Mock(status_code=200)  # detach dir1

        assert _reconcile_directories(module, Mock()) is True

        detach = mock_delete_with_context.call_args_list[-1]
        assert detach[0][1] == "delete_policies_qos_members"
        assert detach[1]["member_names"] == ["fs1:dir1"]
        assert detach[1]["member_types"] == ["directories"]

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_already_attached_is_no_change(self, mock_get_with_context):
        module = Mock()
        module.check_mode = False
        module.params = _params(directories=["fs1:dir1"])
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[FakeMembership(directory="fs1:dir1", policy="qos_gold")],
        )

        assert _reconcile_directories(module, Mock()) is False

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_missing_directory_fails(self, mock_get_with_context):
        module = Mock()
        module.check_mode = False
        module.params = _params(directories=["ghost"])
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[]),  # not attached
            Mock(status_code=200, items=[]),  # get_directories finds nothing
        ]

        try:
            _reconcile_directories(module, Mock())
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        assert "not found" in module.fail_json.call_args[1]["msg"]

    @patch("plugins.modules.purefa_qos_policy.check_response")
    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    def test_check_mode_reports_but_does_not_write(
        self, mock_get_with_context, mock_check_response
    ):
        module = Mock()
        module.check_mode = True
        module.params = _params(directories=["fs1:dir1"])
        mock_get_with_context.side_effect = [
            Mock(status_code=200, items=[]),  # not attached
            Mock(status_code=200, items=[_ref("fs1:dir1")]),  # dir1 exists
            Mock(status_code=200, items=[]),  # dir1 has no policy
        ]

        assert _reconcile_directories(module, Mock()) is True

        methods = [c[0][1] for c in mock_get_with_context.call_args_list]
        assert "post_policies_qos_members" not in methods


class TestMain:
    """Test cases for main"""

    @patch("plugins.modules.purefa_qos_policy.get_array")
    @patch("plugins.modules.purefa_qos_policy.AnsibleModule")
    @patch("plugins.modules.purefa_qos_policy.HAS_PURESTORAGE", False)
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

    @patch("plugins.modules.purefa_qos_policy.get_array")
    @patch("plugins.modules.purefa_qos_policy.AnsibleModule")
    @patch("plugins.modules.purefa_qos_policy.HAS_PURESTORAGE", True)
    def test_main_out_of_range_limit_fails_before_array(
        self, mock_ansible_module, mock_get_array
    ):
        module = Mock()
        module.params = _params(max_total_ops_per_sec=1)
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_ansible_module.return_value = module

        try:
            main()
        except SystemExit:
            pass

        module.fail_json.assert_called_once()
        mock_get_array.assert_not_called()

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    @patch("plugins.modules.purefa_qos_policy.check_api_version")
    @patch("plugins.modules.purefa_qos_policy.get_array")
    @patch("plugins.modules.purefa_qos_policy.AnsibleModule")
    @patch("plugins.modules.purefa_qos_policy.HAS_PURESTORAGE", True)
    def test_main_checks_the_api_version(
        self,
        mock_ansible_module,
        mock_get_array,
        mock_check_api_version,
        mock_get_with_context,
    ):
        """QoS policies need REST 2.54, and the guard runs before any work"""
        module = Mock()
        module.check_mode = False
        module.params = _params()
        mock_ansible_module.return_value = module
        mock_get_with_context.return_value = Mock(
            status_code=200, items=[FakePolicy(name="qos_gold")]
        )

        main()

        mock_check_api_version.assert_called_once()
        args = mock_check_api_version.call_args[0]
        assert args[1] == "2.54"
        assert args[3] == "QoS policies"

    @patch("plugins.modules.purefa_qos_policy.get_with_context")
    @patch("plugins.modules.purefa_qos_policy.check_api_version")
    @patch("plugins.modules.purefa_qos_policy.get_array")
    @patch("plugins.modules.purefa_qos_policy.AnsibleModule")
    @patch("plugins.modules.purefa_qos_policy.HAS_PURESTORAGE", True)
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
