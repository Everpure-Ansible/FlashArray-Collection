# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Pure Storage Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Centralized API helper functions for FlashArray modules.

This module provides utilities to reduce code duplication across modules,
particularly for context-aware API calls and version checking.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import time

from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)


def get_cached_api_version(client):
    """Get API version with caching to avoid repeated calls.

    Args:
        client: FlashArray client instance

    Returns:
        str: API version string (e.g., "2.38")
    """
    if not hasattr(client, "_cached_api_version"):
        client._cached_api_version = client.get_rest_version()
    return client._cached_api_version


def check_api_version(client, min_version, module, feature_name=None):
    """Check if array API version meets minimum requirement.

    Args:
        client: FlashArray client instance
        min_version: Minimum required API version string
        module: AnsibleModule instance
        feature_name: Optional name of feature for error message

    Returns:
        bool: True if API version is sufficient, False otherwise

    Raises:
        Fails module if API version is insufficient and feature_name is provided
    """
    api_version = get_cached_api_version(client)
    version_ok = LooseVersion(min_version) <= LooseVersion(api_version)

    if not version_ok and feature_name:
        module.fail_json(
            msg=f"{feature_name} requires API version {min_version} or higher. "
            f"Current version: {api_version}. Please upgrade Purity."
        )

    return version_ok


def get_with_context(client, method_name, context_version, module, **kwargs):
    """Call array API method with context support if API version allows.

    This is the primary helper to eliminate duplicated context-aware API calls.
    Automatically adds context_names parameter if:
    1. API version supports it (>= context_version)
    2. Module has a 'context' parameter
    3. Context parameter is not None/empty

    Args:
        client: FlashArray client instance
        method_name: Name of method to call (e.g., 'get_protection_groups')
        context_version: Minimum API version for context support (e.g., "2.38")
        module: AnsibleModule instance
        **kwargs: Arguments to pass to the method (can include 'array' for SDK calls)

    Returns:
        API response object

    Example:
        # Instead of:
        api_version = array.get_rest_version()
        if LooseVersion("2.38") <= LooseVersion(api_version):
            res = array.get_protection_groups(
                names=[name],
                context_names=[module.params["context"]]
            )
        else:
            res = array.get_protection_groups(names=[name])

        # Use:
        res = get_with_context(
            array, 'get_protection_groups', "2.38", module,
            names=[name]
        )
    """
    api_version = get_cached_api_version(client)
    method = getattr(client, method_name)

    # Add context if API version supports it and context is provided
    if LooseVersion(context_version) <= LooseVersion(api_version) and module.params.get(
        "context"
    ):
        kwargs["context_names"] = [module.params["context"]]

    return method(**kwargs)


def post_with_context(client, method_name, context_version, module, **kwargs):
    """Alias for get_with_context for POST operations.

    Identical to get_with_context but named for clarity when doing POST operations.
    """
    return get_with_context(client, method_name, context_version, module, **kwargs)


def patch_with_context(client, method_name, context_version, module, **kwargs):
    """Alias for get_with_context for PATCH operations.

    Identical to get_with_context but named for clarity when doing PATCH operations.
    """
    return get_with_context(client, method_name, context_version, module, **kwargs)


def delete_with_context(client, method_name, context_version, module, **kwargs):
    """Alias for get_with_context for DELETE operations.

    Identical to get_with_context but named for clarity when doing DELETE operations.
    """
    return get_with_context(client, method_name, context_version, module, **kwargs)


def post_with_throttle_and_context(
    client, method_name, throttle_version, context_version, module, **kwargs
):
    """Call array API method with throttle and context support if API versions allow.

    This helper handles the pattern where both throttle and context are optional
    based on API version. Used primarily for pod creation operations.

    Behavior:
    - If API version < throttle_version: Call without allow_throttle or context_names
    - If API version >= throttle_version but < context_version: Add allow_throttle only
    - If API version >= context_version: Add both allow_throttle and context_names

    Args:
        client: FlashArray client instance
        method_name: Name of method to call (e.g., 'post_pods')
        throttle_version: Minimum API version for throttle support (e.g., "2.31")
        context_version: Minimum API version for context support (e.g., "2.38")
        module: AnsibleModule instance
        **kwargs: Arguments to pass to the method

    Returns:
        API response object
    """
    api_version = get_cached_api_version(client)
    method = getattr(client, method_name)

    # Check if throttle is supported
    if LooseVersion(throttle_version) <= LooseVersion(api_version):
        # Throttle is supported, add allow_throttle
        kwargs["allow_throttle"] = module.params.get("throttle", False)

        # Check if context is also supported
        if LooseVersion(context_version) <= LooseVersion(
            api_version
        ) and module.params.get("context"):
            kwargs["context_names"] = [module.params["context"]]

    return method(**kwargs)


def check_response(response, module, operation="Operation"):
    """Check API response and fail module if error occurred.

    Args:
        response: API response object
        module: AnsibleModule instance
        operation: Description of operation for error message

    Raises:
        Fails module with appropriate error message if response indicates error
    """
    if hasattr(response, "status_code") and response.status_code != 200:
        error_detail = (
            response.errors[0].message
            if hasattr(response, "errors") and response.errors
            else "Unknown error"
        )
        module.fail_json(
            msg=f"{operation} failed. Error: {error_detail}",
            status_code=response.status_code,
            changed=False,
        )


def get_local_array_name(client, module):
    """Get the name of the array the connection is addressed to.

    Args:
        client: FlashArray client instance
        module: AnsibleModule instance

    Returns:
        str: Name of the array being addressed

    Raises:
        Fails module if the array cannot be read or reports no name
    """
    res = client.get_arrays()
    check_response(res, module, "Reading the local array name")
    name = getattr(next(iter(list(res.items)), None), "name", None)
    if not name:
        module.fail_json(msg="The array did not report its own name.")
    return name


def wait_for(
    module,
    probe,
    is_done,
    timeout,
    description,
    is_failed=None,
    detail=None,
    interval=5,
    max_interval=30,
    skip_in_check_mode=True,
):
    """Poll an array operation until it completes, or fail the module.

    Args:
        module: AnsibleModule instance
        probe: Callable taking no arguments that reads the current state of the
            resource and returns it. Returning None means the resource is
            absent, which is how waiting for a deletion is expressed.
        is_done: Callable taking the probed value, returning True when the
            operation has finished
        timeout: Maximum number of seconds to wait
        description: What is being waited for, phrased to follow "waiting for",
            e.g. "workload foo to become ready". Used in the timeout message
        is_failed: Optional callable taking the probed value and returning an
            error message when the operation has terminally failed, or a falsy
            value otherwise
        detail: Optional callable taking the probed value and returning extra
            diagnostics to append to the timeout message
        interval: Seconds to wait before the second probe
        max_interval: Ceiling for the interval as it backs off
        skip_in_check_mode: By default polls are skipped in check mode, on the
            basis that nothing was asked of the array so there is nothing to wait
            for. Set this to False to poll in check mode anyway.

    Returns:
        The value from the final probe, or None when the poll was skipped in
        check mode.

    Raises:
        Fails the module on a terminal failure or on timeout. Never returns a
        value that does not satisfy is_done.
    """
    if module.check_mode and skip_in_check_mode:
        return None

    deadline = time.monotonic() + timeout
    current_interval = interval
    while True:
        value = probe()
        if is_failed is not None:
            failure = is_failed(value)
            if failure:
                module.fail_json(
                    msg=f"Failed while waiting for {description}. Error: {failure}"
                )
                return value
        if is_done(value):
            return value
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(current_interval, remaining))
        current_interval = min(current_interval * 1.5, max_interval)

    message = f"Timed out after {timeout} seconds waiting for {description}."
    if detail is not None:
        extra = detail(value)
        if extra:
            message = f"{message} Last reported: {extra}"
    module.fail_json(msg=message)
    return value
