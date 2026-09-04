# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_localuser module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock, patch

import pytest

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

from plugins.modules.purefa_localuser import (
    read_user,
    read_memberships,
    create_user,
    update_user,
    rename_user,
    check_renamed_user,
    delete_user,
    _scope,
    _plain_changes,
    _reconcile_groups,
    _reconcile_primary_group,
)


def make_module(**params):
    """An AnsibleModule stand-in whose fail_json raises, as the real one does"""
    module = Mock()
    module.check_mode = False
    base = {
        "name": "fred",
        "local_directory_service": "lds1",
        "password": None,
        "update_password": "on_create",
        "primary_group": None,
        "groups": None,
        "uid": None,
        "email": None,
        "enabled": None,
        "rename": None,
        "state": "present",
        "context": "",
    }
    base.update(params)
    module.params = base
    module.fail_json.side_effect = SystemExit(1)
    return module


def make_user(
    name="fred",
    uid=71000,
    email="a@example.com",
    enabled=True,
    primary="users",
    built_in=False,
):
    user = Mock()
    user.name = name
    user.uid = uid
    user.email = email
    user.enabled = enabled
    user.built_in = built_in
    group = Mock()
    group.name = primary
    user.primary_group = group
    return user


def membership_row(group, is_primary):
    row = Mock()
    ref = Mock()
    ref.name = group
    row.group = ref
    row.is_primary_group = is_primary
    return row


class TestReadUser:
    """Test cases for read_user function"""

    @patch("plugins.modules.purefa_localuser.get_with_context")
    def test_read_user_scopes_by_directory_service(self, mock_get):
        """Test read_user narrows the lookup to one local directory service"""
        module = make_module()
        user = make_user()
        mock_get.return_value = Mock(status_code=200, items=[user])

        assert read_user(module, Mock(), "fred") is user
        kwargs = mock_get.call_args[1]
        assert kwargs["names"] == ["fred"]
        assert kwargs["filter"] == "local_directory_service.name='lds1'"

    @patch("plugins.modules.purefa_localuser.get_with_context")
    def test_read_user_absent_is_400_not_404(self, mock_get):
        """Test anything other than 200 counts as absent"""
        module = make_module()
        mock_get.return_value = Mock(status_code=400)

        assert read_user(module, Mock(), "nope") is None


class TestReadMemberships:
    """Test cases for read_memberships function"""

    @patch("plugins.modules.purefa_localuser.get_with_context")
    def test_read_memberships_maps_group_to_primary_flag(self, mock_get):
        """Test memberships come back as {group: is primary}"""
        module = make_module()
        mock_get.return_value = Mock(
            status_code=200,
            items=[membership_row("users", True), membership_row("backup", False)],
        )

        assert read_memberships(module, Mock(), "fred") == {
            "users": True,
            "backup": False,
        }

    @patch("plugins.modules.purefa_localuser.get_with_context")
    def test_read_memberships_filters_by_user_and_service(self, mock_get):
        """Test the filter names both the user and the service"""
        module = make_module()
        mock_get.return_value = Mock(status_code=200, items=[])

        read_memberships(module, Mock(), "fred")

        assert mock_get.call_args[1]["filter"] == (
            "member.name='fred' and local_directory_service.name='lds1'"
        )

    @patch("plugins.modules.purefa_localuser.get_with_context")
    def test_read_memberships_absent(self, mock_get):
        """Test a failed read is an empty mapping, not an error"""
        module = make_module()
        mock_get.return_value = Mock(status_code=400)

        assert read_memberships(module, Mock(), "fred") == {}


class TestHelpers:
    """Test cases for the scoping and diff helpers"""

    def test_scope_names_the_directory_service(self):
        module = make_module()

        assert _scope(module) == {"local_directory_service_names": ["lds1"]}

    def test_plain_changes_ignores_omitted_options(self):
        """Test an option the play leaves out is never a change"""
        module = make_module()

        assert _plain_changes(module, make_user()) == {}

    def test_plain_changes_ignores_matching_values(self):
        module = make_module(uid=71000, email="a@example.com", enabled=True)

        assert _plain_changes(module, make_user()) == {}

    def test_plain_changes_collects_differences(self):
        module = make_module(uid=71000, email="new@example.com", enabled=False)

        assert _plain_changes(module, make_user()) == {
            "email": "new@example.com",
            "enabled": False,
        }

    def test_plain_changes_handles_enabled_false(self):
        """Test enabled=False is a change, not treated as unset"""
        module = make_module(enabled=False)

        assert _plain_changes(module, make_user(enabled=True)) == {"enabled": False}


class TestReconcileGroups:
    """Test cases for _reconcile_groups function"""

    @patch("plugins.modules.purefa_localuser._leave_group")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_omitted_groups_leaves_membership_alone(self, mock_join, mock_leave):
        """Test omitting the option is not a change"""
        module = make_module()
        memberships = {"users": True, "backup": False}

        assert _reconcile_groups(module, Mock(), make_user(), memberships) is False
        mock_join.assert_not_called()
        mock_leave.assert_not_called()

    @patch("plugins.modules.purefa_localuser._leave_group")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_matching_groups_is_no_change(self, mock_join, mock_leave):
        module = make_module(groups=["backup"])
        memberships = {"users": True, "backup": False}

        assert _reconcile_groups(module, Mock(), make_user(), memberships) is False
        mock_join.assert_not_called()
        mock_leave.assert_not_called()

    @patch("plugins.modules.purefa_localuser._leave_group")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_groups_are_added_and_removed(self, mock_join, mock_leave):
        """Test the list is declarative in both directions"""
        module = make_module(groups=["reporting"])
        memberships = {"users": True, "backup": False}
        array = Mock()

        assert _reconcile_groups(module, array, make_user(), memberships) is True
        mock_join.assert_called_once_with(module, array, "reporting")
        mock_leave.assert_called_once_with(module, array, "backup")

    @patch("plugins.modules.purefa_localuser._leave_group")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_empty_list_clears_the_extras_only(self, mock_join, mock_leave):
        """Test an empty list removes secondaries but never the primary

        The array refuses to remove the primary group's membership, so it must
        never be in the removal set.
        """
        module = make_module(groups=[])
        memberships = {"users": True, "backup": False}
        array = Mock()

        assert _reconcile_groups(module, array, make_user(), memberships) is True
        mock_join.assert_not_called()
        mock_leave.assert_called_once_with(module, array, "backup")

    @patch("plugins.modules.purefa_localuser._leave_group")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_primary_group_listed_is_ignored(self, mock_join, mock_leave):
        """Test naming the primary group in the list is not a change"""
        module = make_module(groups=["users"])
        memberships = {"users": True}

        assert _reconcile_groups(module, Mock(), make_user(), memberships) is False
        mock_join.assert_not_called()
        mock_leave.assert_not_called()

    @patch("plugins.modules.purefa_localuser._leave_group")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_check_mode_reports_without_acting(self, mock_join, mock_leave):
        module = make_module(groups=["reporting"])
        module.check_mode = True
        memberships = {"users": True}

        assert _reconcile_groups(module, Mock(), make_user(), memberships) is True
        mock_join.assert_not_called()
        mock_leave.assert_not_called()


class TestReconcilePrimaryGroup:
    """Test cases for _reconcile_primary_group function"""

    @patch("plugins.modules.purefa_localuser._patch_user")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_no_primary_group_requested(self, mock_join, mock_patch):
        module = make_module()

        assert _reconcile_primary_group(module, Mock(), make_user(), {}) is False
        mock_patch.assert_not_called()

    @patch("plugins.modules.purefa_localuser._patch_user")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_primary_group_already_correct(self, mock_join, mock_patch):
        module = make_module(primary_group="users")

        assert (
            _reconcile_primary_group(
                module, Mock(), make_user(primary="users"), {"users": True}
            )
            is False
        )
        mock_patch.assert_not_called()

    @patch("plugins.modules.purefa_localuser._patch_user")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_primary_group_joined_first_when_not_a_member(self, mock_join, mock_patch):
        """Test the group is joined before being made primary

        The array refuses a primary group the user does not belong to.
        """
        module = make_module(primary_group="backup")
        array = Mock()

        assert (
            _reconcile_primary_group(
                module, array, make_user(primary="users"), {"users": True}
            )
            is True
        )
        mock_join.assert_called_once_with(module, array, "backup")
        mock_patch.assert_called_once()

    @patch("plugins.modules.purefa_localuser._patch_user")
    @patch("plugins.modules.purefa_localuser._join_group")
    def test_primary_group_not_rejoined_when_already_a_member(
        self, mock_join, mock_patch
    ):
        module = make_module(primary_group="backup")
        array = Mock()

        assert (
            _reconcile_primary_group(
                module,
                array,
                make_user(primary="users"),
                {"users": True, "backup": False},
            )
            is True
        )
        mock_join.assert_not_called()
        mock_patch.assert_called_once()


class TestCreateUser:
    """Test cases for create_user function"""

    @patch("plugins.modules.purefa_localuser.post_with_context")
    def test_create_user_requires_password(self, mock_post):
        """Test the missing option is named rather than left to the array"""
        module = make_module(primary_group="users")

        with pytest.raises(SystemExit):
            create_user(module, Mock())

        assert "password is required" in module.fail_json.call_args[1]["msg"]
        mock_post.assert_not_called()

    @patch("plugins.modules.purefa_localuser.post_with_context")
    def test_create_user_requires_primary_group(self, mock_post):
        module = make_module(password="secret")

        with pytest.raises(SystemExit):
            create_user(module, Mock())

        assert "primary_group is required" in module.fail_json.call_args[1]["msg"]
        mock_post.assert_not_called()

    def test_create_user_check_mode(self):
        module = make_module(password="secret", primary_group="users")
        module.check_mode = True

        create_user(module, Mock())

        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localuser._join_group")
    @patch("plugins.modules.purefa_localuser.check_response")
    @patch("plugins.modules.purefa_localuser.post_with_context")
    def test_create_user_scoped(self, mock_post, mock_check, mock_join):
        module = make_module(password="secret", primary_group="users")
        mock_post.return_value = Mock(status_code=200)

        create_user(module, Mock())

        kwargs = mock_post.call_args[1]
        assert kwargs["names"] == ["fred"]
        assert kwargs["local_directory_service_names"] == ["lds1"]
        mock_join.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localuser._join_group")
    @patch("plugins.modules.purefa_localuser.check_response")
    @patch("plugins.modules.purefa_localuser.post_with_context")
    def test_create_user_joins_extra_groups(self, mock_post, mock_check, mock_join):
        """Test extra groups are joined after the user exists"""
        module = make_module(
            password="secret", primary_group="users", groups=["backup", "users"]
        )
        array = Mock()
        mock_post.return_value = Mock(status_code=200)

        create_user(module, array)

        # the primary group is already a membership and is not joined again
        mock_join.assert_called_once_with(module, array, "backup")


class TestUpdateUser:
    """Test cases for update_user function"""

    @patch("plugins.modules.purefa_localuser.read_memberships")
    @patch("plugins.modules.purefa_localuser._patch_user")
    def test_update_user_nothing_requested(self, mock_patch, mock_members):
        """Test naming the user alone reports no change"""
        module = make_module()
        mock_members.return_value = {"users": True}

        update_user(module, Mock(), make_user())

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_localuser.read_memberships")
    @patch("plugins.modules.purefa_localuser._patch_user")
    def test_update_user_patches_plain_settings(self, mock_patch, mock_members):
        module = make_module(email="new@example.com")
        mock_members.return_value = {"users": True}

        update_user(module, Mock(), make_user())

        mock_patch.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localuser.read_memberships")
    @patch("plugins.modules.purefa_localuser._patch_user")
    def test_update_user_password_not_reset_by_default(self, mock_patch, mock_members):
        """Test update_password on_create leaves an existing password alone

        This is what keeps a task that carries a password idempotent.
        """
        module = make_module(password="secret")
        mock_members.return_value = {"users": True}

        update_user(module, Mock(), make_user())

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_localuser.read_memberships")
    @patch("plugins.modules.purefa_localuser._patch_user")
    def test_update_user_password_reset_when_always(self, mock_patch, mock_members):
        """Test update_password always resets and reports a change every run"""
        module = make_module(password="secret", update_password="always")
        mock_members.return_value = {"users": True}

        update_user(module, Mock(), make_user())

        mock_patch.assert_called_once()
        assert mock_patch.call_args[1] == {"password": "secret"}
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localuser.read_memberships")
    @patch("plugins.modules.purefa_localuser._patch_user")
    def test_update_user_password_always_needs_a_password(
        self, mock_patch, mock_members
    ):
        """Test update_password always with no password is not a change"""
        module = make_module(update_password="always")
        mock_members.return_value = {"users": True}

        update_user(module, Mock(), make_user())

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)


class TestRenameUser:
    """Test cases for rename_user function"""

    @patch("plugins.modules.purefa_localuser._patch_user")
    @patch("plugins.modules.purefa_localuser.read_user")
    def test_rename_user_success(self, mock_read, mock_patch):
        """Test the rename passes the new name as a field, not positionally"""
        module = make_module(rename="freddy")
        mock_read.return_value = None
        array = Mock()

        rename_user(module, array)

        mock_patch.assert_called_once_with(module, array, "fred", name="freddy")
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localuser._patch_user")
    @patch("plugins.modules.purefa_localuser.read_user")
    def test_rename_user_target_exists_fails(self, mock_read, mock_patch):
        module = make_module(rename="freddy")
        mock_read.return_value = make_user(name="freddy")

        with pytest.raises(SystemExit):
            rename_user(module, Mock())

        assert "already exists" in module.fail_json.call_args[1]["msg"]
        mock_patch.assert_not_called()

    @patch("plugins.modules.purefa_localuser._patch_user")
    @patch("plugins.modules.purefa_localuser.read_user")
    def test_rename_user_check_mode(self, mock_read, mock_patch):
        module = make_module(rename="freddy")
        module.check_mode = True
        mock_read.return_value = None

        rename_user(module, Mock())

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestCheckRenamedUser:
    """Test cases for check_renamed_user, the second run of a rename"""

    @patch("plugins.modules.purefa_localuser.read_user")
    def test_already_renamed(self, mock_read):
        module = make_module(rename="freddy")
        mock_read.return_value = make_user(name="freddy")

        check_renamed_user(module, Mock())

        module.exit_json.assert_called_once_with(changed=False)
        module.fail_json.assert_not_called()

    @patch("plugins.modules.purefa_localuser.read_user")
    def test_neither_exists_fails(self, mock_read):
        module = make_module(rename="freddy")
        mock_read.return_value = None

        with pytest.raises(SystemExit):
            check_renamed_user(module, Mock())

        assert "not found to rename" in module.fail_json.call_args[1]["msg"]
        module.exit_json.assert_not_called()


class TestDeleteUser:
    """Test cases for delete_user function"""

    @patch("plugins.modules.purefa_localuser.check_response")
    @patch("plugins.modules.purefa_localuser.delete_with_context")
    def test_delete_user_scoped(self, mock_delete, mock_check):
        module = make_module(state="absent")
        mock_delete.return_value = Mock(status_code=200)

        delete_user(module, Mock(), make_user())

        kwargs = mock_delete.call_args[1]
        assert kwargs["names"] == ["fred"]
        assert kwargs["local_directory_service_names"] == ["lds1"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localuser.delete_with_context")
    def test_delete_user_builtin_fails(self, mock_delete):
        """Test a built-in user cannot be deleted

        Unlike built-in groups, built-in users can be modified - only the
        delete is refused.
        """
        module = make_module(state="absent")

        with pytest.raises(SystemExit):
            delete_user(module, Mock(), make_user(built_in=True))

        assert "built-in" in module.fail_json.call_args[1]["msg"]
        mock_delete.assert_not_called()

    def test_delete_user_check_mode(self):
        module = make_module(state="absent")
        module.check_mode = True

        delete_user(module, Mock(), make_user())

        module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for the main dispatch"""

    @patch("plugins.modules.purefa_localuser.get_array")
    @patch("plugins.modules.purefa_localuser.AnsibleModule")
    def test_main_no_purestorage_sdk(self, mock_am, mock_ga):
        import plugins.modules.purefa_localuser as mod

        original = mod.HAS_PURESTORAGE
        mod.HAS_PURESTORAGE = False
        module = make_module()
        mock_am.return_value = module
        try:
            with pytest.raises(SystemExit):
                mod.main()
            assert "sdk is required" in module.fail_json.call_args[1]["msg"]
        finally:
            mod.HAS_PURESTORAGE = original

    @staticmethod
    def _wire(mock_am, mock_ga, **params):
        module = make_module(**params)
        mock_am.return_value = module
        array = Mock()
        mock_ga.return_value = array
        return module, array

    @patch("plugins.modules.purefa_localuser.create_user")
    @patch("plugins.modules.purefa_localuser.read_user")
    @patch("plugins.modules.purefa_localuser.check_api_version")
    @patch("plugins.modules.purefa_localuser.get_array")
    @patch("plugins.modules.purefa_localuser.AnsibleModule")
    def test_main_creates_when_absent(
        self, mock_am, mock_ga, mock_api, mock_read, mock_create
    ):
        import plugins.modules.purefa_localuser as mod

        module, array = self._wire(mock_am, mock_ga)
        mock_read.return_value = None

        mod.main()

        mock_create.assert_called_once_with(module, array)
        mock_api.assert_called_once()

    @patch("plugins.modules.purefa_localuser.update_user")
    @patch("plugins.modules.purefa_localuser.read_user")
    @patch("plugins.modules.purefa_localuser.check_api_version")
    @patch("plugins.modules.purefa_localuser.get_array")
    @patch("plugins.modules.purefa_localuser.AnsibleModule")
    def test_main_updates_when_present(
        self, mock_am, mock_ga, mock_api, mock_read, mock_update
    ):
        import plugins.modules.purefa_localuser as mod

        module, array = self._wire(mock_am, mock_ga, email="a@example.com")
        user = make_user()
        mock_read.return_value = user

        mod.main()

        mock_update.assert_called_once_with(module, array, user)

    @patch("plugins.modules.purefa_localuser.check_renamed_user")
    @patch("plugins.modules.purefa_localuser.create_user")
    @patch("plugins.modules.purefa_localuser.rename_user")
    @patch("plugins.modules.purefa_localuser.read_user")
    @patch("plugins.modules.purefa_localuser.check_api_version")
    @patch("plugins.modules.purefa_localuser.get_array")
    @patch("plugins.modules.purefa_localuser.AnsibleModule")
    def test_main_rename_first_run(
        self,
        mock_am,
        mock_ga,
        mock_api,
        mock_read,
        mock_rename,
        mock_create,
        mock_checked,
    ):
        """First run: the source is there, so the rename happens"""
        import plugins.modules.purefa_localuser as mod

        module, array = self._wire(mock_am, mock_ga, rename="freddy")
        mock_read.return_value = make_user()

        mod.main()

        mock_rename.assert_called_once_with(module, array)
        mock_create.assert_not_called()
        mock_checked.assert_not_called()

    @patch("plugins.modules.purefa_localuser.check_renamed_user")
    @patch("plugins.modules.purefa_localuser.create_user")
    @patch("plugins.modules.purefa_localuser.rename_user")
    @patch("plugins.modules.purefa_localuser.read_user")
    @patch("plugins.modules.purefa_localuser.check_api_version")
    @patch("plugins.modules.purefa_localuser.get_array")
    @patch("plugins.modules.purefa_localuser.AnsibleModule")
    def test_main_rename_second_run_does_not_create(
        self,
        mock_am,
        mock_ga,
        mock_api,
        mock_read,
        mock_rename,
        mock_create,
        mock_checked,
    ):
        """Second run: the source has gone, and must not be created again"""
        import plugins.modules.purefa_localuser as mod

        module, array = self._wire(mock_am, mock_ga, rename="freddy")
        mock_read.return_value = None

        mod.main()

        mock_checked.assert_called_once_with(module, array)
        mock_create.assert_not_called()
        mock_rename.assert_not_called()

    @patch("plugins.modules.purefa_localuser.delete_user")
    @patch("plugins.modules.purefa_localuser.read_user")
    @patch("plugins.modules.purefa_localuser.check_api_version")
    @patch("plugins.modules.purefa_localuser.get_array")
    @patch("plugins.modules.purefa_localuser.AnsibleModule")
    def test_main_deletes_when_present(
        self, mock_am, mock_ga, mock_api, mock_read, mock_delete
    ):
        import plugins.modules.purefa_localuser as mod

        module, array = self._wire(mock_am, mock_ga, state="absent")
        user = make_user()
        mock_read.return_value = user

        mod.main()

        mock_delete.assert_called_once_with(module, array, user)

    @patch("plugins.modules.purefa_localuser.delete_user")
    @patch("plugins.modules.purefa_localuser.read_user")
    @patch("plugins.modules.purefa_localuser.check_api_version")
    @patch("plugins.modules.purefa_localuser.get_array")
    @patch("plugins.modules.purefa_localuser.AnsibleModule")
    def test_main_absent_and_missing_is_no_change(
        self, mock_am, mock_ga, mock_api, mock_read, mock_delete
    ):
        import plugins.modules.purefa_localuser as mod

        module, array = self._wire(mock_am, mock_ga, state="absent")
        mock_read.return_value = None

        mod.main()

        mock_delete.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)
