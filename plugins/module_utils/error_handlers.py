# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Everpure Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Standardized error handling for FlashArray modules.

This module provides consistent error handling patterns across all modules,
improving debugging and user experience.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class FlashArrayError(Exception):
    """Base exception for FlashArray operations."""

    pass


class FlashArrayAPIError(FlashArrayError):
    """API call returned non-200 status."""

    def __init__(self, operation, response):
        self.operation = operation
        self.status_code = (
            response.status_code if hasattr(response, "status_code") else None
        )
        self.errors = response.errors if hasattr(response, "errors") else []

        error_msg = self.errors[0].message if self.errors else "Unknown error"
        super().__init__(f"{operation} failed: {error_msg}")


class FlashArrayAuthError(FlashArrayError):
    """Authentication to FlashArray failed."""

    pass


class FlashArrayVersionError(FlashArrayError):
    """API version not supported for requested operation."""

    pass


class FlashArrayConnectionError(FlashArrayError):
    """Connection to FlashArray failed."""

    pass


def check_response(response, module, operation="Operation"):
    """Check API response and fail module if error occurred.

    Args:
        response: API response object
        module: AnsibleModule instance
        operation: Description of operation for error message

    Raises:
        Fails module with appropriate error message if response indicates error

    Example:
        res = array.post_volumes(names=["vol1"])
        check_response(res, module, "Creating volume vol1")
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


def safe_api_call(func, module, operation="API call", *args, **kwargs):
    """Execute API call with comprehensive error handling.

    Args:
        func: Function to call
        module: AnsibleModule instance
        operation: Description for error messages
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result of func() if successful

    Raises:
        Fails module on any error

    Example:
        result = safe_api_call(
            array.post_volumes,
            module,
            "Creating volume vol1",
            names=["vol1"],
            volume=Volume(provisioned=1024**3)
        )
    """
    try:
        result = func(*args, **kwargs)
        check_response(result, module, operation)
        return result
    except AttributeError as e:
        module.fail_json(
            msg=f"{operation} failed: Invalid API call - {str(e)}", changed=False
        )
    except ConnectionError as e:
        module.fail_json(
            msg=f"{operation} failed: Connection error - {str(e)}", changed=False
        )
    except Exception as e:
        # Catch-all for unexpected errors
        module.fail_json(msg=f"{operation} failed: {str(e)}", changed=False)


def handle_auth_error(module, array_name, error):
    """Handle authentication errors with helpful messages.

    Args:
        module: AnsibleModule instance
        array_name: Name/URL of the array
        error: Exception that occurred

    Raises:
        Fails module with appropriate error message
    """
    if isinstance(error, ConnectionError):
        module.fail_json(
            msg=f"Cannot connect to FlashArray at {array_name}. "
            f"Check network connectivity and fa_url parameter. Error: {str(error)}"
        )
    elif isinstance(error, AttributeError):
        module.fail_json(msg=f"Invalid FlashArray client configuration: {str(error)}")
    else:
        module.fail_json(
            msg=f"FlashArray authentication failed. "
            f"Check your api_token and credentials. Error: {str(error)}"
        )


def format_error_message(operation, error_obj):
    """Format a consistent error message from various error types.

    Args:
        operation: Description of what was being attempted
        error_obj: Error object (could be response, exception, etc.)

    Returns:
        str: Formatted error message
    """
    if hasattr(error_obj, "errors") and error_obj.errors:
        error_detail = error_obj.errors[0].message
    elif hasattr(error_obj, "message"):
        error_detail = error_obj.message
    elif isinstance(error_obj, Exception):
        error_detail = str(error_obj)
    else:
        error_detail = "Unknown error"

    return f"{operation} failed. Error: {error_detail}"
