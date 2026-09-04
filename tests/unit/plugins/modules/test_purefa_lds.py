# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_lds module."""

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

from plugins.modules.purefa_lds import (
    read_lds,
    create_lds,
    update_lds,
    rename_lds,
    check_renamed_lds,
    delete_lds,
)


def make_module(**params):
    """An AnsibleModule stand-in whose fail_json raises, as the real one does"""
    module = Mock()
    module.check_mode = False
    base = {
        "name": "lds1",
        "domain": None,
        "rename": None,
        "state": "present",
        "context": "",
    }
    base.update(params)
    module.params = base
    module.fail_json.side_effect = SystemExit(1)
    return module


class TestReadLds:
    """Test cases for read_lds function"""

    @patch("plugins.modules.purefa_lds.get_with_context")
    def test_read_lds_found(self, mock_get):
        """Test read_lds returns the service the array holds"""
        module = make_module()
        lds = Mock()
        lds.name = "lds1"
        mock_get.return_value = Mock(status_code=200, items=[lds])

        assert read_lds(module, Mock(), "lds1") is lds
        assert mock_get.call_args[1]["names"] == ["lds1"]

    @patch("plugins.modules.purefa_lds.get_with_context")
    def test_read_lds_absent_is_400_not_404(self, mock_get):
        """Test read_lds treats the array's 400 for an unknown name as absent

        The array answers a name it does not have with 400, so anything other
        than 200 has to count as absent.
        """
        module = make_module()
        mock_get.return_value = Mock(status_code=400)

        assert read_lds(module, Mock(), "nope") is None

    @patch("plugins.modules.purefa_lds.get_with_context")
    def test_read_lds_empty_items(self, mock_get):
        """Test read_lds copes with a 200 that carries nothing"""
        module = make_module()
        mock_get.return_value = Mock(status_code=200, items=[])

        assert read_lds(module, Mock(), "lds1") is None


class TestCreateLds:
    """Test cases for create_lds function"""

    def test_create_lds_check_mode(self):
        """Test create_lds predicts the change without calling the array"""
        module = make_module(domain="a.example")
        module.check_mode = True

        create_lds(module, Mock())

        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_lds.check_response")
    @patch("plugins.modules.purefa_lds.post_with_context")
    def test_create_lds_success(self, mock_post, mock_check):
        """Test create_lds posts the name and reports a change"""
        module = make_module(domain="a.example")
        mock_post.return_value = Mock(status_code=200)

        create_lds(module, Mock())

        assert mock_post.call_args[1]["names"] == ["lds1"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_lds.check_response")
    @patch("plugins.modules.purefa_lds.post_with_context")
    def test_create_lds_without_domain(self, mock_post, mock_check):
        """Test create_lds still creates when no domain is given

        The array defaults the domain to the name of the service.
        """
        module = make_module()
        mock_post.return_value = Mock(status_code=200)

        create_lds(module, Mock())

        mock_post.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)


class TestUpdateLds:
    """Test cases for update_lds function"""

    @patch("plugins.modules.purefa_lds.patch_with_context")
    def test_update_lds_no_domain_requested(self, mock_patch):
        """Test an omitted domain is not treated as a change"""
        module = make_module()
        lds = Mock()
        lds.domain = "current.example"

        update_lds(module, Mock(), lds)

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_lds.patch_with_context")
    def test_update_lds_domain_already_correct(self, mock_patch):
        """Test a matching domain reports no change"""
        module = make_module(domain="same.example")
        lds = Mock()
        lds.domain = "same.example"

        update_lds(module, Mock(), lds)

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_lds.check_response")
    @patch("plugins.modules.purefa_lds.patch_with_context")
    def test_update_lds_domain_changed(self, mock_patch, mock_check):
        """Test a differing domain is patched"""
        module = make_module(domain="new.example")
        lds = Mock()
        lds.domain = "old.example"
        mock_patch.return_value = Mock(status_code=200)

        update_lds(module, Mock(), lds)

        assert mock_patch.call_args[1]["names"] == ["lds1"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_lds.patch_with_context")
    def test_update_lds_check_mode(self, mock_patch):
        """Test update_lds predicts a domain change without making it"""
        module = make_module(domain="new.example")
        module.check_mode = True
        lds = Mock()
        lds.domain = "old.example"

        update_lds(module, Mock(), lds)

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestRenameLds:
    """Test cases for rename_lds function"""

    @patch("plugins.modules.purefa_lds.check_response")
    @patch("plugins.modules.purefa_lds.patch_with_context")
    @patch("plugins.modules.purefa_lds.read_lds")
    def test_rename_lds_success(self, mock_read, mock_patch, mock_check):
        """Test rename_lds patches the new name when it is free"""
        module = make_module(rename="lds2")
        mock_read.return_value = None
        mock_patch.return_value = Mock(status_code=200)

        rename_lds(module, Mock())

        assert mock_patch.call_args[1]["names"] == ["lds1"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_lds.patch_with_context")
    @patch("plugins.modules.purefa_lds.read_lds")
    def test_rename_lds_target_exists_fails(self, mock_read, mock_patch):
        """Test rename_lds refuses to rename onto an existing service"""
        module = make_module(rename="lds2")
        mock_read.return_value = Mock()

        with pytest.raises(SystemExit):
            rename_lds(module, Mock())

        assert "already exists" in module.fail_json.call_args[1]["msg"]
        mock_patch.assert_not_called()

    @patch("plugins.modules.purefa_lds.patch_with_context")
    @patch("plugins.modules.purefa_lds.read_lds")
    def test_rename_lds_check_mode(self, mock_read, mock_patch):
        """Test rename_lds predicts the rename without making it"""
        module = make_module(rename="lds2")
        module.check_mode = True
        mock_read.return_value = None

        rename_lds(module, Mock())

        mock_patch.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestCheckRenamedLds:
    """Test cases for check_renamed_lds function

    This is the second run of a rename task, when the source has already gone.
    """

    @patch("plugins.modules.purefa_lds.read_lds")
    def test_check_renamed_lds_already_renamed(self, mock_read):
        """Test no change is reported once the target is there"""
        module = make_module(rename="lds2")
        mock_read.return_value = Mock()

        check_renamed_lds(module, Mock())

        module.exit_json.assert_called_once_with(changed=False)
        module.fail_json.assert_not_called()

    @patch("plugins.modules.purefa_lds.read_lds")
    def test_check_renamed_lds_neither_exists_fails(self, mock_read):
        """Test a rename with nothing to rename fails instead of creating"""
        module = make_module(rename="lds2")
        mock_read.return_value = None

        with pytest.raises(SystemExit):
            check_renamed_lds(module, Mock())

        assert "not found to rename" in module.fail_json.call_args[1]["msg"]
        module.exit_json.assert_not_called()


class TestDeleteLds:
    """Test cases for delete_lds function"""

    def test_delete_lds_check_mode(self):
        """Test delete_lds predicts the change without calling the array"""
        module = make_module(state="absent")
        module.check_mode = True

        delete_lds(module, Mock())

        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_lds.check_response")
    @patch("plugins.modules.purefa_lds.delete_with_context")
    def test_delete_lds_success(self, mock_delete, mock_check):
        """Test delete_lds deletes by name and reports a change"""
        module = make_module(state="absent")
        mock_delete.return_value = Mock(status_code=200)

        delete_lds(module, Mock())

        assert mock_delete.call_args[1]["names"] == ["lds1"]
        module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for the main dispatch"""

    @patch("plugins.modules.purefa_lds.get_array")
    @patch("plugins.modules.purefa_lds.AnsibleModule")
    def test_main_no_purestorage_sdk(self, mock_ansible_module, mock_get_array):
        """Test main fails when py-pure-client is missing"""
        import plugins.modules.purefa_lds as mod

        original = mod.HAS_PURESTORAGE
        mod.HAS_PURESTORAGE = False
        module = make_module()
        mock_ansible_module.return_value = module
        try:
            with pytest.raises(SystemExit):
                mod.main()
            assert "sdk is required" in module.fail_json.call_args[1]["msg"]
        finally:
            mod.HAS_PURESTORAGE = original

    @staticmethod
    def _wire(mock_ansible_module, mock_get_array, **params):
        module = make_module(**params)
        mock_ansible_module.return_value = module
        array = Mock()
        mock_get_array.return_value = array
        return module, array

    @patch("plugins.modules.purefa_lds.create_lds")
    @patch("plugins.modules.purefa_lds.read_lds")
    @patch("plugins.modules.purefa_lds.check_api_version")
    @patch("plugins.modules.purefa_lds.get_array")
    @patch("plugins.modules.purefa_lds.AnsibleModule")
    def test_main_creates_when_absent(
        self, mock_am, mock_ga, mock_check_api, mock_read, mock_create
    ):
        """Test main creates a service the array does not have"""
        import plugins.modules.purefa_lds as mod

        module, array = self._wire(mock_am, mock_ga)
        mock_read.return_value = None

        mod.main()

        mock_create.assert_called_once_with(module, array)
        mock_check_api.assert_called_once()

    @patch("plugins.modules.purefa_lds.update_lds")
    @patch("plugins.modules.purefa_lds.read_lds")
    @patch("plugins.modules.purefa_lds.check_api_version")
    @patch("plugins.modules.purefa_lds.get_array")
    @patch("plugins.modules.purefa_lds.AnsibleModule")
    def test_main_updates_when_present(
        self, mock_am, mock_ga, mock_check_api, mock_read, mock_update
    ):
        """Test main reconciles a service that is already there"""
        import plugins.modules.purefa_lds as mod

        module, array = self._wire(mock_am, mock_ga, domain="a.example")
        lds = Mock()
        mock_read.return_value = lds

        mod.main()

        mock_update.assert_called_once_with(module, array, lds)

    @patch("plugins.modules.purefa_lds.check_renamed_lds")
    @patch("plugins.modules.purefa_lds.create_lds")
    @patch("plugins.modules.purefa_lds.rename_lds")
    @patch("plugins.modules.purefa_lds.read_lds")
    @patch("plugins.modules.purefa_lds.check_api_version")
    @patch("plugins.modules.purefa_lds.get_array")
    @patch("plugins.modules.purefa_lds.AnsibleModule")
    def test_main_rename_first_run(
        self,
        mock_am,
        mock_ga,
        mock_check_api,
        mock_read,
        mock_rename,
        mock_create,
        mock_checked,
    ):
        """First run: the source is there, so the rename happens"""
        import plugins.modules.purefa_lds as mod

        module, array = self._wire(mock_am, mock_ga, rename="lds2")
        mock_read.return_value = Mock()

        mod.main()

        mock_rename.assert_called_once_with(module, array)
        mock_create.assert_not_called()
        mock_checked.assert_not_called()

    @patch("plugins.modules.purefa_lds.check_renamed_lds")
    @patch("plugins.modules.purefa_lds.create_lds")
    @patch("plugins.modules.purefa_lds.rename_lds")
    @patch("plugins.modules.purefa_lds.read_lds")
    @patch("plugins.modules.purefa_lds.check_api_version")
    @patch("plugins.modules.purefa_lds.get_array")
    @patch("plugins.modules.purefa_lds.AnsibleModule")
    def test_main_rename_second_run_does_not_create(
        self,
        mock_am,
        mock_ga,
        mock_check_api,
        mock_read,
        mock_rename,
        mock_create,
        mock_checked,
    ):
        """Second run: the source has gone, and must not be created again"""
        import plugins.modules.purefa_lds as mod

        module, array = self._wire(mock_am, mock_ga, rename="lds2")
        mock_read.return_value = None

        mod.main()

        mock_checked.assert_called_once_with(module, array)
        mock_create.assert_not_called()
        mock_rename.assert_not_called()

    @patch("plugins.modules.purefa_lds.delete_lds")
    @patch("plugins.modules.purefa_lds.read_lds")
    @patch("plugins.modules.purefa_lds.check_api_version")
    @patch("plugins.modules.purefa_lds.get_array")
    @patch("plugins.modules.purefa_lds.AnsibleModule")
    def test_main_deletes_when_present(
        self, mock_am, mock_ga, mock_check_api, mock_read, mock_delete
    ):
        """Test main deletes a service that is there"""
        import plugins.modules.purefa_lds as mod

        module, array = self._wire(mock_am, mock_ga, state="absent")
        mock_read.return_value = Mock()

        mod.main()

        mock_delete.assert_called_once_with(module, array)

    @patch("plugins.modules.purefa_lds.delete_lds")
    @patch("plugins.modules.purefa_lds.read_lds")
    @patch("plugins.modules.purefa_lds.check_api_version")
    @patch("plugins.modules.purefa_lds.get_array")
    @patch("plugins.modules.purefa_lds.AnsibleModule")
    def test_main_absent_and_missing_is_no_change(
        self, mock_am, mock_ga, mock_check_api, mock_read, mock_delete
    ):
        """Test removing something that is not there reports no change"""
        import plugins.modules.purefa_lds as mod

        module, array = self._wire(mock_am, mock_ga, state="absent")
        mock_read.return_value = None

        mod.main()

        mock_delete.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)
