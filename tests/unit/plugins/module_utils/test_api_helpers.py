# Copyright: (c) 2026, Pure Storage Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for api_helpers module utilities."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock, patch

import pytest

# Mock external dependencies before importing api_helpers
sys.modules["pypureclient"] = MagicMock()
sys.modules["pypureclient.flasharray"] = MagicMock()
sys.modules["ansible_collections"] = MagicMock()
sys.modules["ansible_collections.everpure"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray.plugins"] = MagicMock()
sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils"] = (
    MagicMock()
)

# Mock the LooseVersion class needed by api_helpers
mock_version = MagicMock()


class MockLooseVersion:
    """Mock LooseVersion that supports comparison."""

    def __init__(self, version):
        self.version = version
        self.parts = [int(p) for p in version.split(".")]

    def __le__(self, other):
        return self.parts <= other.parts

    def __lt__(self, other):
        return self.parts < other.parts

    def __ge__(self, other):
        return self.parts >= other.parts

    def __gt__(self, other):
        return self.parts > other.parts

    def __eq__(self, other):
        return self.parts == other.parts


sys.modules["ansible_collections.everpure.flasharray.plugins.module_utils.version"] = (
    MagicMock()
)
sys.modules[
    "ansible_collections.everpure.flasharray.plugins.module_utils.version"
].LooseVersion = MockLooseVersion

from plugins.module_utils.api_helpers import (
    check_response,
    get_cached_api_version,
    check_api_version,
    get_local_array_name,
    get_with_context,
    wait_for,
)


class TestCheckResponse:
    """Tests for check_response function."""

    def test_success_response(self, mock_module, mock_success_response):
        """Test that success response does not raise."""
        # Should not raise - no return value expected
        check_response(mock_success_response, mock_module, "Test operation")
        # Verify fail_json was NOT called
        mock_module.fail_json.assert_not_called()

    def test_error_response_with_message(self, mock_module, mock_error_response):
        """Test that error response calls fail_json with error message."""
        try:
            check_response(mock_error_response, mock_module, "Test operation")
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert "Test operation failed" in call_kwargs["msg"]
        assert "Test error message" in call_kwargs["msg"]
        assert call_kwargs["status_code"] == 400
        assert call_kwargs["changed"] is False

    def test_error_response_empty_errors(self, mock_module, mock_empty_error_response):
        """Test that error response with no errors uses 'Unknown error'."""
        try:
            check_response(mock_empty_error_response, mock_module, "Test operation")
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert "Unknown error" in call_kwargs["msg"]

    def test_response_without_status_code(self, mock_module):
        """Test that response without status_code attribute is ignored."""
        response = Mock(spec=[])  # No attributes
        # Should not raise
        check_response(response, mock_module, "Test operation")
        mock_module.fail_json.assert_not_called()

    def test_custom_operation_message(self, mock_module, mock_error_response):
        """Test that custom operation message is included in error."""
        try:
            check_response(mock_error_response, mock_module, "Create volume 'test-vol'")
        except Exception:
            pass

        call_kwargs = mock_module.fail_json.call_args[1]
        assert "Create volume 'test-vol' failed" in call_kwargs["msg"]


def _mock_arrays_response(name="local-array", status_code=200):
    """Response for get_arrays(), which returns only the array being addressed."""
    array = Mock()
    # Assigned rather than passed to Mock(), where name is the mock's own name
    array.name = name
    return Mock(status_code=status_code, items=[array], errors=[])


class TestGetLocalArrayName:
    """Tests for get_local_array_name function."""

    def test_returns_the_array_name(self, mock_module):
        """Test that the name of the array being addressed is returned."""
        client = Mock()
        client.get_arrays.return_value = _mock_arrays_response("MUCFA21")

        assert get_local_array_name(client, mock_module) == "MUCFA21"
        mock_module.fail_json.assert_not_called()

    def test_error_response_fails_the_module(self, mock_module):
        """Test that a failed read is reported rather than returning nothing."""
        client = Mock()
        client.get_arrays.return_value = _mock_arrays_response(status_code=400)

        with pytest.raises(Exception):
            get_local_array_name(client, mock_module)

        assert "local array name" in mock_module.fail_json.call_args[1]["msg"]

    def test_empty_response_fails_the_module(self, mock_module):
        """Test that no array at all fails rather than raising IndexError."""
        client = Mock()
        client.get_arrays.return_value = Mock(status_code=200, items=[])

        with pytest.raises(Exception):
            get_local_array_name(client, mock_module)

        mock_module.fail_json.assert_called_once()

    def test_missing_name_fails_the_module(self, mock_module):
        """Test that an array reporting no name fails rather than returning None."""
        client = Mock()
        client.get_arrays.return_value = _mock_arrays_response(None)

        with pytest.raises(Exception):
            get_local_array_name(client, mock_module)

        mock_module.fail_json.assert_called_once()


class TestGetCachedApiVersion:
    """Tests for get_cached_api_version function."""

    def test_returns_version(self):
        """Test that function returns API version."""
        # Create a fresh mock without _cached_api_version
        array = Mock(spec=["get_rest_version"])
        array.get_rest_version.return_value = "2.38"

        result = get_cached_api_version(array)
        assert result == "2.38"

    def test_caches_version(self):
        """Test that version is cached after first call."""
        # Create a fresh mock without _cached_api_version
        array = Mock(spec=["get_rest_version"])
        array.get_rest_version.return_value = "2.38"

        # First call
        result1 = get_cached_api_version(array)
        # Second call
        result2 = get_cached_api_version(array)

        # Should only call get_rest_version once
        array.get_rest_version.assert_called_once()
        assert result1 == result2 == "2.38"

    def test_uses_cached_value(self):
        """Test that cached value is used if available."""
        # Create a mock WITH _cached_api_version already set
        array = Mock(spec=["get_rest_version", "_cached_api_version"])
        array._cached_api_version = "2.40"

        result = get_cached_api_version(array)

        # Should not call get_rest_version
        array.get_rest_version.assert_not_called()
        assert result == "2.40"


class TestCheckApiVersion:
    """Tests for check_api_version function."""

    def test_version_sufficient(self, mock_module):
        """Test that True is returned when version is sufficient."""
        # Create fresh mock without cached version
        array = Mock(spec=["get_rest_version"])
        array.get_rest_version.return_value = "2.38"

        result = check_api_version(array, "2.30", mock_module)
        assert result is True

    def test_version_exact_match(self, mock_module):
        """Test that True is returned when version exactly matches."""
        # Create fresh mock without cached version
        array = Mock(spec=["get_rest_version"])
        array.get_rest_version.return_value = "2.38"

        result = check_api_version(array, "2.38", mock_module)
        assert result is True

    def test_version_insufficient(self, mock_module):
        """Test that False is returned when version is insufficient."""
        # Create fresh mock without cached version
        array = Mock(spec=["get_rest_version"])
        array.get_rest_version.return_value = "2.38"

        result = check_api_version(array, "2.40", mock_module)
        assert result is False

    def test_version_insufficient_with_feature_name_fails(self, mock_module):
        """Test that module fails when version is insufficient and feature_name is provided."""
        # Create fresh mock without cached version
        array = Mock(spec=["get_rest_version"])
        array.get_rest_version.return_value = "2.38"

        try:
            check_api_version(array, "2.40", mock_module, feature_name="SafeMode")
        except Exception:
            pass

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert "SafeMode" in call_kwargs["msg"]
        assert "2.40" in call_kwargs["msg"]
        assert "2.38" in call_kwargs["msg"]


class TestGetWithContext:
    """Tests for get_with_context function."""

    def test_calls_method_without_context(self, mock_module, mock_array):
        """Test that method is called without context_names when context is None."""
        get_with_context(
            mock_array,
            "get_volumes",
            "2.38",
            mock_module,
            names=["test-vol"],
        )

        mock_array.get_volumes.assert_called_once_with(names=["test-vol"])

    def test_calls_method_with_context(self, mock_module):
        """Test that method is called with context_names when context is provided."""
        # Create fresh mock without cached version
        array = Mock(spec=["get_rest_version", "get_volumes"])
        array.get_rest_version.return_value = "2.38"
        mock_module.params["context"] = "pod1"

        get_with_context(
            array,
            "get_volumes",
            "2.38",
            mock_module,
            names=["test-vol"],
        )

        array.get_volumes.assert_called_once_with(
            names=["test-vol"], context_names=["pod1"]
        )

    def test_no_context_when_api_version_insufficient(self, mock_module, mock_array):
        """Test that context is not added when API version is too old."""
        mock_module.params["context"] = "pod1"
        mock_array.get_rest_version.return_value = "2.30"

        get_with_context(
            mock_array,
            "get_volumes",
            "2.38",
            mock_module,
            names=["test-vol"],
        )

        # Context should NOT be included since API version is too old
        mock_array.get_volumes.assert_called_once_with(names=["test-vol"])

    def test_returns_api_response(self, mock_module, mock_array):
        """Test that function returns the API response."""
        expected_response = Mock()
        mock_array.get_volumes.return_value = expected_response

        result = get_with_context(
            mock_array,
            "get_volumes",
            "2.38",
            mock_module,
            names=["test-vol"],
        )

        assert result == expected_response

    def test_passes_all_kwargs(self, mock_module, mock_array):
        """Test that all kwargs are passed to the API method."""
        mock_module.params["context"] = None

        get_with_context(
            mock_array,
            "get_volumes",
            "2.38",
            mock_module,
            names=["vol1", "vol2"],
            destroyed=False,
            filter="name='vol*'",
        )

        mock_array.get_volumes.assert_called_once_with(
            names=["vol1", "vol2"],
            destroyed=False,
            filter="name='vol*'",
        )


class FakeClock:
    """A monotonic clock that only advances when the code under test sleeps.

    Keeps the polling tests instant while still letting them assert exactly how
    long wait_for() slept for on each iteration.
    """

    def __init__(self, start=1000.0):
        self.now = start
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock():
    """Patch the time module wait_for() uses with a controllable fake clock."""
    fake = FakeClock()
    with patch("plugins.module_utils.api_helpers.time") as mock_time:
        mock_time.monotonic = fake.monotonic
        mock_time.sleep = fake.sleep
        yield fake


def _transient():
    """A probed value that is not finished yet."""
    value = Mock()
    value.status = "creating"
    return value


def _done():
    """A probed value that is finished."""
    value = Mock()
    value.status = "ready"
    return value


class TestWaitFor:
    """Tests for the wait_for polling helper."""

    def test_already_satisfied_never_sleeps(self, mock_module, clock):
        """Test that a condition true on the first probe costs no delay."""
        finished = _done()
        probe = Mock(return_value=finished)

        result = wait_for(
            mock_module,
            probe=probe,
            is_done=lambda value: value.status == "ready",
            timeout=300,
            description="workload foo to become ready",
        )

        assert result is finished
        probe.assert_called_once_with()
        assert clock.sleeps == []
        mock_module.fail_json.assert_not_called()

    def test_polls_until_done(self, mock_module, clock):
        """Test that wait_for keeps probing, with backoff, until done."""
        finished = _done()
        probe = Mock(side_effect=[_transient(), _transient(), finished])

        result = wait_for(
            mock_module,
            probe=probe,
            is_done=lambda value: value.status == "ready",
            timeout=300,
            description="workload foo to become ready",
        )

        assert result is finished
        assert probe.call_count == 3
        # Probes first, then sleeps, so two waits for three probes
        assert clock.sleeps == [5, 7.5]

    def test_backoff_caps_at_max_interval(self, mock_module, clock):
        """Test that the interval grows by 1.5x but never past max_interval."""
        probe = Mock(side_effect=[_transient()] * 5 + [_done()])

        wait_for(
            mock_module,
            probe=probe,
            is_done=lambda value: value.status == "ready",
            timeout=1000,
            description="workload foo to become ready",
            max_interval=10,
        )

        assert clock.sleeps == [5, 7.5, 10, 10, 10]

    def test_absent_resource_is_a_valid_outcome(self, mock_module, clock):
        """Test that a probe returning None can satisfy the condition."""
        probe = Mock(side_effect=[_transient(), None])

        result = wait_for(
            mock_module,
            probe=probe,
            is_done=lambda value: value is None,
            timeout=300,
            description="workload foo to be eradicated",
        )

        assert result is None
        assert probe.call_count == 2

    def test_timeout_fails_module(self, mock_module, clock):
        """Test that exhausting the timeout fails the module."""
        probe = Mock(return_value=_transient())

        with pytest.raises(Exception, match="fail_json called"):
            wait_for(
                mock_module,
                probe=probe,
                is_done=lambda value: value.status == "ready",
                timeout=10,
                description="workload foo to become ready",
            )

        # The final sleep is clamped so the last probe lands on the deadline
        assert clock.sleeps == [5, 5]
        assert probe.call_count == 3
        call_kwargs = mock_module.fail_json.call_args[1]
        assert "Timed out after 10 seconds" in call_kwargs["msg"]
        assert "workload foo to become ready" in call_kwargs["msg"]

    def test_timeout_message_includes_detail(self, mock_module, clock):
        """Test that the array's own diagnostics are quoted on timeout."""
        with pytest.raises(Exception, match="fail_json called"):
            wait_for(
                mock_module,
                probe=Mock(return_value=_transient()),
                is_done=lambda value: False,
                timeout=5,
                description="workload foo to become ready",
                detail=lambda value: "creating volume foo-vol1",
            )

        call_kwargs = mock_module.fail_json.call_args[1]
        assert "creating volume foo-vol1" in call_kwargs["msg"]

    def test_failure_predicate_fails_module(self, mock_module, clock):
        """Test that a terminal failure fails the module without waiting out."""
        probe = Mock(return_value=_transient())

        with pytest.raises(Exception, match="fail_json called"):
            wait_for(
                mock_module,
                probe=probe,
                is_done=lambda value: False,
                timeout=300,
                description="workload foo to become ready",
                is_failed=lambda value: "placement rejected",
            )

        probe.assert_called_once_with()
        assert clock.sleeps == []
        call_kwargs = mock_module.fail_json.call_args[1]
        assert "placement rejected" in call_kwargs["msg"]
        assert "workload foo to become ready" in call_kwargs["msg"]

    def test_failure_predicate_ignored_while_healthy(self, mock_module, clock):
        """Test that a falsy is_failed result does not stop the wait."""
        finished = _done()
        probe = Mock(side_effect=[_transient(), finished])

        result = wait_for(
            mock_module,
            probe=probe,
            is_done=lambda value: value.status == "ready",
            timeout=300,
            description="workload foo to become ready",
            is_failed=lambda value: None,
        )

        assert result is finished
        mock_module.fail_json.assert_not_called()

    def test_check_mode_returns_immediately(self, mock_module, clock):
        """Test that check mode never probes - nothing was asked of the array."""
        mock_module.check_mode = True
        probe = Mock()

        result = wait_for(
            mock_module,
            probe=probe,
            is_done=lambda value: False,
            timeout=300,
            description="workload foo to become ready",
        )

        assert result is None
        probe.assert_not_called()
        assert clock.sleeps == []
        mock_module.fail_json.assert_not_called()


class TestWaitForSkipInCheckMode:
    """Some operations are safe to wait on under check mode

    A calculation that changes nothing can and should still be polled, so the
    task can report what it would have produced.
    """

    def test_polls_when_skipping_is_disabled(self, mock_module, clock):
        """Test the wait runs under check mode when told the operation is safe"""
        mock_module.check_mode = True
        finished = _done()
        probe = Mock(side_effect=[_transient(), finished])

        result = wait_for(
            mock_module,
            probe=probe,
            is_done=lambda value: value.status == "ready",
            timeout=300,
            description="a calculation to finish",
            skip_in_check_mode=False,
        )

        assert result is finished
        assert probe.call_count == 2
        assert clock.sleeps == [5]

    def test_still_fails_on_timeout_when_skipping_is_disabled(self, mock_module, clock):
        """A safe operation that never finishes is still a failure"""
        mock_module.check_mode = True

        with pytest.raises(Exception, match="fail_json called"):
            wait_for(
                mock_module,
                probe=Mock(return_value=_transient()),
                is_done=lambda value: False,
                timeout=10,
                description="a calculation to finish",
                skip_in_check_mode=False,
            )

    def test_default_still_skips_under_check_mode(self, mock_module, clock):
        """The default is unchanged: no probe, no poll, no failure"""
        mock_module.check_mode = True
        probe = Mock()

        result = wait_for(
            mock_module,
            probe=probe,
            is_done=lambda value: False,
            timeout=300,
            description="workload foo to become ready",
        )

        assert result is None
        probe.assert_not_called()
        mock_module.fail_json.assert_not_called()

    def test_irrelevant_outside_check_mode(self, mock_module, clock):
        """The flag only governs check mode, not normal runs"""
        finished = _done()

        result = wait_for(
            mock_module,
            probe=Mock(return_value=finished),
            is_done=lambda value: value.status == "ready",
            timeout=300,
            description="a calculation to finish",
            skip_in_check_mode=False,
        )

        assert result is finished
