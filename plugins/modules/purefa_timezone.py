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
module: purefa_timezone
version_added: '1.45.0'
short_description: Configure Everpure FlashArray system time zone
description:
- Configure the system time zone for Everpure FlashArrays.
- Ideal for Day 0 initial configuration.
- The current time zone of an array is reported by the C(config) subset
  of M(everpure.flasharray.purefa_info).
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  state:
    description:
    - Set the array time zone
    type: str
    default: present
    choices: [ present ]
  timezone:
    description:
    - Name of the time zone to set, as used by the IANA time zone database,
      eg. C(America/New_York) or C(Europe/London).
    - Validated against the time zone database of the C(pytz) module
      installed on the Ansible control node.
    type: str
    required: true
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
notes:
- This module requires the C(pytz) Python library.
- Requires Purity//FA REST API 2.26 or higher.
"""

EXAMPLES = r"""
- name: Set array time zone
  everpure.flasharray.purefa_timezone:
    timezone: America/New_York
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Set the time zone of a fleet member
  everpure.flasharray.purefa_timezone:
    timezone: Europe/London
    context: remote-array
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PYTZ = True
try:
    import pytz
except ImportError:
    HAS_PYTZ = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_api_version,
    check_response,
    get_with_context,
)

CONTEXT_VERSION = "2.38"
TIMEZONE_VERSION = "2.26"


def update_timezone(module, array):
    """Change the array time zone"""
    changed = True
    if not module.check_mode:
        # The SDK marks time_zone as a read-only field of the Arrays model, so
        # it is dropped when a request body is built from Arrays(time_zone=...).
        # Pass the body as a dict so that the field reaches the array.
        res = get_with_context(
            array,
            "patch_arrays",
            CONTEXT_VERSION,
            module,
            array={"time_zone": module.params["timezone"]},
        )
        check_response(
            res,
            module,
            "Failed to set array time zone to {0}".format(module.params["timezone"]),
        )
        # The array echoes back the object it has just modified. As time_zone
        # is flagged read-only by the API spec, confirm the array really did
        # take the new value instead of quietly ignoring the field.
        applied = getattr(next(iter(list(res.items)), None), "time_zone", None)
        if applied is not None and applied != module.params["timezone"]:
            module.fail_json(
                msg="Array did not apply the requested time zone {0}. "
                "Time zone is {1}".format(module.params["timezone"], applied)
            )

    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            timezone=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["present"]),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PYTZ:
        module.fail_json(msg="pytz is required for this module")

    if module.params["timezone"] not in pytz.all_timezones_set:
        module.fail_json(
            msg="Timezone {0} is not valid".format(module.params["timezone"])
        )

    array = get_array(module)
    check_api_version(array, TIMEZONE_VERSION, module, "Array time zone management")

    res = get_with_context(array, "get_arrays", CONTEXT_VERSION, module)
    check_response(res, module, "Failed to get current array time zone")
    current_timezone = getattr(list(res.items)[0], "time_zone", None)
    if current_timezone != module.params["timezone"]:
        update_timezone(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
