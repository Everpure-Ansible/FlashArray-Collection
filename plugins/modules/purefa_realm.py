#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_realm
version_added: '1.33.0'
short_description: Manage realms on Everpure FlashArrays
description:
- Create, delete or modify realms on Everpure FlashArrays.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the realm.
    - This has to be unique and not equal to any existing realm or pod.
    type: str
    required: true
  state:
    description:
    - Define whether the realm should exist or not.
    type: str
    default: present
    choices: [ absent, present ]
  eradicate:
    description:
    - Define whether to eradicate the realm on delete or leave in trash.
    type : bool
    default: false
  quota:
    description:
      - Logical quota limit of the realm in K, M, G, T or P units, or bytes.
      - This must be a multiple of 512.
    type: str
  bw_qos:
    description:
    - Bandwidth limit for realm in M or G units.
      M will set MB/s
      G will set GB/s
      To clear an existing QoS setting use 0 (zero)
    type: str
  iops_qos:
    description:
    - IOPs limit for realm - use value or K or M
      K will mean 1000
      M will mean 1000000
      To clear an existing IOPs setting use 0 (zero)
    type: str
  rename:
    description:
    - Value to rename the specified realm to
    - This has to be unique and not equal to any existing realm or pods.
    type: str
  ignore_usage:
    description:
    -  Flag used to override checks for quota management
       operations.
    - If set to true, realm usage is not checked against the
      quota_limits that are set.
    - If set to false, the actual logical bytes in use are prevented
      from exceeding the limits set in the realm.
    - Client operations might be impacted.
    - If the limit exceeds the quota, the operation is not allowed.
    default: false
    type: bool
  delete_contents:
    description:
    - This enables you to eradicate realms with contents.
    type: bool
    default: False
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create new realm
  everpure.flasharray.purefa_realm:
    name: foo
    bw_qos: 50M
    iops_qos: 100
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Update realm QoS limits
  everpure.flasharray.purefa_realm:
    name: foo
    bw_qos: 0
    iops_qos: 5555
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Destroy realm
  everpure.flasharray.purefa_realm:
    name: foo
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Recover deleted realm
  everpure.flasharray.purefa_realm:
    name: foo
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Destroy and Eradicate realm
  everpure.flasharray.purefa_realm:
    name: foo
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Rename realm foo to bar
  everpure.flasharray.purefa_realm:
    name: foo
    rename: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import RealmPatch, RealmPost, ContainerQos
except ImportError:
    HAS_PURESTORAGE = False

try:
    # Only this model accepts the empty string that clears a QoS limit
    from pypureclient.flasharray import ContainerQosPatch
except ImportError:
    ContainerQosPatch = None

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.common import (
    human_to_bytes,
    human_to_real,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_response,
)

MINIMUM_API_VERSION = "2.36"


def get_pending_realm(module, array):
    """Get Deleted realm"""
    vgroup = None
    res = array.get_realms(names=[module.params["name"]])
    if res.status_code == 200:
        vgroup = list(res.items)[0].destroyed
    return vgroup


def get_realm(module, array):
    """Get Realm"""
    vgroup = None
    res = array.get_realms(names=[module.params["name"]])
    if res.status_code == 200:
        if not list(res.items)[0].destroyed:
            vgroup = True
    return vgroup


def get_renamed_realm(module, array):
    """True when the rename target already exists (a completed rename)"""
    res = array.get_realms(names=[module.params["rename"]])
    return bool(res.status_code == 200 and not list(res.items)[0].destroyed)


def qos_clear_requested(value):
    """True when a QoS parameter asks for the limit to be removed"""
    return value is not None and str(value).strip() in ("", "0")


def clear_qos_patch(module, **limits):
    """Build the QoS patch that removes the given limits

    The REST API clears a container QoS limit with an empty string, which
    only the ContainerQosPatch model accepts.
    """
    if ContainerQosPatch is None:
        module.fail_json(
            msg="Clearing realm QoS limits requires a py-pure-client release "
            "that provides the ContainerQosPatch model."
        )
    return ContainerQosPatch(**{key: "" for key in limits})


def rename_realm(module, array):
    changed = True
    if not module.check_mode:
        res = array.patch_realms(
            names=[module.params["name"]],
            realm=RealmPatch(name=module.params["rename"]),
        )
        check_response(res, module, f"Rename to {module.params['rename']}")
    module.exit_json(changed=changed)


def make_realm(module, array):
    """Create Realm"""
    changed = True
    if module.params["quota"]:
        quota = int(human_to_bytes(module.params["quota"]))
        if quota % 512 != 0:
            module.fail_json(msg="Quota not a multiple of 512 bytes")
        if quota < 1048576:
            module.fail_json(
                msg="Quota must be a value greater than or equal to 1048576 bytes"
            )
        if not module.check_mode:
            res = array.post_realms(
                names=[module.params["name"]], realm=RealmPost(quota_limit=quota)
            )
            check_response(res, module, f"Creation of realm {module.params['name']}")
    else:
        if not module.check_mode:
            res = array.post_realms(names=[module.params["name"]])
            check_response(res, module, f"Creation of realm {module.params['name']}")
    if module.params["bw_qos"] and not module.params["iops_qos"]:
        if int(human_to_bytes(module.params["bw_qos"])) in range(1048576, 549755813888):
            changed = True
            if not module.check_mode:
                res = array.patch_realms(
                    names=[module.params["name"]],
                    realm=RealmPatch(
                        qos=ContainerQos(
                            bandwidth_limit=int(human_to_bytes(module.params["bw_qos"]))
                        )
                    ),
                )
                check_response(
                    res, module, f"Setting of realm {module.params['name']} QoS"
                )
        else:
            module.fail_json(
                msg="Bandwidth QoS value {0} out of range.".format(
                    module.params["bw_qos"]
                )
            )
    elif module.params["iops_qos"] and not module.params["bw_qos"]:
        if int(human_to_real(module.params["iops_qos"])) in range(100, 100000000):
            changed = True
            if not module.check_mode:
                res = array.patch_realms(
                    names=[module.params["name"]],
                    realm=RealmPatch(
                        qos=ContainerQos(
                            iops_limit=int(human_to_real(module.params["iops_qos"]))
                        )
                    ),
                )
                check_response(
                    res, module, f"Setting of realm {module.params['name']} QoS"
                )
        else:
            module.fail_json(
                msg="IOPs QoS value {0} out of range.".format(module.params["iops_qos"])
            )
    elif module.params["iops_qos"] and module.params["bw_qos"]:
        bw_qos_size = int(human_to_bytes(module.params["bw_qos"]))
        if int(human_to_real(module.params["iops_qos"])) in range(
            100, 100000000
        ) and bw_qos_size in range(1048576, 549755813888):
            changed = True
            if not module.check_mode:
                res = array.patch_realms(
                    names=[module.params["name"]],
                    realm=RealmPatch(
                        qos=ContainerQos(
                            iops_limit=int(human_to_real(module.params["iops_qos"])),
                            bandwidth_limit=int(
                                human_to_bytes(module.params["bw_qos"])
                            ),
                        ),
                    ),
                )
                check_response(
                    res, module, f"Setting of realm {module.params['name']} QoS"
                )
        else:
            module.fail_json(msg="IOPs or Bandwidth QoS value out of range.")

    module.exit_json(changed=changed)


def update_realm(module, array):
    """Update Realm"""
    changed = False
    realm = list(array.get_realms(names=[module.params["name"]]).items)[0]
    current_realm = {
        "quota": realm.quota_limit,
        "bw": getattr(realm.qos, "bandwidth_limit", 0) or 0,
        "iops": getattr(realm.qos, "iops_limit", 0) or 0,
    }
    if qos_clear_requested(module.params["bw_qos"]):
        if current_realm["bw"]:
            changed = True
            if not module.check_mode:
                res = array.patch_realms(
                    names=[module.params["name"]],
                    realm=RealmPatch(qos=clear_qos_patch(module, bandwidth_limit=True)),
                )
                check_response(
                    res,
                    module,
                    f"Realm {module.params['name']} Bandwidth QoS clear",
                )
    elif module.params["bw_qos"]:
        if int(human_to_bytes(module.params["bw_qos"])) != current_realm["bw"]:
            if int(human_to_bytes(module.params["bw_qos"])) in range(
                1048576, 549755813888
            ):
                changed = True
                if not module.check_mode:
                    res = array.patch_realms(
                        names=[module.params["name"]],
                        realm=RealmPatch(
                            qos=ContainerQos(
                                bandwidth_limit=int(
                                    human_to_bytes(module.params["bw_qos"])
                                )
                            )
                        ),
                    )
                    check_response(
                        res,
                        module,
                        f"Realm {module.params['name']} Bandwidth QoS change",
                    )
            else:
                module.fail_json(
                    msg="Bandwidth QoS value {0} out of range.".format(
                        module.params["bw_qos"]
                    )
                )
    if qos_clear_requested(module.params["iops_qos"]):
        if current_realm["iops"]:
            changed = True
            if not module.check_mode:
                res = array.patch_realms(
                    names=[module.params["name"]],
                    realm=RealmPatch(qos=clear_qos_patch(module, iops_limit=True)),
                )
                check_response(
                    res,
                    module,
                    f"Realm {module.params['name']} IOPs QoS clear",
                )
    elif module.params["iops_qos"]:
        if int(human_to_real(module.params["iops_qos"])) != current_realm["iops"]:
            if int(human_to_real(module.params["iops_qos"])) in range(100, 100000000):
                changed = True
                if not module.check_mode:
                    res = array.patch_realms(
                        names=[module.params["name"]],
                        realm=RealmPatch(
                            qos=ContainerQos(
                                iops_limit=int(human_to_real(module.params["iops_qos"]))
                            )
                        ),
                    )
                    check_response(
                        res,
                        module,
                        f"Realm {module.params['name']} IOPs QoS change",
                    )
            else:
                module.fail_json(
                    msg="IOPs QoS value {0} out of range.".format(
                        module.params["iops_qos"]
                    )
                )
    if module.params["quota"]:
        if int(human_to_bytes(module.params["quota"])) != current_realm["quota"]:
            if int(human_to_bytes(module.params["quota"])) % 512 == 0:
                changed = True
                if not module.check_mode:
                    res = array.patch_realms(
                        names=[module.params["name"]],
                        realm=RealmPatch(
                            quota_limit=int(human_to_bytes(module.params["quota"]))
                        ),
                    )
                    check_response(
                        res,
                        module,
                        f"Realm {module.params['name']} quota change",
                    )
            else:
                module.fail_json(
                    msg="Realm quota {0} not a multiple of 512.".format(
                        module.params["quota"]
                    )
                )

    module.exit_json(changed=changed)


def recover_realm(module, array):
    """Recover Realm"""
    changed = True
    if not module.check_mode:
        res = array.patch_realms(
            names=[module.params["name"]], realm=RealmPatch(destroyed=False)
        )
        check_response(res, module, f"Recovery of realm {module.params['name']}")

    module.exit_json(changed=changed)


def eradicate_realm(module, array):
    """Eradicate Realm"""
    changed = True
    if not module.check_mode:
        res = array.delete_realms(
            names=[module.params["name"]],
            eradicate_contents=module.params["delete_contents"],
        )
        check_response(res, module, f"Eradicating realm {module.params['name']}")
    module.exit_json(changed=changed)


def delete_realm(module, array):
    """Delete Realm"""
    changed = True
    if not module.check_mode:
        res = array.patch_realms(
            names=[module.params["name"]],
            destroy_contents=module.params["delete_contents"],
            ignore_usage=module.params["ignore_usage"],
            realm=RealmPatch(destroyed=True),
        )
        check_response(res, module, f"Deleting realm {module.params['name']}")
    if module.params["eradicate"]:
        eradicate_realm(module, array)

    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            bw_qos=dict(type="str"),
            iops_qos=dict(type="str"),
            quota=dict(type="str"),
            eradicate=dict(type="bool", default=False),
            rename=dict(type="str"),
            delete_contents=dict(type="bool", default=False),
            ignore_usage=dict(type="bool", default=False),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    state = module.params["state"]
    array = get_array(module)
    api_version = array.get_rest_version()
    if LooseVersion(MINIMUM_API_VERSION) > LooseVersion(api_version):
        module.fail_json(
            msg="Realms are not supported. Purity//FA 6.6.11, or higher, is required."
        )
    realm = get_realm(module, array)
    xrealm = get_pending_realm(module, array)

    if xrealm and state == "present":
        recover_realm(module, array)
    elif realm and state == "absent":
        delete_realm(module, array)
    elif xrealm and state == "absent" and module.params["eradicate"]:
        eradicate_realm(module, array)
    elif (
        not realm
        and not xrealm
        and state == "present"
        and module.params["rename"]
        and get_renamed_realm(module, array)
    ):
        # Rename already completed on an earlier run; do not recreate the
        # source realm under its old name.
        module.exit_json(changed=False)
    elif not realm and not xrealm and state == "present":
        make_realm(module, array)
    elif state == "present" and realm and module.params["rename"] and not xrealm:
        rename_realm(module, array)
    elif realm and state == "present":
        update_realm(module, array)
    elif realm is None and state == "absent":
        module.exit_json(changed=False)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
