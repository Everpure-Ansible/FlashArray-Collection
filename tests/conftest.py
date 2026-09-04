# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared pytest fixtures for FlashArray Collection tests."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_module():
    """Create a mock Ansible module with common parameters.

    Returns:
        Mock: Mock AnsibleModule instance with default parameters
    """
    module = Mock()
    module.params = {
        "fa_url": "flasharray.example.com",
        "api_token": "T-test-token-12345",
        "disable_warnings": True,
        "state": "present",
        "context": None,
    }
    module.check_mode = False
    module.fail_json = Mock(side_effect=Exception("fail_json called"))
    module.exit_json = Mock(side_effect=Exception("exit_json called"))
    return module


@pytest.fixture
def mock_array():
    """Create a mock FlashArray client.

    Returns:
        Mock: Mock FlashArray client with common API methods
    """
    array = MagicMock()

    # Mock API version
    array.get_rest_version.return_value = "2.38"

    # Mock successful responses by default
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.errors = []

    # Set default return values for common API calls
    array.get_volumes.return_value = mock_response
    array.post_volumes.return_value = mock_response
    array.patch_volumes.return_value = mock_response
    array.delete_volumes.return_value = mock_response

    array.get_hosts.return_value = mock_response
    array.post_hosts.return_value = mock_response
    array.patch_hosts.return_value = mock_response
    array.delete_hosts.return_value = mock_response

    array.get_protection_groups.return_value = mock_response
    array.post_protection_groups.return_value = mock_response
    array.patch_protection_groups.return_value = mock_response
    array.delete_protection_groups.return_value = mock_response

    array.get_hardware.return_value = mock_response

    return array


@pytest.fixture
def mock_error_response():
    """Create a mock error response from FlashArray API.

    Returns:
        Mock: Mock response with error
    """
    response = Mock()
    response.status_code = 400
    error = Mock()
    error.message = "Test error message"
    response.errors = [error]
    return response


@pytest.fixture
def mock_empty_error_response():
    """Create a mock error response with empty errors list.

    Returns:
        Mock: Mock response with empty errors
    """
    response = Mock()
    response.status_code = 400
    response.errors = []
    return response


@pytest.fixture
def mock_success_response():
    """Create a mock successful response from FlashArray API.

    Returns:
        Mock: Mock response with success status
    """
    response = Mock()
    response.status_code = 200
    response.errors = []
    return response


@pytest.fixture
def mock_volume():
    """Create a mock volume object.

    Returns:
        Mock: Mock volume with common attributes
    """
    volume = Mock()
    volume.name = "test-volume"
    volume.provisioned = 107374182400  # 100GB in bytes
    volume.destroyed = False
    volume.serial = "ABCD1234567890EF"
    return volume


@pytest.fixture
def mock_host():
    """Create a mock host object.

    Returns:
        Mock: Mock host with common attributes
    """
    host = Mock()
    host.name = "test-host"
    host.iqns = []
    host.wwns = []
    host.nqns = []
    host.personality = None
    return host


@pytest.fixture
def mock_protection_group():
    """Create a mock protection group object.

    Returns:
        Mock: Mock protection group with common attributes
    """
    pgroup = Mock()
    pgroup.name = "test-pgroup"
    pgroup.destroyed = False
    pgroup.host_count = 0
    pgroup.volume_count = 0
    return pgroup


@pytest.fixture
def mock_api_exception():
    """Create a mock API exception.

    Returns:
        Exception: Mock exception for API errors
    """
    exception = Exception("API call failed")
    exception.status = 400
    exception.reason = "Bad Request"
    return exception
