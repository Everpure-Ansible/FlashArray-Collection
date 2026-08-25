#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2026, Simon Dodsley (simon@everpuredata.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: purefa_zte
version_added: '1.44.0'
short_description: Perform Zero Touch Erasure (ZTE) on a FlashArray
description:
- Securely reset a FlashArray to a factory-fresh state using Zero Touch
  Erasure (ZTE).
- ZTE wipes all drives, generates a NIST SP800-88R1 sanitization certificate
  and optionally reinstalls the array image.
- B(This is an extremely destructive and irreversible operation.) All data on
  the array is permanently and unrecoverably erased.
- Requires Purity//FA 6.6.8, or higher.
- All customer data (pods, protection groups, volumes/snapshots, array
  connections, file systems, directory service, file local users and groups,
  and Active Directory service) must be deleted and eradicated before starting
  ZTE, otherwise the operation will fail immediately.
- ZTE is a multi-phase process. Use I(state=start) to begin the drive wipe,
  I(state=status) to monitor progress and retrieve the sanitization
  certificate, and I(state=finalize) to complete the reset. Use
  I(state=cancel) to cancel a failed reset.
- During the drive wipe the array REST API service is unavailable for a period
  of time (typically around 30 minutes). This is expected behaviour.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  state:
    description:
    - The ZTE phase to perform.
    - I(start) begins Phase 1, securely wiping the drives and generating the
      sanitization certificate. If a reset is already running this is a no-op.
    - I(status) returns the current ZTE process status and, when available,
      the sanitization certificate. This is non-destructive.
    - I(finalize) performs Phase 3, finalizing the reset. This permanently
      deletes the sanitization certificate, so ensure it has been saved first.
      A finalized array no longer reports a reset process, so re-running
      I(finalize) reports no change rather than failing.
    - I(cancel) cancels a ZTE process that is in a failed state. If no reset
      is present, or the reset has not failed, this is a no-op.
    type: str
    choices: [ start, status, finalize, cancel ]
    default: status
  eradicate:
    description:
    - A safety acknowledgement that must be set to C(true) to perform any
      destructive ZTE phase (I(start) or I(finalize)).
    - Setting this to C(true) confirms that you understand all data on the
      array will be permanently and unrecoverably erased.
    type: bool
    default: false
  preserve_config:
    description:
    - Whether to preserve array configuration data during the drive wipe.
    - Note that the default preserves all configuration data. Set this to
      C(false) to wipe configuration data as well, for a completely
      factory-fresh array.
    - Only used when I(state=start).
    type: bool
    default: true
  skip_phonehome_check:
    description:
    - Skip the phonehome connectivity check when starting ZTE.
    - Must be set to C(true) for darksite arrays that do not have connectivity
      to Pure Storage cloud servers, otherwise the reset will fail the
      phonehome connectivity check.
    - Only used when I(state=start).
    type: bool
    default: false
  reinstall_image:
    description:
    - Whether to reinstall the array image when finalizing ZTE.
    - When C(false) (Option 1), existing system-generated data, management
      interface configuration and configuration data are retained.
    - When C(true) (Option 2), the array image is reinstalled and existing
      system-generated data, management interface configuration and
      configuration data are removed.
    - Only used when I(state=finalize).
    type: bool
    default: false
  image_source:
    description:
    - The source of the image used when I(reinstall_image=true).
    - For phoning-home arrays set this to C(auto).
    - For darksite arrays set this to the URL, or file path, of an image
      bundle that the array can access. The image bundle must be the same
      version as the Purity//FA version running on the array.
    - Only used when I(state=finalize) and I(reinstall_image=true).
    type: str
    default: auto
  image_version:
    description:
    - The Purity//FA version of the darksite image bundle referenced by
      I(image_source).
    - Only used when I(state=finalize) and I(reinstall_image=true) for a
      darksite array.
    type: str
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Check current ZTE status and retrieve sanitization certificate
  everpure.flasharray.purefa_zte:
    state: status
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: zte

- name: Save the sanitization certificate before finalizing
  ansible.builtin.copy:
    content: "{{ zte.zte.sanitization_certificate }}"
    dest: ./sanitization_certificate.txt
  when: zte.zte.sanitization_certificate | length > 0

- name: Start ZTE (Phase 1 - wipe drives)
  everpure.flasharray.purefa_zte:
    state: start
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Start ZTE on a darksite array
  everpure.flasharray.purefa_zte:
    state: start
    eradicate: true
    skip_phonehome_check: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Finalize ZTE without reinstalling the image (Option 1)
  everpure.flasharray.purefa_zte:
    state: finalize
    eradicate: true
    reinstall_image: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Finalize ZTE and reinstall image on a phoning-home array (Option 2)
  everpure.flasharray.purefa_zte:
    state: finalize
    eradicate: true
    reinstall_image: true
    image_source: auto
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Finalize ZTE and reinstall image on a darksite array (Option 2)
  everpure.flasharray.purefa_zte:
    state: finalize
    eradicate: true
    reinstall_image: true
    image_source: "https://server.example.com/purity_iso.sh"
    image_version: "6.6.8"
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Cancel a failed ZTE process
  everpure.flasharray.purefa_zte:
    state: cancel
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
zte:
  description: The current state of the ZTE process.
  returned: always
  type: dict
  contains:
    status:
      description:
      - The status of the ZTE process. One of C(resetting),
        C(waiting_for_finalize), C(downloading), C(downloaded),
        C(reset_failed), C(download_failed) or C(reimage_failed).
      - An empty string indicates that no ZTE process is in progress. This is
        both the pre-start and the post-finalize state.
      type: str
      returned: always
    details:
      description: Failure information when the ZTE process has failed.
      type: str
      returned: always
    image_download_progress:
      description:
      - The image download progress, in decimal format, when reinstalling the
        image.
      - Null when no image download is in progress.
      type: float
      returned: always
    sanitization_certificate:
      description:
      - The NIST SP800-88R1 sanitization certificate generated during the
        drive wipe.
      - This is only available between Phase 1 completing and ZTE being
        finalized. It cannot be retrieved once ZTE is finalized.
      type: str
      returned: always
"""

HAS_PURESTORAGE = True
try:
    from pypureclient import flasharray
except ImportError:
    HAS_PURESTORAGE = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_response,
)

MIN_REQUIRED_API_VERSION = "2.34"

# Statuses that indicate a ZTE process is actively running or awaiting action
ACTIVE_STATES = frozenset(
    [
        "resetting",
        "waiting_for_finalize",
        "downloading",
        "downloaded",
    ]
)

# Statuses that indicate the ZTE process has failed. These are the only
# statuses from which the array will accept a cancellation.
FAILED_STATES = frozenset(
    [
        "reset_failed",
        "download_failed",
        "reimage_failed",
    ]
)

# Statuses from which the array will accept a finalize request
FINALIZABLE_STATES = frozenset(
    [
        "waiting_for_finalize",
        "downloaded",
    ]
)


def response_erasure(res):
    """Return the erasure object carried by an API response, or None."""
    items = list(getattr(res, "items", None) or [])
    return items[0] if items else None


def get_erasure(module, array):
    """Return the current erasure (factory reset) object, or None.

    A successful Option 1 finalize leaves no erasure in progress, in which case
    ``get_arrays_erasures`` returns a 200 with an empty item list. Any non-200
    is a genuine API failure and must not be confused with "no reset running".
    """
    res = array.get_arrays_erasures()
    check_response(res, module, "Failed to get ZTE status")
    return response_erasure(res)


def erasure_status(current):
    """Return the status string of an erasure object, or an empty string."""
    if current is None:
        return ""
    return getattr(current, "status", "") or ""


def erasure_facts(current):
    """Build the return dict from an erasure object."""
    if current is None:
        return {
            "status": "",
            "details": "",
            "image_download_progress": None,
            "sanitization_certificate": "",
        }
    return {
        "status": erasure_status(current),
        "details": getattr(current, "details", "") or "",
        # A numeric field - 0 is a valid progress value, so it must not be
        # collapsed to an empty string.
        "image_download_progress": getattr(current, "image_download_progress", None),
        "sanitization_certificate": getattr(current, "sanitization_certificate", "")
        or "",
    }


def zte_status(module, current):
    """Report the current ZTE status. Non-destructive."""
    module.exit_json(changed=False, zte=erasure_facts(current))


def start_zte(module, array, current):
    """Phase 1 - securely wipe the drives and generate the sanitization cert."""
    if not module.params["eradicate"]:
        module.fail_json(
            msg="To start ZTE the `eradicate` parameter must be set to true. "
            "This permanently and unrecoverably erases all data on the array."
        )
        return
    if current is not None:
        status = erasure_status(current)
        if status in ACTIVE_STATES:
            # A reset is already in progress - nothing to do
            module.exit_json(changed=False, zte=erasure_facts(current))
            return
        module.fail_json(
            msg="Cannot start ZTE. A factory reset already exists with status "
            "'{0}'. Cancel it using `state: cancel` before starting a new "
            "reset. Details: {1}".format(
                status, getattr(current, "details", "") or "none"
            )
        )
        return
    if not module.check_mode:
        preserve = ["all"] if module.params["preserve_config"] else []
        res = array.post_arrays_erasures(
            eradicate_all_data=True,
            preserve_configuration_data=preserve,
            skip_phonehome_check=module.params["skip_phonehome_check"],
        )
        check_response(res, module, "Failed to start ZTE")
        # Take the new state from the POST response. The REST service becomes
        # unavailable shortly after the wipe starts, so a follow-up GET here
        # could fail an operation that actually succeeded.
        current = response_erasure(res)
    module.exit_json(changed=True, zte=erasure_facts(current))


def finalize_zte(module, array, current):
    """Phase 3 - finalize the reset."""
    if not module.params["eradicate"]:
        module.fail_json(
            msg="To finalize ZTE the `eradicate` parameter must be set to true. "
            "This permanently deletes the sanitization certificate."
        )
        return
    if current is None:
        # A successful finalize removes the erasure object, so "no reset
        # present" is the post-finalize steady state. Report no change rather
        # than failing, so the task stays idempotent across re-runs.
        module.exit_json(changed=False, zte=erasure_facts(None))
        return
    status = erasure_status(current)
    if status in FAILED_STATES:
        module.fail_json(
            msg="Cannot finalize ZTE. The factory reset is in a failed state "
            "('{0}') and must be cancelled using `state: cancel`. "
            "Details: {1}".format(status, getattr(current, "details", "") or "none")
        )
        return
    if status not in FINALIZABLE_STATES:
        module.fail_json(
            msg="Cannot finalize ZTE. The factory reset is not ready to be "
            "finalized (status '{0}'). Wait until the status is "
            "`waiting_for_finalize`.".format(status)
        )
        return
    if not module.check_mode:
        kwargs = dict(
            finalize=True,
            eradicate_all_data=True,
            delete_sanitization_certificate=True,
            reinstall_image=module.params["reinstall_image"],
        )
        if module.params["reinstall_image"]:
            kwargs["erasure_patch"] = flasharray.ArrayErasurePatch(
                image_source=module.params["image_source"],
                image_version=module.params["image_version"],
            )
        res = array.patch_arrays_erasures(**kwargs)
        check_response(res, module, "Failed to finalize ZTE")
        current = response_erasure(res)
    module.exit_json(changed=True, zte=erasure_facts(current))


def cancel_zte(module, array, current):
    """Cancel a ZTE process that is in a failed state."""
    if current is None:
        module.exit_json(changed=False, zte=erasure_facts(current))
        return
    if erasure_status(current) not in FAILED_STATES:
        # The array only accepts a cancellation for a failed reset, so there
        # is nothing to cancel here.
        module.exit_json(changed=False, zte=erasure_facts(current))
        return
    if not module.check_mode:
        res = array.delete_arrays_erasures()
        check_response(res, module, "Failed to cancel ZTE")
        current = None
    module.exit_json(changed=True, zte=erasure_facts(current))


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(
                type="str",
                default="status",
                choices=["start", "status", "finalize", "cancel"],
            ),
            eradicate=dict(type="bool", default=False),
            preserve_config=dict(type="bool", default=True),
            skip_phonehome_check=dict(type="bool", default=False),
            reinstall_image=dict(type="bool", default=False),
            image_source=dict(type="str", default="auto"),
            image_version=dict(type="str"),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)
    api_version = array.get_rest_version()

    if LooseVersion(MIN_REQUIRED_API_VERSION) > LooseVersion(api_version):
        module.fail_json(
            msg="FlashArray REST version not supported. "
            "Minimum version required: {0}".format(MIN_REQUIRED_API_VERSION)
        )

    current = get_erasure(module, array)

    state = module.params["state"]
    if state == "start":
        start_zte(module, array, current)
    elif state == "finalize":
        finalize_zte(module, array, current)
    elif state == "cancel":
        cancel_zte(module, array, current)
    else:
        zte_status(module, current)


if __name__ == "__main__":
    main()
