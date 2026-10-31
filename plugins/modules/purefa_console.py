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
module: purefa_console
version_added: '1.0.0'
short_description: Enable or Disable Everpure FlashArray Console Lock
description:
- Enablke or Disable root lockout from the array at the physical console for a Everpure FlashArray.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  state:
    description:
    - Define state of console lockout
    - When set to I(enable) the console port is locked from root login.
    type: str
    default: disable
    choices: [ enable, disable ]
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
    version_added: '1.39.0'
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Enable Console Lockout
  everpure.flasharray.purefa_console:
    state: enable
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Disable Console Lockout
  everpure.flasharray.purefa_console:
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PYPURECLIENT = True
try:
    from pypureclient.flasharray import Arrays
except ImportError:
    HAS_PYPURECLIENT = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    get_with_context,
    check_response,
)

CONTEXT_VERSION = "2.38"


def update_console(module, array):
    """Update Console Lockout setting"""
    changed = False
    res = get_with_context(array, "get_arrays", CONTEXT_VERSION, module)
    current_state = list(res.items)[0].console_lock_enabled
    new_state = bool(module.params["state"] == "enable")
    if current_state != new_state:
        changed = True
        if not module.check_mode:
            res = get_with_context(
                array,
                "patch_arrays",
                CONTEXT_VERSION,
                module,
                array=Arrays(console_lock_enabled=new_state),
            )
            check_response(res, module, "Enabling Console Lock")
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", default="disable", choices=["enable", "disable"]),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PYPURECLIENT:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    array = get_array(module)

    update_console(module, array)


if __name__ == "__main__":
    main()
