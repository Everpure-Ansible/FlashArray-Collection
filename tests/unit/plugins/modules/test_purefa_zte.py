# Copyright: (c) 2026, Pure Storage Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefa_zte module."""

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

# Create a mock version module with real LooseVersion
mock_version_module = MagicMock()
from packaging.version import Version as LooseVersion

mock_version_module.LooseVersion = LooseVersion
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    mock_version_module
)

from plugins.modules.purefa_zte import (
    ACTIVE_STATES,
    FAILED_STATES,
    FINALIZABLE_STATES,
    cancel_zte,
    erasure_facts,
    erasure_status,
    finalize_zte,
    get_erasure,
    response_erasure,
    start_zte,
    zte_status,
)


def _erasure(status="", details=None, progress=None, certificate=None):
    """Build a mock erasure object.

    ``spec`` keeps ``getattr(obj, name, default)`` honest - an attribute that
    is not listed raises AttributeError rather than auto-creating a Mock, which
    is what the pypureclient models do for unset fields.
    """
    attrs = {"status": status}
    if details is not None:
        attrs["details"] = details
    if progress is not None:
        attrs["image_download_progress"] = progress
    if certificate is not None:
        attrs["sanitization_certificate"] = certificate
    obj = Mock(spec=list(attrs))
    for name, value in attrs.items():
        setattr(obj, name, value)
    return obj


def _module(check_mode=False, **params):
    module = Mock()
    module.check_mode = check_mode
    module.params = {
        "state": "status",
        "eradicate": False,
        "preserve_config": True,
        "skip_phonehome_check": False,
        "reinstall_image": False,
        "image_source": "auto",
        "image_version": None,
    }
    module.params.update(params)
    return module


class TestStateSets:
    """The status sets must match the values the REST API can return."""

    def test_state_sets_are_disjoint(self):
        assert not ACTIVE_STATES & FAILED_STATES
        assert FINALIZABLE_STATES <= ACTIVE_STATES

    def test_failed_states_cover_every_api_failure(self):
        assert FAILED_STATES == {"reset_failed", "download_failed", "reimage_failed"}


class TestErasureFacts:
    """Tests for erasure_facts / erasure_status / response_erasure"""

    def test_facts_when_no_erasure(self):
        assert erasure_facts(None) == {
            "status": "",
            "details": "",
            "image_download_progress": None,
            "sanitization_certificate": "",
        }

    def test_facts_populated(self):
        current = _erasure(
            status="waiting_for_finalize", details="all good", certificate="CERT"
        )
        facts = erasure_facts(current)
        assert facts["status"] == "waiting_for_finalize"
        assert facts["details"] == "all good"
        assert facts["sanitization_certificate"] == "CERT"

    def test_zero_download_progress_is_preserved(self):
        """0 is a real progress value and must not become an empty string."""
        facts = erasure_facts(_erasure(status="downloading", progress=0.0))
        assert facts["image_download_progress"] == 0.0

    def test_partial_download_progress_is_preserved(self):
        facts = erasure_facts(_erasure(status="downloading", progress=0.5))
        assert facts["image_download_progress"] == 0.5

    def test_unset_fields_default_cleanly(self):
        facts = erasure_facts(_erasure(status="resetting"))
        assert facts["details"] == ""
        assert facts["sanitization_certificate"] == ""
        assert facts["image_download_progress"] is None

    def test_erasure_status_of_none(self):
        assert erasure_status(None) == ""

    def test_response_erasure_empty(self):
        assert response_erasure(Mock(items=[])) is None
        assert response_erasure(Mock(items=None)) is None

    def test_response_erasure_returns_first_item(self):
        item = _erasure(status="resetting")
        assert response_erasure(Mock(items=[item])) is item


class TestGetErasure:
    """Tests for get_erasure"""

    @patch("plugins.modules.purefa_zte.check_response")
    def test_returns_none_when_no_reset_running(self, mock_check):
        array = Mock()
        array.get_arrays_erasures.return_value = Mock(status_code=200, items=[])
        module = _module()

        assert get_erasure(module, array) is None
        mock_check.assert_called_once()

    @patch("plugins.modules.purefa_zte.check_response")
    def test_returns_current_erasure(self, mock_check):
        item = _erasure(status="resetting")
        array = Mock()
        array.get_arrays_erasures.return_value = Mock(status_code=200, items=[item])

        assert get_erasure(_module(), array) is item

    @patch("plugins.modules.purefa_zte.check_response")
    def test_api_error_is_not_silently_swallowed(self, mock_check):
        """A non-200 must fail the module, not look like 'no reset running'."""
        array = Mock()
        array.get_arrays_erasures.return_value = Mock(status_code=500, items=[])
        module = _module()

        get_erasure(module, array)

        mock_check.assert_called_once()
        assert mock_check.call_args[0][1] is module


class TestZteStatus:
    """Tests for zte_status"""

    def test_status_never_reports_change(self):
        module = _module()
        zte_status(module, _erasure(status="resetting"))
        module.exit_json.assert_called_once()
        assert module.exit_json.call_args.kwargs["changed"] is False


class TestStartZte:
    """Tests for start_zte"""

    def test_requires_eradicate(self):
        module = _module(eradicate=False)
        array = Mock()

        start_zte(module, array, None)

        module.fail_json.assert_called_once()
        array.post_arrays_erasures.assert_not_called()

    def test_check_mode_does_not_call_api(self):
        module = _module(check_mode=True, eradicate=True)
        array = Mock()

        start_zte(module, array, None)

        array.post_arrays_erasures.assert_not_called()
        assert module.exit_json.call_args.kwargs["changed"] is True

    def test_idempotent_while_reset_in_progress(self):
        for status in sorted(ACTIVE_STATES):
            module = _module(eradicate=True)
            array = Mock()

            start_zte(module, array, _erasure(status=status))

            array.post_arrays_erasures.assert_not_called()
            assert module.exit_json.call_args.kwargs["changed"] is False
            assert module.exit_json.call_args.kwargs["zte"]["status"] == status

    def test_failed_reset_is_reported_not_restarted(self):
        """A failed reset must be cancelled first, not silently re-POSTed."""
        for status in sorted(FAILED_STATES):
            module = _module(eradicate=True)
            array = Mock()

            start_zte(module, array, _erasure(status=status, details="disk error"))

            array.post_arrays_erasures.assert_not_called()
            module.exit_json.assert_not_called()
            msg = module.fail_json.call_args.kwargs["msg"]
            assert status in msg
            assert "state: cancel" in msg

    @patch("plugins.modules.purefa_zte.check_response")
    def test_start_preserving_configuration(self, mock_check):
        module = _module(eradicate=True, preserve_config=True)
        array = Mock()
        array.post_arrays_erasures.return_value = Mock(
            status_code=200, items=[_erasure(status="resetting")]
        )

        start_zte(module, array, None)

        kwargs = array.post_arrays_erasures.call_args.kwargs
        assert kwargs["eradicate_all_data"] is True
        assert kwargs["preserve_configuration_data"] == ["all"]
        assert kwargs["skip_phonehome_check"] is False
        assert module.exit_json.call_args.kwargs["changed"] is True
        assert module.exit_json.call_args.kwargs["zte"]["status"] == "resetting"

    @patch("plugins.modules.purefa_zte.check_response")
    def test_start_darksite_without_preserving_configuration(self, mock_check):
        module = _module(
            eradicate=True, preserve_config=False, skip_phonehome_check=True
        )
        array = Mock()
        array.post_arrays_erasures.return_value = Mock(status_code=200, items=[])

        start_zte(module, array, None)

        kwargs = array.post_arrays_erasures.call_args.kwargs
        assert kwargs["preserve_configuration_data"] == []
        assert kwargs["skip_phonehome_check"] is True

    @patch("plugins.modules.purefa_zte.check_response")
    def test_start_does_not_reread_state_from_array(self, mock_check):
        """The REST service goes away during the wipe, so no follow-up GET."""
        module = _module(eradicate=True)
        array = Mock()
        array.post_arrays_erasures.return_value = Mock(status_code=200, items=[])

        start_zte(module, array, None)

        array.get_arrays_erasures.assert_not_called()


class TestFinalizeZte:
    """Tests for finalize_zte"""

    def test_requires_eradicate(self):
        module = _module(eradicate=False)
        array = Mock()

        finalize_zte(module, array, _erasure(status="waiting_for_finalize"))

        module.fail_json.assert_called_once()
        array.patch_arrays_erasures.assert_not_called()

    def test_idempotent_after_successful_finalize(self):
        """A finalized array reports no erasure - re-running must not fail."""
        module = _module(eradicate=True)
        array = Mock()

        finalize_zte(module, array, None)

        module.fail_json.assert_not_called()
        array.patch_arrays_erasures.assert_not_called()
        assert module.exit_json.call_args.kwargs["changed"] is False
        assert module.exit_json.call_args.kwargs["zte"]["status"] == ""

    def test_refuses_to_finalize_a_running_reset(self):
        module = _module(eradicate=True)
        array = Mock()

        finalize_zte(module, array, _erasure(status="resetting"))

        array.patch_arrays_erasures.assert_not_called()
        assert "not ready" in module.fail_json.call_args.kwargs["msg"]

    def test_refuses_to_finalize_a_failed_reset(self):
        for status in sorted(FAILED_STATES):
            module = _module(eradicate=True)
            array = Mock()

            finalize_zte(module, array, _erasure(status=status, details="boom"))

            array.patch_arrays_erasures.assert_not_called()
            msg = module.fail_json.call_args.kwargs["msg"]
            assert "state: cancel" in msg
            assert "boom" in msg

    def test_check_mode_does_not_call_api(self):
        module = _module(check_mode=True, eradicate=True)
        array = Mock()

        finalize_zte(module, array, _erasure(status="waiting_for_finalize"))

        array.patch_arrays_erasures.assert_not_called()
        assert module.exit_json.call_args.kwargs["changed"] is True

    @patch("plugins.modules.purefa_zte.check_response")
    def test_finalize_option_one(self, mock_check):
        module = _module(eradicate=True, reinstall_image=False)
        array = Mock()
        array.patch_arrays_erasures.return_value = Mock(status_code=200, items=[])

        finalize_zte(module, array, _erasure(status="waiting_for_finalize"))

        kwargs = array.patch_arrays_erasures.call_args.kwargs
        assert kwargs["finalize"] is True
        assert kwargs["eradicate_all_data"] is True
        assert kwargs["delete_sanitization_certificate"] is True
        assert kwargs["reinstall_image"] is False
        assert "erasure_patch" not in kwargs
        assert module.exit_json.call_args.kwargs["changed"] is True

    @patch("plugins.modules.purefa_zte.flasharray")
    @patch("plugins.modules.purefa_zte.check_response")
    def test_finalize_option_two_darksite(self, mock_check, mock_fa):
        module = _module(
            eradicate=True,
            reinstall_image=True,
            image_source="https://example.com/purity.sh",
            image_version="6.6.8",
        )
        array = Mock()
        array.patch_arrays_erasures.return_value = Mock(status_code=200, items=[])

        finalize_zte(module, array, _erasure(status="downloaded"))

        assert array.patch_arrays_erasures.call_args.kwargs["reinstall_image"] is True
        patch_kwargs = mock_fa.ArrayErasurePatch.call_args.kwargs
        assert patch_kwargs["image_source"] == "https://example.com/purity.sh"
        assert patch_kwargs["image_version"] == "6.6.8"


class TestCancelZte:
    """Tests for cancel_zte"""

    def test_no_erasure_is_a_no_op(self):
        module = _module()
        array = Mock()

        cancel_zte(module, array, None)

        array.delete_arrays_erasures.assert_not_called()
        assert module.exit_json.call_args.kwargs["changed"] is False

    def test_healthy_reset_is_not_cancelled(self):
        """The array only accepts a cancel for a failed reset."""
        for status in sorted(ACTIVE_STATES):
            module = _module()
            array = Mock()

            cancel_zte(module, array, _erasure(status=status))

            array.delete_arrays_erasures.assert_not_called()
            assert module.exit_json.call_args.kwargs["changed"] is False
            assert module.exit_json.call_args.kwargs["zte"]["status"] == status

    def test_check_mode_does_not_call_api(self):
        module = _module(check_mode=True)
        array = Mock()

        cancel_zte(module, array, _erasure(status="reset_failed"))

        array.delete_arrays_erasures.assert_not_called()
        assert module.exit_json.call_args.kwargs["changed"] is True

    @patch("plugins.modules.purefa_zte.check_response")
    def test_cancels_each_failed_state(self, mock_check):
        for status in sorted(FAILED_STATES):
            module = _module()
            array = Mock()
            array.delete_arrays_erasures.return_value = Mock(status_code=200, items=[])

            cancel_zte(module, array, _erasure(status=status))

            array.delete_arrays_erasures.assert_called_once_with()
            assert module.exit_json.call_args.kwargs["changed"] is True
            assert module.exit_json.call_args.kwargs["zte"]["status"] == ""
