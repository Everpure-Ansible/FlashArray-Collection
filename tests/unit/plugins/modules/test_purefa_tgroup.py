# Copyright: (c) 2026, Everpure Ansible Team
# <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_tgroup module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch, MagicMock
from packaging.version import Version as LooseVersion

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
mock_version_module = MagicMock()
mock_version_module.LooseVersion = LooseVersion
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    mock_version_module
)
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers"
] = MagicMock()

from plugins.modules.purefa_tgroup import (
    _build_members_payload,
    create_tgroup,
    get_tgroup,
    main,
    rename_exists,
    update_tgroup,
    validate_inputs,
)


def _member(resource_type, name):
    return SimpleNamespace(
        member=SimpleNamespace(resource_type=resource_type, name=name),
        topology_group=SimpleNamespace(name="app-stack"),
        status="healthy",
        status_details=None,
    )


class TestMemberPayloads:
    @patch("plugins.modules.purefa_tgroup.TgroupMembersPost")
    @patch("plugins.modules.purefa_tgroup.TgroupMembersPostMember")
    @patch("plugins.modules.purefa_tgroup.ReferenceWithType")
    def test_build_members_payload_uses_remote_array_resource_type(
        self,
        mock_reference_with_type,
        mock_tgroup_member_post_member,
        mock_tgroup_members_post,
    ):
        _build_members_payload(["array-a"], ["child-a"])

        assert mock_reference_with_type.call_args_list[0][1] == {
            "name": "array-a",
            "resource_type": "remote-arrays",
        }
        assert mock_reference_with_type.call_args_list[1][1] == {
            "name": "child-a",
            "resource_type": "topology-groups",
        }
        mock_tgroup_member_post_member.assert_called()
        mock_tgroup_members_post.assert_called_once()


class TestValidateInputs:
    @patch("plugins.modules.purefa_tgroup.get_tgroup", return_value=None)
    def test_validate_inputs_self_parent_fails(self, _mock_get_tgroup):
        mock_module = Mock()
        mock_module.params = {
            "name": "app-stack",
            "rename": None,
            "parent": "app-stack",
            "tgroup": [],
            "array": [],
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        try:
            validate_inputs(mock_module, Mock())
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()

    @patch("plugins.modules.purefa_tgroup.get_with_context")
    def test_validate_inputs_missing_child_tgroup_fails(self, mock_get_with_context):
        mock_module = Mock()
        mock_module.params = {
            "name": "app-stack",
            "rename": None,
            "parent": None,
            "tgroup": ["child-a", "missing-child"],
            "array": [],
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[SimpleNamespace(name="child-a")],
        )

        try:
            validate_inputs(mock_module, Mock())
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        assert "missing-child" in mock_module.fail_json.call_args[1]["msg"]

    def test_validate_inputs_missing_array_fails(self):
        mock_module = Mock()
        mock_module.params = {
            "name": "app-stack",
            "rename": None,
            "parent": None,
            "tgroup": [],
            "array": ["array-a", "missing-array"],
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_array = Mock()
        mock_array.get_remote_arrays.return_value = Mock(
            status_code=200,
            items=[SimpleNamespace(name="array-a")],
        )

        try:
            validate_inputs(mock_module, mock_array)
        except SystemExit:
            pass

        mock_array.get_remote_arrays.assert_called_once_with(current_fleet_only=True)
        mock_module.fail_json.assert_called_once()
        assert "missing-array" in mock_module.fail_json.call_args[1]["msg"]


class TestLookups:
    @patch("plugins.modules.purefa_tgroup.get_with_context")
    def test_get_tgroup_returns_none_for_empty_items(self, mock_get_with_context):
        mock_module = Mock()
        mock_module.params = {"name": "missing-tg", "context": ""}
        mock_get_with_context.return_value = Mock(status_code=200, items=[])

        assert get_tgroup(mock_module, Mock()) is None

    @patch("plugins.modules.purefa_tgroup.get_with_context")
    def test_rename_exists_false_for_empty_items(self, mock_get_with_context):
        mock_module = Mock()
        mock_module.params = {"rename": "missing-tg", "context": ""}
        mock_get_with_context.return_value = Mock(status_code=200, items=[])

        assert rename_exists(mock_module, Mock()) is False

    @patch("plugins.modules.purefa_tgroup.get_with_context")
    def test_rename_exists_true_when_item_returned(self, mock_get_with_context):
        mock_module = Mock()
        mock_module.params = {"rename": "existing-tg", "context": ""}
        mock_get_with_context.return_value = Mock(
            status_code=200,
            items=[SimpleNamespace(name="existing-tg")],
        )

        assert rename_exists(mock_module, Mock()) is True


class TestCreateTgroup:
    @patch("plugins.modules.purefa_tgroup.add_members")
    @patch("plugins.modules.purefa_tgroup.check_response")
    @patch("plugins.modules.purefa_tgroup.post_with_context")
    def test_create_tgroup_with_parent_and_members(
        self,
        mock_post_with_context,
        _mock_check_response,
        mock_add_members,
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "app-stack",
            "rename": None,
            "parent": "parent-stack",
            "array": ["array-a"],
            "tgroup": ["child-a"],
        }
        mock_array = Mock()

        create_tgroup(mock_module, mock_array)

        mock_post_with_context.assert_called_once()
        assert mock_post_with_context.call_args[1]["names"] == ["app-stack"]
        assert mock_post_with_context.call_args[1]["parent_topology_group_names"] == [
            "parent-stack"
        ]
        mock_add_members.assert_called_once_with(
            mock_module,
            mock_array,
            "app-stack",
            ["array-a"],
            ["child-a"],
        )
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestUpdateTgroup:
    @patch("plugins.modules.purefa_tgroup.add_members")
    @patch("plugins.modules.purefa_tgroup.check_response")
    @patch("plugins.modules.purefa_tgroup.patch_with_context")
    @patch("plugins.modules.purefa_tgroup.rename_exists", return_value=False)
    def test_update_tgroup_rename_move_and_add_members(
        self,
        _mock_rename_exists,
        mock_patch_with_context,
        _mock_check_response,
        mock_add_members,
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "app-stack",
            "state": "present",
            "rename": "app-stack-qa",
            "parent": "parent-stack",
            "array": ["array-a"],
            "tgroup": ["child-a"],
        }
        mock_array = Mock()
        current_tgroup = SimpleNamespace(
            name="app-stack",
            parent_topology_group=SimpleNamespace(name=None),
        )

        update_tgroup(mock_module, mock_array, current_tgroup, [])

        assert mock_patch_with_context.call_count == 2
        assert mock_patch_with_context.call_args_list[0][1]["names"] == ["app-stack"]
        assert mock_patch_with_context.call_args_list[1][1]["names"] == ["app-stack-qa"]
        assert "topology_group" in mock_patch_with_context.call_args_list[1][1]
        assert mock_patch_with_context.call_args_list[1][1][
            "to_parent_topology_group_names"
        ] == ["parent-stack"]
        mock_add_members.assert_called_once_with(
            mock_module,
            mock_array,
            "app-stack-qa",
            ["array-a"],
            ["child-a"],
        )
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tgroup.add_members")
    @patch("plugins.modules.purefa_tgroup.check_response")
    @patch("plugins.modules.purefa_tgroup.patch_with_context")
    def test_update_tgroup_move_only_includes_topology_group_body(
        self,
        mock_patch_with_context,
        _mock_check_response,
        mock_add_members,
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "app-stack",
            "state": "present",
            "rename": None,
            "parent": "parent-stack",
            "array": [],
            "tgroup": [],
        }
        mock_array = Mock()
        current_tgroup = SimpleNamespace(
            name="app-stack",
            parent_topology_group=SimpleNamespace(name=None),
        )

        update_tgroup(mock_module, mock_array, current_tgroup, [])

        mock_patch_with_context.assert_called_once()
        assert mock_patch_with_context.call_args[1]["names"] == ["app-stack"]
        assert "topology_group" in mock_patch_with_context.call_args[1]
        assert mock_patch_with_context.call_args[1][
            "to_parent_topology_group_names"
        ] == ["parent-stack"]
        mock_add_members.assert_not_called()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tgroup.remove_members")
    def test_update_tgroup_absent_removes_only_existing_members(
        self, mock_remove_members
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {
            "name": "app-stack",
            "state": "absent",
            "rename": None,
            "parent": None,
            "array": ["array-b", "array-c"],
            "tgroup": ["child-a"],
        }
        mock_array = Mock()
        current_tgroup = SimpleNamespace(
            name="app-stack",
            parent_topology_group=None,
        )
        current_members = [
            _member("remote-arrays", "array-a"),
            _member("remote-arrays", "array-b"),
            _member("topology-groups", "child-a"),
        ]

        update_tgroup(mock_module, mock_array, current_tgroup, current_members)

        mock_remove_members.assert_called_once_with(
            mock_module,
            mock_array,
            "app-stack",
            ["array-b", "child-a"],
        )
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    @patch("plugins.modules.purefa_tgroup.validate_inputs")
    @patch("plugins.modules.purefa_tgroup.get_tgroup_members")
    @patch("plugins.modules.purefa_tgroup.get_tgroup")
    @patch("plugins.modules.purefa_tgroup.check_api_version")
    @patch("plugins.modules.purefa_tgroup.get_array")
    @patch("plugins.modules.purefa_tgroup.AnsibleModule")
    def test_main_absent_missing_group_is_unchanged(
        self,
        mock_ansible_module,
        mock_get_array,
        _mock_check_api_version,
        mock_get_tgroup,
        mock_get_tgroup_members,
        mock_validate_inputs,
    ):
        mock_module = Mock()
        mock_module.params = {
            "name": "missing-tg",
            "state": "absent",
            "rename": None,
            "parent": None,
            "array": [],
            "tgroup": [],
            "context": "",
        }
        mock_module.exit_json.side_effect = SystemExit(0)
        mock_ansible_module.return_value = mock_module

        mock_array = Mock()
        mock_array.get_rest_version.return_value = "2.54"
        mock_get_array.return_value = mock_array
        mock_get_tgroup.return_value = None

        try:
            main()
        except SystemExit:
            pass

        mock_get_tgroup_members.assert_not_called()
        mock_validate_inputs.assert_called_once_with(
            mock_module,
            mock_array,
            None,
            [],
        )
        mock_module.exit_json.assert_called_once_with(changed=False)
