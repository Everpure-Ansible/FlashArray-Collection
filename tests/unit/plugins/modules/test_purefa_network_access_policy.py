# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_network_access_policy module."""

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

from plugins.modules.purefa_network_access_policy import (
    check_renamed_policy,
    rename_policy,
    create_policy,
    update_policy,
    delete_policy,
)


MODULE_PATH = "plugins.modules.purefa_network_access_policy"


def _base_params(**overrides):
    """Return a full params dict with sensible defaults for the module."""
    params = {
        "name": "restricted",
        "context": "",
        "state": "present",
        "enabled": True,
        "rename": None,
        "active": None,
        "effect": None,
        "client": None,
        "interfaces": None,
        "index": None,
        "rule_name": None,
    }
    params.update(overrides)
    return params


def _rule_obj(name="restricted.1", effect="allow", client="*",
              interfaces=None, index=1):
    """Build a mock rule object with the attributes update_policy inspects."""
    rule = Mock()
    rule.name = name
    rule.effect = effect
    rule.client = client
    rule.interfaces = interfaces if interfaces is not None else ["management-ssh"]
    rule.index = index
    return rule


class TestCheckRenamedPolicy:
    """Tests for check_renamed_policy"""

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_renamed_target_present_reports_no_change(self, mock_get):
        mock_module = Mock()
        mock_module.params = _base_params(rename="restricted-mgmt")
        target = Mock()
        target.destroyed = False
        mock_get.return_value = Mock(status_code=200, items=[target])

        check_renamed_policy(mock_module, Mock())

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_module.fail_json.assert_not_called()

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_renamed_target_missing_fails(self, mock_get):
        mock_module = Mock()
        mock_module.params = _base_params(rename="restricted-mgmt")
        mock_module.fail_json.side_effect = Exception("fail_json called")
        mock_get.return_value = Mock(status_code=400, items=[])

        try:
            check_renamed_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert "not found to rename" in mock_module.fail_json.call_args.kwargs["msg"]

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_renamed_target_destroyed_fails(self, mock_get):
        mock_module = Mock()
        mock_module.params = _base_params(rename="restricted-mgmt")
        mock_module.fail_json.side_effect = Exception("fail_json called")
        target = Mock()
        target.destroyed = True
        mock_get.return_value = Mock(status_code=200, items=[target])

        try:
            check_renamed_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert "destroyed" in mock_module.fail_json.call_args.kwargs["msg"]


class TestRenamePolicy:
    """Tests for rename_policy"""

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_rename_conflict_fails(self, mock_get):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(rename="restricted-mgmt")
        mock_module.fail_json.side_effect = Exception("fail_json called")
        mock_get.return_value = Mock(status_code=200, items=[Mock()])

        try:
            rename_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert "already exists" in mock_module.fail_json.call_args.kwargs["msg"]

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_rename_check_mode(self, mock_get):
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _base_params(rename="restricted-mgmt")
        mock_get.return_value = Mock(status_code=400)

        rename_policy(mock_module, Mock())

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.check_response")
    @patch(f"{MODULE_PATH}.PolicyPatch")
    @patch(f"{MODULE_PATH}.patch_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_rename_success(self, mock_get, mock_patch, mock_patch_model, mock_check):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(rename="restricted-mgmt")
        mock_get.return_value = Mock(status_code=400)
        mock_patch.return_value = Mock(status_code=200)

        rename_policy(mock_module, Mock())

        mock_patch.assert_called_once()
        assert mock_patch_model.call_args.kwargs["name"] == "restricted-mgmt"
        mock_module.exit_json.assert_called_once_with(changed=True)


class TestCreatePolicy:
    """Tests for create_policy"""

    def test_create_active_with_no_rule_fails(self):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(active=True)
        mock_module.fail_json.side_effect = Exception("fail_json called")

        try:
            create_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert "no rules" in mock_module.fail_json.call_args.kwargs["msg"]

    def test_create_policy_check_mode(self):
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _base_params()

        create_policy(mock_module, Mock())

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.PolicyPost")
    @patch(f"{MODULE_PATH}.post_with_context")
    def test_create_policy_empty_success(self, mock_post, mock_post_model):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params()
        mock_post.return_value = Mock(status_code=200)

        create_policy(mock_module, Mock())

        mock_post.assert_called_once()
        assert mock_post_model.call_args.kwargs["enabled"] is True
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.check_response")
    @patch(f"{MODULE_PATH}.PolicyrulenetworkaccesspostRules")
    @patch(f"{MODULE_PATH}.PolicyRuleNetworkAccessPost")
    @patch(f"{MODULE_PATH}.PolicyPost")
    @patch(f"{MODULE_PATH}.post_with_context")
    def test_create_policy_with_initial_rule(
        self, mock_post, mock_post_model, mock_rules_model, mock_rule_model, mock_check
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(
            effect="deny",
            client="10.20.30.0/24",
            interfaces=["management-ssh", "management-web-ui"],
        )
        mock_post.return_value = Mock(status_code=200)

        create_policy(mock_module, Mock())

        # First call creates policy; second call posts the rule.
        assert mock_post.call_count == 2
        rule_kwargs = mock_rule_model.call_args.kwargs
        assert rule_kwargs["effect"] == "deny"
        assert rule_kwargs["client"] == "10.20.30.0/24"
        assert rule_kwargs["interfaces"] == [
            "management-ssh",
            "management-web-ui",
        ]
        assert "index" not in rule_kwargs
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.check_response")
    @patch(f"{MODULE_PATH}.Reference")
    @patch(f"{MODULE_PATH}.Arrays")
    @patch(f"{MODULE_PATH}.PolicyrulenetworkaccesspostRules")
    @patch(f"{MODULE_PATH}.PolicyRuleNetworkAccessPost")
    @patch(f"{MODULE_PATH}.PolicyPost")
    @patch(f"{MODULE_PATH}.patch_with_context")
    @patch(f"{MODULE_PATH}.post_with_context")
    def test_create_policy_with_activate(
        self,
        mock_post,
        mock_patch,
        mock_post_model,
        mock_rules_model,
        mock_rule_model,
        mock_arrays,
        mock_reference,
        mock_check,
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(
            effect="allow",
            client="*",
            interfaces=["management-ssh"],
            active=True,
        )
        mock_post.return_value = Mock(status_code=200)
        mock_patch.return_value = Mock(status_code=200)

        create_policy(mock_module, Mock())

        assert mock_post.call_count == 2
        mock_patch.assert_called_once()
        mock_reference.assert_called_once_with(name="restricted")
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.PolicyPost")
    @patch(f"{MODULE_PATH}.post_with_context")
    def test_create_policy_post_failure(self, mock_post, mock_post_model):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params()
        mock_module.fail_json.side_effect = Exception("fail_json called")
        err = Mock()
        err.message = "boom"
        mock_post.return_value = Mock(status_code=400, errors=[err])

        try:
            create_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert (
            "Failed to create" in mock_module.fail_json.call_args.kwargs["msg"]
        )


class TestUpdatePolicy:
    """Tests for update_policy"""

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_no_change(self, mock_get):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params()
        current = Mock()
        current.enabled = True
        mock_get.return_value = Mock(status_code=200, items=[current])

        update_policy(mock_module, Mock())

        mock_module.exit_json.assert_called_once_with(changed=False)

    @patch(f"{MODULE_PATH}.check_response")
    @patch(f"{MODULE_PATH}.PolicyPatch")
    @patch(f"{MODULE_PATH}.patch_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_toggles_enabled(
        self, mock_get, mock_patch, mock_patch_model, mock_check
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(enabled=False)
        current = Mock()
        current.enabled = True
        mock_get.return_value = Mock(status_code=200, items=[current])
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, Mock())

        mock_patch.assert_called_once()
        assert mock_patch_model.call_args.kwargs["enabled"] is False
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_get_failure_fails(self, mock_get):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params()
        mock_module.fail_json.side_effect = Exception("fail_json called")
        mock_get.return_value = Mock(status_code=400)

        try:
            update_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert (
            "Failed to read" in mock_module.fail_json.call_args.kwargs["msg"]
        )

    @patch(f"{MODULE_PATH}.check_response")
    @patch(f"{MODULE_PATH}.PolicyrulenetworkaccesspatchRules")
    @patch(f"{MODULE_PATH}.PolicyRuleNetworkAccessPatch")
    @patch(f"{MODULE_PATH}.patch_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_named_rule_changes(
        self, mock_get, mock_patch, mock_patch_model, mock_rules_model, mock_check
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(
            rule_name="restricted.1",
            effect="deny",
        )
        policy_obj = Mock()
        policy_obj.enabled = True
        rule = _rule_obj(effect="allow")
        mock_get.side_effect = [
            Mock(status_code=200, items=[policy_obj]),   # policy fetch
            Mock(status_code=200, items=[rule]),         # rule fetch
        ]
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, Mock())

        mock_patch.assert_called_once()
        assert mock_rules_model.call_args.kwargs["effect"] == "deny"
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_named_rule_missing_fails(self, mock_get):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(
            rule_name="restricted.99",
            effect="deny",
        )
        mock_module.fail_json.side_effect = Exception("fail_json called")
        policy_obj = Mock()
        policy_obj.enabled = True
        mock_get.side_effect = [
            Mock(status_code=200, items=[policy_obj]),   # policy fetch
            Mock(status_code=400, items=[]),             # rule fetch
        ]

        try:
            update_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert (
            "not found" in mock_module.fail_json.call_args.kwargs["msg"]
        )

    @patch(f"{MODULE_PATH}.check_response")
    @patch(f"{MODULE_PATH}.PolicyrulenetworkaccesspostRules")
    @patch(f"{MODULE_PATH}.PolicyRuleNetworkAccessPost")
    @patch(f"{MODULE_PATH}.post_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_adds_new_rule_when_no_match(
        self, mock_get, mock_post, mock_post_model, mock_rule_model, mock_check
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(
            effect="deny",
            client="10.20.30.0/24",
            interfaces=["management-ssh"],
        )
        policy_obj = Mock()
        policy_obj.enabled = True
        existing_rule = _rule_obj(
            name="restricted.1",
            effect="allow",
            client="*",
            interfaces=["management-ssh"],
        )
        mock_get.side_effect = [
            Mock(status_code=200, items=[policy_obj]),        # policy fetch
            Mock(status_code=200, items=[existing_rule]),     # rules list
        ]
        mock_post.return_value = Mock(status_code=200)

        update_policy(mock_module, Mock())

        mock_post.assert_called_once()
        assert mock_rule_model.call_args.kwargs["effect"] == "deny"
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.check_response")
    @patch(f"{MODULE_PATH}.PolicyrulenetworkaccesspatchRules")
    @patch(f"{MODULE_PATH}.PolicyRuleNetworkAccessPatch")
    @patch(f"{MODULE_PATH}.patch_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_reorders_matched_rule(
        self, mock_get, mock_patch, mock_patch_model, mock_rules_model, mock_check
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(
            effect="allow",
            client="*",
            interfaces=["management-ssh"],
            index=3,
        )
        policy_obj = Mock()
        policy_obj.enabled = True
        matching_rule = _rule_obj(
            name="restricted.1",
            effect="allow",
            client="*",
            interfaces=["management-ssh"],
            index=1,
        )
        mock_get.side_effect = [
            Mock(status_code=200, items=[policy_obj]),
            Mock(status_code=200, items=[matching_rule]),
        ]
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, Mock())

        mock_patch.assert_called_once()
        assert mock_rules_model.call_args.kwargs["index"] == 3
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.check_response")
    @patch(f"{MODULE_PATH}.Reference")
    @patch(f"{MODULE_PATH}.Arrays")
    @patch(f"{MODULE_PATH}.patch_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_activates_policy(
        self, mock_get, mock_patch, mock_arrays, mock_reference, mock_check
    ):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(active=True)
        policy_obj = Mock()
        policy_obj.enabled = True
        existing_rule = _rule_obj()
        array_obj = Mock()
        array_obj.network_access_policy = None
        mock_get.side_effect = [
            Mock(status_code=200, items=[policy_obj]),       # policy fetch
            Mock(status_code=200, items=[existing_rule]),    # rules-present check
            Mock(status_code=200, items=[array_obj]),        # arrays fetch
        ]
        mock_patch.return_value = Mock(status_code=200)

        update_policy(mock_module, Mock())

        mock_patch.assert_called_once()
        mock_reference.assert_called_once_with(name="restricted")
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_activate_with_no_rules_fails(self, mock_get):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(active=True)
        mock_module.fail_json.side_effect = Exception("fail_json called")
        policy_obj = Mock()
        policy_obj.enabled = True
        mock_get.side_effect = [
            Mock(status_code=200, items=[policy_obj]),   # policy fetch
            Mock(status_code=200, items=[]),             # empty rules list
        ]

        try:
            update_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert "no rules" in mock_module.fail_json.call_args.kwargs["msg"]

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_update_activate_already_active_no_change(self, mock_get):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(active=True)
        policy_obj = Mock()
        policy_obj.enabled = True
        existing_rule = _rule_obj()
        array_obj = Mock()
        array_obj.network_access_policy = Mock()
        array_obj.network_access_policy.name = "restricted"
        mock_get.side_effect = [
            Mock(status_code=200, items=[policy_obj]),
            Mock(status_code=200, items=[existing_rule]),
            Mock(status_code=200, items=[array_obj]),
        ]

        update_policy(mock_module, Mock())

        mock_module.exit_json.assert_called_once_with(changed=False)


class TestDeletePolicy:
    """Tests for delete_policy"""

    def test_delete_policy_check_mode(self):
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _base_params()
        with patch(f"{MODULE_PATH}.get_with_context") as mock_get:
            mock_get.return_value = Mock(status_code=200, items=[Mock(
                network_access_policy=None
            )])
            delete_policy(mock_module, Mock())

        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.delete_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_delete_policy_success(self, mock_get, mock_delete):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params()
        array_obj = Mock()
        array_obj.network_access_policy = None
        mock_get.return_value = Mock(status_code=200, items=[array_obj])
        mock_delete.return_value = Mock(status_code=200)

        delete_policy(mock_module, Mock())

        mock_delete.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    @patch(f"{MODULE_PATH}.get_with_context")
    def test_delete_active_policy_fails(self, mock_get):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params()
        mock_module.fail_json.side_effect = Exception("fail_json called")
        array_obj = Mock()
        array_obj.network_access_policy = Mock()
        array_obj.network_access_policy.name = "restricted"
        mock_get.return_value = Mock(status_code=200, items=[array_obj])

        try:
            delete_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert (
            "active array policy"
            in mock_module.fail_json.call_args.kwargs["msg"]
        )

    @patch(f"{MODULE_PATH}.delete_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_delete_policy_api_failure(self, mock_get, mock_delete):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params()
        mock_module.fail_json.side_effect = Exception("fail_json called")
        array_obj = Mock()
        array_obj.network_access_policy = None
        mock_get.return_value = Mock(status_code=200, items=[array_obj])
        err = Mock()
        err.message = "boom"
        mock_delete.return_value = Mock(status_code=400, errors=[err])

        try:
            delete_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        assert (
            "Deletion of network-access policy"
            in mock_module.fail_json.call_args.kwargs["msg"]
        )

    @patch(f"{MODULE_PATH}.delete_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_delete_missing_rule_no_change(self, mock_get, mock_delete):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(rule_name="restricted.99")
        mock_module.exit_json.side_effect = Exception("exit_json called")
        mock_get.return_value = Mock(status_code=400)

        try:
            delete_policy(mock_module, Mock())
        except Exception:
            pass

        mock_module.exit_json.assert_called_once_with(changed=False)
        mock_delete.assert_not_called()

    @patch(f"{MODULE_PATH}.delete_with_context")
    @patch(f"{MODULE_PATH}.get_with_context")
    def test_delete_rule_success(self, mock_get, mock_delete):
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = _base_params(rule_name="restricted.1")
        mock_get.return_value = Mock(status_code=200, items=[_rule_obj()])
        mock_delete.return_value = Mock(status_code=200)

        delete_policy(mock_module, Mock())

        mock_delete.assert_called_once()
        mock_module.exit_json.assert_called_once_with(changed=True)

    def test_delete_rule_check_mode(self):
        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = _base_params(rule_name="restricted.1")
        with patch(f"{MODULE_PATH}.get_with_context") as mock_get:
            mock_get.return_value = Mock(status_code=200, items=[_rule_obj()])
            delete_policy(mock_module, Mock())

        mock_module.exit_json.assert_called_once_with(changed=True)
