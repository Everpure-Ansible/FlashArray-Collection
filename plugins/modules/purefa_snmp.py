#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2019, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_snmp
version_added: '1.0.0'
short_description: Configure FlashArray SNMP Managers
description:
- Manage SNMP managers on a Everpure FlashArray.
- Changing of a named SNMP managers version is not supported.
- For an existing SNMP v2c manager only I(host) and I(notification) are
  compared. The array returns the community string masked, so a change to
  only I(community) cannot be detected and is not applied; delete and
  recreate the manager to change its community string.
- For an existing SNMP v3 manager I(host), I(notification), I(user),
  I(auth_protocol) and I(privacy_protocol) are compared. The array returns
  the passphrases masked, so a change to only I(auth_passphrase) or
  I(privacy_passphrase) cannot be detected and is not applied; delete and
  recreate the manager to change a passphrase.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of SNMP Manager
    required: true
    type: str
  state:
    description:
    - Create, delete or testSNMP manager
    type: str
    default: present
    choices: [ absent, present, test ]
  auth_passphrase:
    type: str
    description:
    - SNMPv3 only. Passphrase of 8 - 32 characters.
  auth_protocol:
    type: str
    description:
    - SNMP v3 only. Hash algorithm to use
    choices: [ MD5, SHA ]
  community:
    type: str
    description:
    - SNMP v2c only. Manager community ID. Between 1 and 32 characters long.
  host:
    type: str
    description:
    - IPv4 or IPv6 address or FQDN to send trap messages to.
  user:
    type: str
    description:
    - SNMP v3 only. User ID recognized by the specified SNMP manager.
      Must be between 1 and 32 characters.
  version:
    type: str
    description:
    - Version of SNMP protocol to use for the manager.
    choices: [ v2c, v3 ]
    default: v2c
  notification:
    type: str
    description:
    - Action to perform on event.
    default: trap
    choices: [ inform, trap ]
  privacy_passphrase:
    type: str
    description:
    - SNMPv3 only. Passphrase to encrypt SNMP messages.
      Must be between 8 and 63 non-space ASCII characters.
  privacy_protocol:
    type: str
    description:
    - SNMP v3 only. Encryption protocol to use
    choices: [ AES, DES ]
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Delete existing SNMP manager
  everpure.flasharray.purefa_snmp:
    name: manager1
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
- name: Create v2c SNMP manager
  puretorage.flasharray.purefa_snmp:
    name: manager1
    community: public
    host: 10.21.22.23
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
- name: Create v3 SNMP manager
  puretorage.flasharray.purefa_snmp:
    name: manager2
    version: v3
    user: manager
    auth_protocol: MD5
    auth_passphrase: password
    host: 10.21.22.23
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
- name: Update existing SNMP manager
  everpure.flasharray.purefa_snmp:
    name: manager1
    community: private
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
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_response,
)

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        SnmpManagerPost,
        SnmpManagerPatch,
        SnmpV2c,
        SnmpV3Patch,
        SnmpV3Post,
    )
except ImportError:
    HAS_PURESTORAGE = False


def test_manager(module, array):
    """Test SNMP manager configuration"""
    test_response = []
    res = array.get_snmp_managers_test(names=[module.params["name"]])
    # An unreachable manager makes the array return an error response,
    # which has no items to iterate over.
    check_response(res, module, f"Test of SNMP manager {module.params['name']}")
    # The TestResult model only carries the fields the array chose to report,
    # so every field is read with a default (resource in particular may be
    # absent).
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


def update_manager(module, array):
    """Update SNMP Manager"""
    changed = False
    res = array.get_snmp_managers(names=module.params["name"])
    check_response(
        res,
        module,
        f"Failed to get configuration for SNMP manager {module.params['name']}",
    )
    mgr = list(res.items)[0]
    if mgr.version != module.params["version"]:
        module.fail_json(msg="Changing an SNMP managers version is not supported.")
    elif module.params["version"] == "v2c":
        # The community string is returned masked, so only the readable
        # fields can be compared.
        if (
            getattr(mgr, "host", None) != module.params["host"]
            or getattr(mgr, "notification", None) != module.params["notification"]
        ):
            changed = True
        if changed and not module.check_mode:
            res = array.patch_snmp_managers(
                names=module.params["name"],
                snmp_manager=SnmpManagerPatch(
                    version=module.params["version"],
                    v2c=SnmpV2c(community=module.params["community"]),
                    notification=module.params["notification"],
                    host=module.params["host"],
                ),
            )
            check_response(
                res,
                module,
                f"Failed to update SNMP manager {module.params['name']}",
            )
    else:
        # The passphrases are returned masked, so only the readable fields
        # can be compared. A passphrase-only change cannot be detected and
        # needs the manager deleted and recreated. The SDK model raises
        # AttributeError for a field the array returned as null, so every
        # read has a default of None, which is also what an unset parameter is.
        current_v3 = getattr(mgr, "v3", None)
        current = {
            "host": getattr(mgr, "host", None),
            "notification": getattr(mgr, "notification", None),
            "user": getattr(current_v3, "user", None),
            "auth_protocol": getattr(current_v3, "auth_protocol", None),
            "privacy_protocol": getattr(current_v3, "privacy_protocol", None),
        }
        desired = {
            "host": module.params["host"],
            "notification": module.params["notification"],
            "user": module.params["user"],
            "auth_protocol": module.params["auth_protocol"],
            "privacy_protocol": module.params["privacy_protocol"],
        }
        if current != desired:
            changed = True
            if not module.check_mode:
                # A protocol is only accepted together with its passphrase
                v3_settings = {"user": module.params["user"]}
                if module.params["auth_protocol"]:
                    v3_settings["auth_protocol"] = module.params["auth_protocol"]
                    v3_settings["auth_passphrase"] = module.params["auth_passphrase"]
                if module.params["privacy_protocol"]:
                    v3_settings["privacy_protocol"] = module.params["privacy_protocol"]
                    v3_settings["privacy_passphrase"] = module.params[
                        "privacy_passphrase"
                    ]
                res = array.patch_snmp_managers(
                    names=module.params["name"],
                    snmp_manager=SnmpManagerPatch(
                        version=module.params["version"],
                        notification=module.params["notification"],
                        host=module.params["host"],
                        v3=SnmpV3Patch(**v3_settings),
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to update SNMP manager {module.params['name']}",
                )

    module.exit_json(changed=changed)


def delete_manager(module, array):
    """Delete SNMP Manager"""
    changed = True
    if not module.check_mode:
        res = array.delete_snmp_managers(names=[module.params["name"]])
        check_response(res, module, f"Delete SNMP manager {module.params['name']}")
    module.exit_json(changed=changed)


def create_manager(module, array):
    """Create SNMP Manager"""
    changed = True
    if not module.check_mode:
        if module.params["version"] == "v2c":
            res = array.post_snmp_managers(
                names=module.params["name"],
                snmp_manager=SnmpManagerPost(
                    version=module.params["version"],
                    notification=module.params["notification"],
                    host=module.params["host"],
                    v2c=SnmpV2c(
                        community=module.params["community"],
                    ),
                ),
            )
            check_response(
                res, module, f"Failed to create SNMP manager {module.params['name']}"
            )
        else:
            if module.params["auth_protocol"] and module.params["privacy_protocol"]:
                res = array.post_snmp_managers(
                    names=module.params["name"],
                    snmp_manager=SnmpManagerPost(
                        host=module.params["host"],
                        notification=module.params["notification"],
                        version=module.params["version"],
                        v3=SnmpV3Post(
                            auth_passphrase=module.params["auth_passphrase"],
                            auth_protocol=module.params["auth_protocol"],
                            privacy_passphrase=module.params["privacy_passphrase"],
                            privacy_protocol=module.params["privacy_protocol"],
                            user=module.params["user"],
                        ),
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to create SNMP manager {module.params['name']}",
                )
            elif (
                module.params["auth_protocol"] and not module.params["privacy_protocol"]
            ):
                res = array.post_snmp_managers(
                    names=module.params["name"],
                    snmp_manager=SnmpManagerPost(
                        version=module.params["version"],
                        notification=module.params["notification"],
                        host=module.params["host"],
                        v3=SnmpV3Post(
                            auth_passphrase=module.params["auth_passphrase"],
                            auth_protocol=module.params["auth_protocol"],
                            user=module.params["user"],
                        ),
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to create SNMP manager {module.params['name']}",
                )
            elif (
                not module.params["auth_protocol"] and module.params["privacy_protocol"]
            ):
                res = array.post_snmp_managers(
                    names=module.params["name"],
                    snmp_manager=SnmpManagerPost(
                        host=module.params["host"],
                        notification=module.params["notification"],
                        version=module.params["version"],
                        v3=SnmpV3Post(
                            privacy_passphrase=module.params["privacy_passphrase"],
                            privacy_protocol=module.params["privacy_protocol"],
                            user=module.params["user"],
                        ),
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to create SNMP manager {module.params['name']}",
                )
            elif (
                not module.params["auth_protocol"]
                and not module.params["privacy_protocol"]
            ):
                res = array.post_snmp_managers(
                    names=module.params["name"],
                    snmp_manager=SnmpManagerPost(
                        host=module.params["host"],
                        notification=module.params["notification"],
                        version=module.params["version"],
                        v3=SnmpV3Post(
                            user=module.params["user"],
                        ),
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to create SNMP manager {module.params['name']}",
                )
            else:
                module.fail_json(
                    msg="Invalid parameters selected in create. Please raise issue in Ansible GitHub"
                )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            host=dict(type="str"),
            state=dict(
                type="str", default="present", choices=["absent", "present", "test"]
            ),
            user=dict(type="str"),
            notification=dict(type="str", choices=["inform", "trap"], default="trap"),
            auth_passphrase=dict(type="str", no_log=True),
            auth_protocol=dict(type="str", choices=["MD5", "SHA"]),
            privacy_passphrase=dict(type="str", no_log=True),
            privacy_protocol=dict(type="str", choices=["AES", "DES"]),
            version=dict(type="str", default="v2c", choices=["v2c", "v3"]),
            community=dict(type="str"),
        )
    )

    required_together = [
        ["auth_passphrase", "auth_protocol"],
        ["privacy_passphrase", "privacy_protocol"],
    ]

    module = AnsibleModule(
        argument_spec,
        required_together=required_together,
        supports_check_mode=True,
    )

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    state = module.params["state"]
    array = get_array(module)
    mgr_configured = False
    mgrs = list(array.get_snmp_managers().items)
    for mgr in mgrs:
        if mgr.name == module.params["name"]:
            mgr_configured = True
            break
    if not module.params["host"]:
        module.fail_json(msg="The following parameter is required: host")
    if module.params["version"] == "v3":
        if not module.params["user"]:
            module.fail_json(msg="version is v3 but the following is missing: user")
        if module.params["auth_passphrase"] and not (
            8 <= len(module.params["auth_passphrase"]) <= 32
        ):
            module.fail_json(msg="auth_password must be between 8 and 32 characters")
        if module.params["privacy_passphrase"] and not (
            8 <= len(module.params["privacy_passphrase"]) <= 63
        ):
            module.fail_json(msg="privacy_password must be between 8 and 63 characters")
    else:
        if not module.params["community"]:
            module.fail_json(
                msg="version is v2c but the following is missing: community"
            )
    if state == "absent" and mgr_configured:
        delete_manager(module, array)
    elif mgr_configured and state == "present":
        update_manager(module, array)
    elif mgr_configured and state == "test":
        test_manager(module, array)
    elif not mgr_configured and state == "present":
        create_manager(module, array)
    else:
        module.exit_json(changed=False)


if __name__ == "__main__":
    main()
