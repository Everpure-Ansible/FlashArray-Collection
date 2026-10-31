#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2018, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_ra
version_added: '1.0.0'
short_description: Enable or Disable Everpure FlashArray Remote Assist
description:
- Enable or Disable Remote Assist for a Everpure FlashArray.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  state:
    description:
    - Define state of remote assist
    - When set to I(enable) the RA port can be exposed using the
      I(debug) module.
    type: str
    default: present
    choices: [ enable, disable, absent, present, test ]
  duration:
    description:
    - Number of hours Remote Assist port stays open for.
    - Must be an integer between 4 and 48
    type: int
    default: 24
    version_added: 1.33.0
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Enable Remote Assist port
  everpure.flasharray.purefa_ra:
    duration: 12
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
  register: result

  debug:
    msg: "Remote Assist: {{ result['ra_info'] }}"

- name: Disable Remote Assist port
  everpure.flasharray.purefa_ra:
    state: disable
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

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

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import SupportPatch
except ImportError:
    HAS_PURESTORAGE = False

DURATION_API = "2.35"


def test_ra(module, array):
    """Test support/remote assist configuration"""
    test_response = []
    res = array.get_support_test()
    check_response(res, module, "Remote Assist test")
    # The TestResult model only carries the fields the array chose to report,
    # so every field is read with a default. In particular ``resource`` is
    # absent on some Purity versions.
    for component in list(res.items):
        enabled = "true" if getattr(component, "enabled", False) else "false"
        success = "true" if getattr(component, "success", False) else "false"
        resource = getattr(component, "resource", None)
        test_response.append(
            {
                "component_address": getattr(component, "component_address", None),
                "component_name": getattr(component, "component_name", None),
                "description": getattr(component, "description", None),
                "destination": getattr(component, "destination", None),
                "enabled": enabled,
                "result_details": getattr(component, "result_details", ""),
                "success": success,
                "test_type": getattr(component, "test_type", None),
                "resource_name": getattr(resource, "name", None),
            }
        )
    # Running a test does not modify the array
    module.exit_json(changed=False, test_response=test_response)


def enable_ra(module, array):
    """Enable Remote Assist"""
    changed = False
    ra_facts = {}
    if not list(array.get_support().items)[0].remote_assist_status in [
        "connected",
        "connecting",
        "enabled",
    ]:
        changed = True
        res = {}
        api_version = array.get_rest_version()
        if not module.check_mode:
            if LooseVersion(DURATION_API) <= LooseVersion(api_version):
                if not 4 <= module.params["duration"] <= 48:
                    module.fail_json(msg="The duration must be between 4-48 hours.")
                else:
                    duration = module.params["duration"] * 3600000
                    res = array.patch_support(
                        support=SupportPatch(
                            remote_assist_duration=duration, remote_assist_active=True
                        )
                    )
            else:
                res = array.patch_support(
                    support=SupportPatch(remote_assist_active=True)
                )
            if res.status_code == 200:
                ra_data = list(res.items)[0]
                ra_facts["fa_ra"] = {
                    "name": ra_data.remote_assist_paths[0].component_name,
                    "port": None,
                }
            else:
                module.fail_json(
                    msg="Enabling Remote Assist failed. Error: {0}".format(
                        res.errors[0].message
                    )
                )
    else:
        res = array.get_support()
        if res.status_code == 200:
            ra_data = list(res.items)[0]
            ra_facts["fa_ra"] = {
                "name": ra_data.remote_assist_paths[0].component_name,
                "port": None,
            }
        else:
            module.fail_json(
                msg="Getting Remote Assist failed. Error: {0}".format(
                    res.errors[0].message
                )
            )
    module.exit_json(changed=changed, ra_info=ra_facts)


def disable_ra(module, array):
    """Disable Remote Assist"""
    changed = False
    if list(array.get_support().items)[0].remote_assist_status in [
        "connected",
        "connecting",
        "enabled",
    ]:
        changed = True
        if not module.check_mode:
            res = array.patch_support(support=SupportPatch(remote_assist_active=False))
            check_response(res, module, "Disabling Remote Assist")
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(
                type="str",
                default="present",
                choices=["enable", "disable", "absent", "present", "test"],
            ),
            duration=dict(type="int", default=24),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)
    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)

    if module.params["state"] in ["enable", "present"]:
        enable_ra(module, array)
    elif module.params["state"] == "test":
        test_ra(module, array)
    else:
        disable_ra(module, array)
    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
