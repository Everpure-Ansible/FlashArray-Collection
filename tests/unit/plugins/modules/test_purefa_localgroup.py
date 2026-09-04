# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_localgroup module."""

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

from plugins.modules.purefa_localgroup import (
    read_group,
    create_group,
    update_group,
    rename_group,
    check_renamed_group,
    delete_group,
    _scope,
    _wanted_changes,
)


def make_module(**params):
    """An AnsibleModule stand-in whose fail_json raises, as the real one does"""
    module = Mock()
    module.check_mode = False
    base = {
        "name": "grp1",
        "local_directory_service": "lds1",
        "gid": None,
        "email": None,
        "rename": None,
        "state": "present",
        "context": "",
    }
    base.update(params)
    module.params = base
    module.fail_json.side_effect = SystemExit(1)
    return module


def make_group(name="grp1", gid=70001, email="a@example.com", built_in=False):
    group = Mock()
    group.name = name
    group.gid = gid
    group.email = email
    group.built_in = built_in
    return group


class TestReadGroup:
    """Test cases for read_group function"""

    @patch("plugins.modules.purefa_localgroup.get_with_context")
    def test_read_group_scopes_by_directory_service(self, mock_get):
        """Test read_group narrows the lookup to one local directory service

        A bare name matches the group of that name in every service on the
        array, so the service has to be part of the query.
        """
        module = make_module()
        group = make_group()
        mock_get.return_value = Mock(status_code=200, items=[group])

        assert read_group(module, Mock(), "grp1") is group
        kwargs = mock_get.call_args[1]
        assert kwargs["names"] == ["grp1"]
        assert kwargs["filter"] == "local_directory_service.name='lds1'"

    @patch("plugins.modules.purefa_localgroup.get_with_context")
    def test_read_group_absent_is_400_not_404(self, mock_get):
        """Test anything other than 200 counts as absent"""
        module = make_module()
        mock_get.return_value = Mock(status_code=400)

        assert read_group(module, Mock(), "nope") is None

    @patch("plugins.modules.purefa_localgroup.get_with_context")
    def test_read_group_empty_items(self, mock_get):
        """Test a 200 carrying nothing is absent"""
        module = make_module()
        mock_get.return_value = Mock(status_code=200, items=[])

        assert read_group(module, Mock(), "grp1") is None


class TestHelpers:
    """Test cases for the scoping and diff helpers"""

    def test_scope_names_the_directory_service(self):
        """Test writes are aimed at one local directory service"""
        module = make_module()

        assert _scope(module) == {"local_directory_service_names": ["lds1"]}

    def test_wanted_changes_ignores_omitted_options(self):
        """Test an option the play leaves out is never a change"""
        module = make_module()
        group = make_group(gid=1, email="x@example.com")

        assert _wanted_changes(module, group) == {}

    def test_wanted_changes_ignores_matching_values(self):
        """Test a setting that already matches is not a change"""
        module = make_module(gid=70001, email="a@example.com")
        group = make_group(gid=70001, email="a@example.com")

        assert _wanted_changes(module, group) == {}

    def test_wanted_changes_reports_differences_only(self):
        """Test only the differing settings are collected"""
        module = make_module(gid=70001, email="new@example.com")
        group = make_group(gid=70001, email="old@example.com")

        assert _wanted_changes(module, group) == {"email": "new@example.com"}


class TestCreateGroup:
    """Test cases for create_group function"""

    def test_create_group_check_mode(self):
        """Test create_group predicts the change without calling the array"""
        module = make_module(gid=70001)
        module.check_mode = True

        create_group(module, Mock())

        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localgroup.check_response")
    @patch("plugins.modules.purefa_localgroup.post_with_context")
    def test_create_group_scoped(self, mock_post, mock_check):
        """Test create_group posts into the requested service"""
        module = make_module(gid=70001, email="a@example.com")
        mock_post.return_value = Mock(status_code=200)

        create_group(module, Mock())

        kwargs = mock_post.call_args[1]
        assert kwargs["names"] == ["grp1"]
        assert kwargs["local_directory_service_names"] == ["lds1"]
        module.exit_json.assert_called_once_with(changed=True)


class TestUpdateGroup:
    """Test cases for update_group function"""

    @patch("plugins.modules.purefa_localgroup.patch_with_context")
    def test_update_group_nothing_requested(self, mock_patch):
        """Test naming the group alone reports no change"""
        module = make_module()
        update_group(module, Mock(), make_group())

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_localgroup.check_response")
    @patch("plugins.modules.purefa_localgroup.patch_with_context")
    def test_update_group_changes_email(self, mock_patch, mock_check):
        """Test a differing setting is patched, scoped to the service"""
        module = make_module(email="new@example.com")
        mock_patch.return_value = Mock(status_code=200)

        update_group(module, Mock(), make_group(email="old@example.com"))

        assert mock_patch.call_args[1]["local_directory_service_names"] == ["lds1"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localgroup.patch_with_context")
    def test_update_group_builtin_no_change_allowed(self, mock_patch):
        """Test a built-in group with nothing asked of it is not an error"""
        module = make_module()

        update_group(module, Mock(), make_group(built_in=True))

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)
        module.fail_json.assert_not_called()

    @patch("plugins.modules.purefa_localgroup.patch_with_context")
    def test_update_group_builtin_change_fails(self, mock_patch):
        """Test changing a built-in group fails before the array is called"""
        module = make_module(email="nope@example.com")

        with pytest.raises(SystemExit):
            update_group(
                module, Mock(), make_group(email="a@example.com", built_in=True)
            )

        assert "built-in" in module.fail_json.call_args[1]["msg"]
        mock_patch.assert_not_called()

    @patch("plugins.modules.purefa_localgroup.patch_with_context")
    def test_update_group_check_mode(self, mock_patch):
        """Test update_group predicts a change without making it"""
        module = make_module(gid=70009)
        module.check_mode = True

        update_group(module, Mock(), make_group(gid=70001))

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestRenameGroup:
    """Test cases for rename_group function"""

    @patch("plugins.modules.purefa_localgroup.check_response")
    @patch("plugins.modules.purefa_localgroup.patch_with_context")
    @patch("plugins.modules.purefa_localgroup.read_group")
    def test_rename_group_success(self, mock_read, mock_patch, mock_check):
        """Test rename_group patches the new name when it is free"""
        module = make_module(rename="grp2")
        mock_read.return_value = None
        mock_patch.return_value = Mock(status_code=200)

        rename_group(module, Mock(), make_group())

        assert mock_patch.call_args[1]["local_directory_service_names"] == ["lds1"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localgroup.patch_with_context")
    @patch("plugins.modules.purefa_localgroup.read_group")
    def test_rename_group_target_exists_fails(self, mock_read, mock_patch):
        """Test renaming onto an existing group in the same service fails"""
        module = make_module(rename="grp2")
        mock_read.return_value = make_group(name="grp2")

        with pytest.raises(SystemExit):
            rename_group(module, Mock(), make_group())

        assert "already exists" in module.fail_json.call_args[1]["msg"]
        mock_patch.assert_not_called()

    @patch("plugins.modules.purefa_localgroup.patch_with_context")
    @patch("plugins.modules.purefa_localgroup.read_group")
    def test_rename_group_builtin_fails(self, mock_read, mock_patch):
        """Test a built-in group cannot be renamed"""
        module = make_module(rename="grp2")

        with pytest.raises(SystemExit):
            rename_group(module, Mock(), make_group(built_in=True))

        assert "built-in" in module.fail_json.call_args[1]["msg"]
        mock_patch.assert_not_called()
        mock_read.assert_not_called()


class TestCheckRenamedGroup:
    """Test cases for check_renamed_group, the second run of a rename"""

    @patch("plugins.modules.purefa_localgroup.read_group")
    def test_check_renamed_group_already_renamed(self, mock_read):
        """Test no change is reported once the target is there"""
        module = make_module(rename="grp2")
        mock_read.return_value = make_group(name="grp2")

        check_renamed_group(module, Mock())

        module.exit_json.assert_called_once_with(changed=False)
        module.fail_json.assert_not_called()

    @patch("plugins.modules.purefa_localgroup.read_group")
    def test_check_renamed_group_neither_exists_fails(self, mock_read):
        """Test a rename with nothing to rename fails instead of creating"""
        module = make_module(rename="grp2")
        mock_read.return_value = None

        with pytest.raises(SystemExit):
            check_renamed_group(module, Mock())

        assert "not found to rename" in module.fail_json.call_args[1]["msg"]
        module.exit_json.assert_not_called()


class TestDeleteGroup:
    """Test cases for delete_group function"""

    def test_delete_group_check_mode(self):
        """Test delete_group predicts the change without calling the array"""
        module = make_module(state="absent")
        module.check_mode = True

        delete_group(module, Mock(), make_group())

        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localgroup.check_response")
    @patch("plugins.modules.purefa_localgroup.delete_with_context")
    def test_delete_group_scoped(self, mock_delete, mock_check):
        """Test delete_group only targets the requested service"""
        module = make_module(state="absent")
        mock_delete.return_value = Mock(status_code=200)

        delete_group(module, Mock(), make_group())

        kwargs = mock_delete.call_args[1]
        assert kwargs["names"] == ["grp1"]
        assert kwargs["local_directory_service_names"] == ["lds1"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_localgroup.delete_with_context")
    def test_delete_group_builtin_fails(self, mock_delete):
        """Test a built-in group cannot be deleted"""
        module = make_module(state="absent")

        with pytest.raises(SystemExit):
            delete_group(module, Mock(), make_group(built_in=True))

        assert "built-in" in module.fail_json.call_args[1]["msg"]
        mock_delete.assert_not_called()


class TestMain:
    """Test cases for the main dispatch"""

    @patch("plugins.modules.purefa_localgroup.get_array")
    @patch("plugins.modules.purefa_localgroup.AnsibleModule")
    def test_main_no_purestorage_sdk(self, mock_am, mock_ga):
        """Test main fails when py-pure-client is missing"""
        import plugins.modules.purefa_localgroup as mod

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

    @patch("plugins.modules.purefa_localgroup.create_group")
    @patch("plugins.modules.purefa_localgroup.read_group")
    @patch("plugins.modules.purefa_localgroup.check_api_version")
    @patch("plugins.modules.purefa_localgroup.get_array")
    @patch("plugins.modules.purefa_localgroup.AnsibleModule")
    def test_main_creates_when_absent(
        self, mock_am, mock_ga, mock_api, mock_read, mock_create
    ):
        """Test main creates a group the service does not hold"""
        import plugins.modules.purefa_localgroup as mod

        module, array = self._wire(mock_am, mock_ga)
        mock_read.return_value = None

        mod.main()

        mock_create.assert_called_once_with(module, array)
        mock_api.assert_called_once()

    @patch("plugins.modules.purefa_localgroup.update_group")
    @patch("plugins.modules.purefa_localgroup.read_group")
    @patch("plugins.modules.purefa_localgroup.check_api_version")
    @patch("plugins.modules.purefa_localgroup.get_array")
    @patch("plugins.modules.purefa_localgroup.AnsibleModule")
    def test_main_updates_when_present(
        self, mock_am, mock_ga, mock_api, mock_read, mock_update
    ):
        """Test main reconciles a group that is already there"""
        import plugins.modules.purefa_localgroup as mod

        module, array = self._wire(mock_am, mock_ga, email="a@example.com")
        group = make_group()
        mock_read.return_value = group

        mod.main()

        mock_update.assert_called_once_with(module, array, group)

    @patch("plugins.modules.purefa_localgroup.check_renamed_group")
    @patch("plugins.modules.purefa_localgroup.create_group")
    @patch("plugins.modules.purefa_localgroup.rename_group")
    @patch("plugins.modules.purefa_localgroup.read_group")
    @patch("plugins.modules.purefa_localgroup.check_api_version")
    @patch("plugins.modules.purefa_localgroup.get_array")
    @patch("plugins.modules.purefa_localgroup.AnsibleModule")
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
        import plugins.modules.purefa_localgroup as mod

        module, array = self._wire(mock_am, mock_ga, rename="grp2")
        group = make_group()
        mock_read.return_value = group

        mod.main()

        mock_rename.assert_called_once_with(module, array, group)
        mock_create.assert_not_called()
        mock_checked.assert_not_called()

    @patch("plugins.modules.purefa_localgroup.check_renamed_group")
    @patch("plugins.modules.purefa_localgroup.create_group")
    @patch("plugins.modules.purefa_localgroup.rename_group")
    @patch("plugins.modules.purefa_localgroup.read_group")
    @patch("plugins.modules.purefa_localgroup.check_api_version")
    @patch("plugins.modules.purefa_localgroup.get_array")
    @patch("plugins.modules.purefa_localgroup.AnsibleModule")
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
        import plugins.modules.purefa_localgroup as mod

        module, array = self._wire(mock_am, mock_ga, rename="grp2")
        mock_read.return_value = None

        mod.main()

        mock_checked.assert_called_once_with(module, array)
        mock_create.assert_not_called()
        mock_rename.assert_not_called()

    @patch("plugins.modules.purefa_localgroup.delete_group")
    @patch("plugins.modules.purefa_localgroup.read_group")
    @patch("plugins.modules.purefa_localgroup.check_api_version")
    @patch("plugins.modules.purefa_localgroup.get_array")
    @patch("plugins.modules.purefa_localgroup.AnsibleModule")
    def test_main_deletes_when_present(
        self, mock_am, mock_ga, mock_api, mock_read, mock_delete
    ):
        """Test main deletes a group that is there"""
        import plugins.modules.purefa_localgroup as mod

        module, array = self._wire(mock_am, mock_ga, state="absent")
        group = make_group()
        mock_read.return_value = group

        mod.main()

        mock_delete.assert_called_once_with(module, array, group)

    @patch("plugins.modules.purefa_localgroup.delete_group")
    @patch("plugins.modules.purefa_localgroup.read_group")
    @patch("plugins.modules.purefa_localgroup.check_api_version")
    @patch("plugins.modules.purefa_localgroup.get_array")
    @patch("plugins.modules.purefa_localgroup.AnsibleModule")
    def test_main_absent_and_missing_is_no_change(
        self, mock_am, mock_ga, mock_api, mock_read, mock_delete
    ):
        """Test removing something that is not there reports no change"""
        import plugins.modules.purefa_localgroup as mod

        module, array = self._wire(mock_am, mock_ga, state="absent")
        mock_read.return_value = None

        mod.main()

        mock_delete.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)
