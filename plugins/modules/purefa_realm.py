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
    - The array accepts values from 1M (1048576 bytes/s) to 512G.
    - To clear an existing QoS setting use 0 (zero)
    type: str
  iops_qos:
    description:
    - IOPs limit for realm - use value or K or M
      K will mean 1000
      M will mean 1000000
    - The array accepts values from 100 to 100M.
    - To clear an existing IOPs setting use 0 (zero)
    type: str
  bw_floor:
    description:
    - Bandwidth floor for the realm, in the same units as I(bw_qos).
    - While the array is under contention the realm's I/O is prioritized
      until it reaches this bandwidth. A floor is a target, not a
      reservation, and has no effect while the array is not under contention.
    - The array accepts values from 1M (1048576 bytes/s) to 512G.
    - To clear an existing floor use 0 (zero)
    - Requires Purity//FA REST API 2.47 or higher. QoS floors on realms
      became generally available in Purity//FA 6.10.0.
    type: str
    version_added: '1.47.0'
  iops_floor:
    description:
    - IOPs floor for the realm, in the same units as I(iops_qos).
    - While the array is under contention the realm's I/O is prioritized
      until it reaches this many IOPs. A floor is a target, not a
      reservation, and has no effect while the array is not under contention.
    - The array accepts values from 100 to 100M.
    - To clear an existing floor use 0 (zero)
    - Requires Purity//FA REST API 2.47 or higher. QoS floors on realms
      became generally available in Purity//FA 6.10.0.
    type: str
    version_added: '1.47.0'
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
notes:
- QoS limits and floors given in the same task are applied to the realm in
  a single request, and a new realm is created with its QoS settings in
  place rather than having them added afterwards.
- The array does not stop a floor being set higher than the matching
  limit, but a realm can never reach such a floor because the limit still
  applies. Floors are honoured before any priority weighting.
"""

EXAMPLES = r"""
- name: Create new realm
  everpure.flasharray.purefa_realm:
    name: foo
    bw_qos: 50M
    iops_qos: 100
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create new realm with QoS limits and floors
  everpure.flasharray.purefa_realm:
    name: gold
    bw_qos: 2G
    iops_qos: 100K
    bw_floor: 500M
    iops_floor: 20K
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Update realm QoS limits
  everpure.flasharray.purefa_realm:
    name: foo
    bw_qos: 0
    iops_qos: 5555
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Set QoS floors on an existing realm
  everpure.flasharray.purefa_realm:
    name: foo
    bw_floor: 100M
    iops_floor: 5K
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Remove the QoS floors from a realm
  everpure.flasharray.purefa_realm:
    name: foo
    bw_floor: 0
    iops_floor: 0
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
    # Only this model accepts the empty string that clears a QoS value
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
    check_api_version,
    check_response,
)

MINIMUM_API_VERSION = "2.36"
# bandwidth_floor and iops_floor joined the container QoS object in this version
FLOOR_API_VERSION = "2.47"
MIN_BWS = 1048576
MAX_BWS = 549755813888
MIN_IOPS = 100
MAX_IOPS = 100000000

# Module option -> the container QoS field it drives
QOS_FIELDS = {
    "bw_qos": "bandwidth_limit",
    "iops_qos": "iops_limit",
    "bw_floor": "bandwidth_floor",
    "iops_floor": "iops_floor",
}
QOS_LABELS = {
    "bw_qos": "Bandwidth QoS",
    "iops_qos": "IOPs QoS",
    "bw_floor": "Bandwidth floor",
    "iops_floor": "IOPs floor",
}
FLOOR_OPTIONS = ("bw_floor", "iops_floor")


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
    """True when a QoS parameter asks for the value to be removed"""
    return value is not None and str(value).strip() in ("", "0")


def floors_requested(module):
    """True when the task names either QoS floor option"""
    return any(module.params[option] is not None for option in FLOOR_OPTIONS)


def parse_qos_value(module, option):
    """The value the array expects for a QoS option

    Returns None when the option was not given, the empty string when the
    option asks for the current value to be removed, and otherwise the
    integer the array expects, checked against the range it enforces.
    """
    value = module.params[option]
    if value is None:
        return None
    if qos_clear_requested(value):
        return ""
    if option in ("bw_qos", "bw_floor"):
        number = int(human_to_bytes(value))
        low, high = MIN_BWS, MAX_BWS
    else:
        number = int(human_to_real(value))
        low, high = MIN_IOPS, MAX_IOPS
    if not low <= number <= high:
        module.fail_json(
            msg="{0} value {1} out of range.".format(QOS_LABELS[option], value)
        )
    return number


def requested_qos(module):
    """Container QoS field -> wanted value, for every QoS option given"""
    wanted = {}
    for option, field in QOS_FIELDS.items():
        value = parse_qos_value(module, option)
        if value is not None:
            wanted[field] = value
    return wanted


def current_qos(realm):
    """Container QoS field -> value the realm has now (0 when unset)"""
    qos = getattr(realm, "qos", None)
    return {field: getattr(qos, field, 0) or 0 for field in QOS_FIELDS.values()}


def qos_changes(module, current):
    """The QoS fields whose wanted value differs from the realm's"""
    changes = {}
    for field, wanted in requested_qos(module).items():
        if wanted == "":
            if current[field]:
                changes[field] = ""
        elif wanted != current[field]:
            changes[field] = wanted
    return changes


def qos_model(module, fields):
    """The SDK object that carries the given container QoS fields

    The REST API clears a container QoS value with an empty string, which
    only the ContainerQosPatch model accepts.
    """
    if "" in fields.values():
        if ContainerQosPatch is None:
            module.fail_json(
                msg="Clearing realm QoS values requires a py-pure-client release "
                "that provides the ContainerQosPatch model."
            )
        return ContainerQosPatch(**fields)
    return ContainerQos(**fields)


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
    realm = {}
    if module.params["quota"]:
        quota = int(human_to_bytes(module.params["quota"]))
        if quota % 512 != 0:
            module.fail_json(msg="Quota not a multiple of 512 bytes")
        if quota < 1048576:
            module.fail_json(
                msg="Quota must be a value greater than or equal to 1048576 bytes"
            )
        realm["quota_limit"] = quota
    # A new realm has nothing to clear, so only values to set are sent
    qos = {
        field: value for field, value in requested_qos(module).items() if value != ""
    }
    if qos:
        realm["qos"] = ContainerQos(**qos)
    if not module.check_mode:
        if realm:
            res = array.post_realms(
                names=[module.params["name"]], realm=RealmPost(**realm)
            )
        else:
            res = array.post_realms(names=[module.params["name"]])
        check_response(res, module, f"Creation of realm {module.params['name']}")
    module.exit_json(changed=changed)


def update_realm(module, array):
    """Update Realm"""
    changed = False
    realm = list(array.get_realms(names=[module.params["name"]]).items)[0]
    changes = qos_changes(module, current_qos(realm))
    if changes:
        changed = True
        if not module.check_mode:
            res = array.patch_realms(
                names=[module.params["name"]],
                realm=RealmPatch(qos=qos_model(module, changes)),
            )
            check_response(res, module, f"Realm {module.params['name']} QoS change")
    if module.params["quota"]:
        if int(human_to_bytes(module.params["quota"])) != realm.quota_limit:
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
            bw_floor=dict(type="str"),
            iops_floor=dict(type="str"),
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
    if floors_requested(module):
        check_api_version(array, FLOOR_API_VERSION, module, "Realm QoS floor support")
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
