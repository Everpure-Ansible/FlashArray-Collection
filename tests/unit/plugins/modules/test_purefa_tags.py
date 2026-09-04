# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_tags module."""

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

from plugins.modules.purefa_tags import (
    RESOURCES,
    apply_tags,
    parse_kvp,
    read_tags,
    remove_tags,
    _api_name,
    _compares_copyable,
    _resource_args,
)


def make_module(**params):
    """An AnsibleModule stand-in whose fail_json raises, as the real one does"""
    module = Mock()
    module.check_mode = False
    base = {
        "resource_type": "host",
        "name": "host1",
        "namespace": "default",
        "kvp": None,
        "keys": None,
        "copyable": None,
        "state": "present",
        "context": "",
    }
    base.update(params)
    module.params = base
    module.fail_json.side_effect = SystemExit(1)
    return module


def make_tag(key, value, copyable=True):
    tag = Mock()
    tag.key = key
    tag.value = value
    tag.copyable = copyable
    return tag


class TestResourceMap:
    """The map is the module's whole reason for existing"""

    def test_every_resource_has_an_api_name_and_version(self):
        for resource_type, (api_name, version) in RESOURCES.items():
            assert api_name, resource_type
            assert version.startswith("2."), resource_type

    def test_versions_are_per_resource_not_uniform(self):
        """Test the map really does carry different floors

        A single version for every type would have been wrong - the endpoints
        arrived across 2.2 to 2.44.
        """
        versions = {version for _api, version in RESOURCES.values()}
        assert len(versions) > 1
        assert "2.2" in versions and "2.44" in versions

    def test_volumes_are_not_included(self):
        """Volumes keep their own module, so they must not appear here"""
        assert "volume" not in RESOURCES

    def test_api_name_is_the_plural_api_form(self):
        assert _api_name(make_module(resource_type="host_group")) == "host_groups"
        assert _api_name(make_module(resource_type="array")) == "arrays"


class TestResourceArgs:
    """Test cases for _resource_args function"""

    def test_named_resource_passes_its_name(self):
        assert _resource_args(make_module()) == {"resource_names": ["host1"]}

    def test_array_passes_no_name(self):
        """The array is a singleton, so its endpoints take no resource name"""
        module = make_module(resource_type="array", name=None)

        assert _resource_args(module) == {}


class TestComparesCopyable:
    """copyable is only honoured by the volume family"""

    def test_not_compared_when_unset(self):
        assert _compares_copyable(make_module(resource_type="volume_group")) is False

    def test_compared_for_volume_group(self):
        module = make_module(resource_type="volume_group", copyable=False)

        assert _compares_copyable(module) is True

    def test_not_compared_for_host(self):
        """Test copyable is ignored for a host

        The array stores true whatever is sent, so comparing it would report a
        change on every run.
        """
        module = make_module(resource_type="host", copyable=False)

        assert _compares_copyable(module) is False


class TestParseKvp:
    """Test cases for parse_kvp function"""

    def test_splits_on_the_first_colon_only(self):
        """Test a value may itself contain colons"""
        module = make_module(kvp=["url:https://example.com:8443"])

        assert parse_kvp(module) == [("url", "https://example.com:8443")]

    def test_multiple_pairs(self):
        module = make_module(kvp=["a:1", "b:2"])

        assert parse_kvp(module) == [("a", "1"), ("b", "2")]

    def test_empty_value_is_allowed(self):
        module = make_module(kvp=["a:"])

        assert parse_kvp(module) == [("a", "")]

    def test_missing_colon_fails(self):
        module = make_module(kvp=["nocolon"])

        with pytest.raises(SystemExit):
            parse_kvp(module)

        assert "key:value form" in module.fail_json.call_args[1]["msg"]

    def test_empty_key_fails(self):
        module = make_module(kvp=[":value"])

        with pytest.raises(SystemExit):
            parse_kvp(module)

        assert "empty key" in module.fail_json.call_args[1]["msg"]

    def test_no_kvp_is_an_empty_list(self):
        assert parse_kvp(make_module()) == []


class TestReadTags:
    """Test cases for read_tags function"""

    @patch("plugins.modules.purefa_tags.get_with_context")
    def test_read_always_sends_the_namespace(self, mock_get):
        """Test the namespace is part of every read

        A read that leaves it out comes back with the default namespace only,
        which would hide tags in any other namespace.
        """
        module = make_module(namespace="other")
        mock_get.return_value = Mock(status_code=200, items=[make_tag("a", "1")])

        read_tags(module, Mock())

        kwargs = mock_get.call_args[1]
        assert kwargs["namespaces"] == ["other"]
        assert kwargs["resource_names"] == ["host1"]
        assert mock_get.call_args[0][1] == "get_hosts_tags"

    @patch("plugins.modules.purefa_tags.get_with_context")
    def test_read_for_the_array_sends_no_resource_name(self, mock_get):
        module = make_module(resource_type="array", name=None)
        mock_get.return_value = Mock(status_code=200, items=[])

        read_tags(module, Mock())

        assert "resource_names" not in mock_get.call_args[1]
        assert mock_get.call_args[0][1] == "get_arrays_tags"

    @patch("plugins.modules.purefa_tags.check_response")
    @patch("plugins.modules.purefa_tags.get_with_context")
    def test_read_failure_is_surfaced(self, mock_get, mock_check):
        """Test a bad read goes through check_response

        Tagging something that does not exist fails here, with the array's own
        message naming the resource type.
        """
        module = make_module()
        mock_get.return_value = Mock(status_code=400, items=[])

        read_tags(module, Mock())

        mock_check.assert_called_once()


class TestApplyTags:
    """Test cases for apply_tags function"""

    @patch("plugins.modules.purefa_tags._write_tags")
    def test_requires_kvp(self, mock_write):
        module = make_module()

        with pytest.raises(SystemExit):
            apply_tags(module, Mock(), [])

        assert "kvp is required" in module.fail_json.call_args[1]["msg"]
        mock_write.assert_not_called()

    @patch("plugins.modules.purefa_tags._write_tags")
    def test_writes_a_missing_tag(self, mock_write):
        module = make_module(kvp=["a:1"])
        array = Mock()

        apply_tags(module, array, [])

        mock_write.assert_called_once_with(module, array, [("a", "1")])
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tags._write_tags")
    def test_matching_tag_is_no_change(self, mock_write):
        """Test a put is not issued when nothing differs

        The array accepts a put whether or not anything changes, so the
        difference has to be worked out in the module.
        """
        module = make_module(kvp=["a:1"])

        apply_tags(module, Mock(), [make_tag("a", "1")])

        mock_write.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_tags._write_tags")
    def test_changed_value_is_written(self, mock_write):
        module = make_module(kvp=["a:2"])
        array = Mock()

        apply_tags(module, array, [make_tag("a", "1")])

        mock_write.assert_called_once_with(module, array, [("a", "2")])
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tags._write_tags")
    def test_only_the_differing_pairs_are_written(self, mock_write):
        module = make_module(kvp=["a:1", "b:9"])
        array = Mock()

        apply_tags(module, array, [make_tag("a", "1"), make_tag("b", "2")])

        mock_write.assert_called_once_with(module, array, [("b", "9")])

    @patch("plugins.modules.purefa_tags._write_tags")
    def test_copyable_difference_counts_for_a_volume_group(self, mock_write):
        module = make_module(
            resource_type="volume_group", name="vg1", kvp=["a:1"], copyable=False
        )
        array = Mock()

        apply_tags(module, array, [make_tag("a", "1", copyable=True)])

        mock_write.assert_called_once_with(module, array, [("a", "1")])
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tags._write_tags")
    def test_copyable_difference_ignored_for_a_host(self, mock_write):
        """Test an ignored copyable does not produce a change every run"""
        module = make_module(kvp=["a:1"], copyable=False)

        apply_tags(module, Mock(), [make_tag("a", "1", copyable=True)])

        mock_write.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_tags._write_tags")
    def test_check_mode_predicts_without_writing(self, mock_write):
        module = make_module(kvp=["a:1"])
        module.check_mode = True

        apply_tags(module, Mock(), [])

        mock_write.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestRemoveTags:
    """Test cases for remove_tags function"""

    @patch("plugins.modules.purefa_tags.delete_with_context")
    def test_requires_keys_or_kvp(self, mock_delete):
        module = make_module(state="absent")

        with pytest.raises(SystemExit):
            remove_tags(module, Mock(), [])

        assert "keys or kvp is required" in module.fail_json.call_args[1]["msg"]
        mock_delete.assert_not_called()

    @patch("plugins.modules.purefa_tags.check_response")
    @patch("plugins.modules.purefa_tags.delete_with_context")
    def test_removes_only_what_is_there(self, mock_delete, mock_check):
        module = make_module(state="absent", keys=["a", "nosuch"])
        mock_delete.return_value = Mock(status_code=200)

        remove_tags(module, Mock(), [make_tag("a", "1")])

        assert mock_delete.call_args[1]["keys"] == ["a"]
        assert mock_delete.call_args[1]["namespaces"] == ["default"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tags.delete_with_context")
    def test_nothing_to_remove_is_no_change(self, mock_delete):
        """Test a delete is not issued for a key the resource does not have

        The array accepts a delete of a missing key, so the module has to
        decide for itself.
        """
        module = make_module(state="absent", keys=["nosuch"])

        remove_tags(module, Mock(), [make_tag("a", "1")])

        mock_delete.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    @patch("plugins.modules.purefa_tags.check_response")
    @patch("plugins.modules.purefa_tags.delete_with_context")
    def test_kvp_keys_are_used_when_keys_is_absent(self, mock_delete, mock_check):
        """Test removal by kvp uses the keys and ignores the values

        purefa_volume_tags compares 1-tuples against strings here and so never
        removes anything; this asserts the working behaviour.
        """
        module = make_module(state="absent", kvp=["a:whatever"])
        mock_delete.return_value = Mock(status_code=200)

        remove_tags(module, Mock(), [make_tag("a", "1")])

        assert mock_delete.call_args[1]["keys"] == ["a"]
        module.exit_json.assert_called_once_with(changed=True)

    @patch("plugins.modules.purefa_tags.check_response")
    @patch("plugins.modules.purefa_tags.delete_with_context")
    def test_keys_wins_over_kvp(self, mock_delete, mock_check):
        module = make_module(state="absent", keys=["b"], kvp=["a:1"])
        mock_delete.return_value = Mock(status_code=200)

        remove_tags(module, Mock(), [make_tag("a", "1"), make_tag("b", "2")])

        assert mock_delete.call_args[1]["keys"] == ["b"]

    @patch("plugins.modules.purefa_tags.delete_with_context")
    def test_check_mode_predicts_without_deleting(self, mock_delete):
        module = make_module(state="absent", keys=["a"])
        module.check_mode = True

        remove_tags(module, Mock(), [make_tag("a", "1")])

        mock_delete.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)


class TestMain:
    """Test cases for the main dispatch"""

    @patch("plugins.modules.purefa_tags.get_array")
    @patch("plugins.modules.purefa_tags.AnsibleModule")
    def test_main_no_purestorage_sdk(self, mock_am, mock_ga):
        import plugins.modules.purefa_tags as mod

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

    @patch("plugins.modules.purefa_tags.apply_tags")
    @patch("plugins.modules.purefa_tags.read_tags")
    @patch("plugins.modules.purefa_tags.check_api_version")
    @patch("plugins.modules.purefa_tags.get_array")
    @patch("plugins.modules.purefa_tags.AnsibleModule")
    def test_main_present_applies(
        self, mock_am, mock_ga, mock_api, mock_read, mock_apply
    ):
        import plugins.modules.purefa_tags as mod

        module = make_module(kvp=["a:1"])
        mock_am.return_value = module
        array = Mock()
        mock_ga.return_value = array
        current = [make_tag("a", "1")]
        mock_read.return_value = current

        mod.main()

        mock_apply.assert_called_once_with(module, array, current)

    @patch("plugins.modules.purefa_tags.remove_tags")
    @patch("plugins.modules.purefa_tags.read_tags")
    @patch("plugins.modules.purefa_tags.check_api_version")
    @patch("plugins.modules.purefa_tags.get_array")
    @patch("plugins.modules.purefa_tags.AnsibleModule")
    def test_main_absent_removes(
        self, mock_am, mock_ga, mock_api, mock_read, mock_remove
    ):
        import plugins.modules.purefa_tags as mod

        module = make_module(state="absent", keys=["a"])
        mock_am.return_value = module
        array = Mock()
        mock_ga.return_value = array
        mock_read.return_value = []

        mod.main()

        mock_remove.assert_called_once_with(module, array, [])

    @patch("plugins.modules.purefa_tags.apply_tags")
    @patch("plugins.modules.purefa_tags.read_tags")
    @patch("plugins.modules.purefa_tags.check_api_version")
    @patch("plugins.modules.purefa_tags.get_array")
    @patch("plugins.modules.purefa_tags.AnsibleModule")
    def test_main_checks_the_version_for_the_requested_type(
        self, mock_am, mock_ga, mock_api, mock_read, mock_apply
    ):
        """Test the guardrail is the version for that resource type

        protection_group_snapshot tags arrived in 2.44, far later than the
        2.2 of volume snapshots.
        """
        import plugins.modules.purefa_tags as mod

        module = make_module(
            resource_type="protection_group_snapshot", name="pg.1", kvp=["a:1"]
        )
        mock_am.return_value = module
        mock_ga.return_value = Mock()
        mock_read.return_value = []

        mod.main()

        assert mock_api.call_args[0][1] == "2.44"
