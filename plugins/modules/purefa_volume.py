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
module: purefa_volume
version_added: '1.0.0'
short_description:  Manage volumes on Everpure FlashArrays
description:
- Create, delete or extend the capacity of a volume on Everpure FlashArray.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the volume.
    - Volume could be created in a POD with this syntax POD_NAME::VOLUME_NAME.
    - If the pod is in a realm use the syntax REALM_NAME::POD_NAME::VOLUME_NAME.
    - Volume could be created in a volume group with this syntax VG_NAME/VOLUME_NAME.
    - Multi-volume support available from Purity//FA 6.0.0
      B(***NOTE***) Manual deletion or eradication of individual volumes created
      using multi-volume will cause idempotency to fail
    - Multi-volume support only exists for volume creation
    - When copying with I(target), the name may also be a volume snapshot,
      including a protection group snapshot inside a pod, for example
      C(pod::pgroup.suffix.volume). The snapshot is copied to I(target).
    type: str
    required: true
  target:
    description:
    - The name of the target volume, if copying.
    - The copy source I(name) may be a volume or a volume snapshot.
    type: str
  state:
    description:
    - Define whether the volume should exist or not.
    default: present
    choices: [ absent, present ]
    type: str
  eradicate:
    description:
    - Define whether to eradicate the volume on delete or leave in trash.
    type: bool
    default: false
  overwrite:
    description:
    - Define whether to overwrite a target volume if it already exists.
    type: bool
    default: false
  size:
    description:
    - Volume size in M, G, T or P units.
    type: str
  count:
    description:
    - Number of volumes to be created in a multiple volume creation
    - Only supported from Purity//FA v6.0.0 and higher
    type: int
  start:
    description:
    - Number at which to start the multiple volume creation index
    - Only supported from Purity//FA v6.0.0 and higher
    type: int
    default: 0
  digits:
    description:
    - Number of digits to use for multiple volume count. This
      will pad the index number with zeros where necessary
    - Only supported from Purity//FA v6.0.0 and higher
    - Range is between 1 and 10
    type: int
    default: 1
  suffix:
    description:
    - Suffix string, if required, for multiple volume create
    - Volume names will be formed as I(<name>#I<suffix>), where
      I(#) is a placeholder for the volume index
      See associated descriptions
    - Only supported from Purity//FA v6.0.0 and higher
    type: str
    default: ""
  bw_qos:
    description:
    - Bandwidth limit for volume in M or G units.
      M will set MB/s
      G will set GB/s
      To clear an existing QoS setting use 0 (zero)
    type: str
    aliases: [ qos ]
  iops_qos:
    description:
    - IOPs limit for volume - use value or K or M
      K will mean 1000
      M will mean 1000000
      To clear an existing IOPs setting use 0 (zero)
    type: str
  move:
    description:
    - Move a volume in and out of a pod or vgroup
    - Provide the name of pod or vgroup to move the volume to
    - Pod and Vgroup names must be unique in the array
    - To move to the local array, specify C(local)
    - This is not idempotent - use C(ignore_errors) in the play
    type: str
  rename:
    description:
    - Value to rename the specified volume to.
    - Rename only applies to the container the current volumes is in.
    - There is no requirement to specify the pod or vgroup name as this is implied.
    type: str
  pgroup:
    description:
    - Name of existing, not deleted, protection group to add volume to
    - Only application for volume(s) creation
    - Superseded from Purity//FA 6.3.4 by I(add_to_pgs)
    type: str
    version_added: 1.8.0
  priority_operator:
    description:
    - DMM Priority Adjustment operator
    type: str
    choices: [ '=', '+', '-' ]
    version_added: '1.13.0'
  priority_value:
    description:
    - DMM Priority Adjustment value
    type: int
    choices: [ -10, 0, 10 ]
    version_added: '1.13.0'
  with_default_protection:
    description:
    - Whether to add the default container protection groups to
      those specified in I(add_to_pgs) as the initial protection
      of a new volume.
    type: bool
    default: true
    version_added: '1.14.0'
  add_to_pgs:
    description:
    - A new volume will be added to the specified protection groups
      on creation
    type: list
    elements: str
    version_added: '1.14.0'
  promotion_state:
    description:
    - Promote or demote the volume so that the volume starts or
      stops accepting write requests.
    type: str
    choices: [ promoted, demoted ]
    version_added: '1.16.0'
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
    version_added: '1.33.0'
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create new volume named foo with a QoS limit
  everpure.flasharray.purefa_volume:
    name: foo
    size: 1T
    bw_qos: 58M
    iops_qos: 23K
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Create new volume named foo with a DMM priority (Purity//FA 6.1.2+)
  everpure.flasharray.purefa_volume:
    name: foo
    size: 1T
    priority_operator: +
    priority_value: 10
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Create new volume named foo in protection group pg1 (this cannot be used with context)
  everpure.flasharray.purefa_volume:
    name: foo
    pgroup: pg1
    size: 1T
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Create 10 volumes with index starting at 10 but padded with 3 digits
  everpure.flasharray.purefa_volume:
    name: foo
    size: 1T
    suffix: bar
    count: 10
    start: 10
    digits: 3
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Extend the size of an existing volume named foo
  everpure.flasharray.purefa_volume:
    name: foo
    size: 2T
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Delete and eradicate volume named foo
  everpure.flasharray.purefa_volume:
    name: foo
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Create clone of volume bar named foo
  everpure.flasharray.purefa_volume:
    name: foo
    target: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Overwrite volume bar with volume foo
  everpure.flasharray.purefa_volume:
    name: foo
    target: bar
    overwrite: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Restore volume vol1 in pod ac-test from a protection group snapshot
  everpure.flasharray.purefa_volume:
    name: ac-test::hourly.drill1.vol1
    target: ac-test::vol1
    overwrite: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Clear volume QoS from volume foo
  everpure.flasharray.purefa_volume:
    name: foo
    bw_qos: 0
    iops_qos: 0
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Move local volume foo from local array to pod bar
  everpure.flasharray.purefa_volume:
    name: foo
    move: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Move volume foo in pod bar to local array
  everpure.flasharray.purefa_volume:
    name: bar::foo
    move: local
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Move volume foo in pod bar to vgroup fin
  everpure.flasharray.purefa_volume:
    name: bar::foo
    move: fin
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
volume:
    description: A dictionary describing the changed volume.  Only some
        attributes below will be returned with various actions.
    type: dict
    returned: success
    contains:
        source:
            description: Volume name of source volume used for volume copy
            type: str
        serial:
            description: Volume serial number
            type: str
            sample: '361019ECACE43D83000120A4'
        nvme_nguid:
            description: Volume NVMe namespace globally unique identifier
            type: str
            sample: 'eui.00cd6b99ef25864724a937c5000be684'
        page83_naa:
            description: Volume NAA canonical name
            type: str
            sample: 'naa.624a9370361019ecace43db3000120a4'
        created:
            description: Volume creation time
            type: str
            sample: '2019-03-13T22:49:24Z'
        name:
            description: Volume name
            type: str
        size:
            description: Volume size in bytes
            type: int
        bandwidth_limit:
            description: Volume bandwidth limit in bytes/sec
            type: int
        iops_limit:
            description: Volume IOPs limit
            type: int
        priority_operator:
            description: DMM Priority Adjustment operator
            type: str
        priority_value:
            description: DMM Priority Adjustment value
            type: int
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        Qos,
        VolumePost,
        VolumePatch,
        PriorityAdjustment,
        Reference,
        ReferenceType,
    )
except ImportError:
    HAS_PURESTORAGE = False

import re
import time
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
    get_with_context,
    post_with_context,
    patch_with_context,
    delete_with_context,
)

PURE_OUI = "naa.624a9370"
PRIORITY_API_VERSION = "2.11"
DEFAULT_API_VERSION = "2.16"
CONTEXT_API_VERSION = "2.38"


def _volfact(module, array, volume_name):
    api_version = array.get_rest_version()
    if not module.check_mode:
        volume_data = list(
            get_with_context(
                array, "get_volumes", CONTEXT_API_VERSION, module, names=[volume_name]
            ).items
        )[0]
        volfact = {
            volume_name: {
                "size": volume_data.provisioned,
                "serial": volume_data.serial,
                "created": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(volume_data.created / 1000)
                ),
                "page83_naa": PURE_OUI + volume_data.serial.lower(),
                "nvme_nguid": _create_nguid(volume_data.serial.lower()),
                "iops_limit": getattr(volume_data.qos, "iops_limit", 0),
                "bandwidth_limit": getattr(volume_data.qos, "bandwidth_limit", 0),
                "requested_promotion_state": volume_data.requested_promotion_state,
                "promotion_status": volume_data.promotion_status,
                "priority": getattr(volume_data, "priority", 0),
                "priority_operator": "",
                "priority_value": "",
                "destroyed": volume_data.destroyed,
            }
        }
        if LooseVersion(PRIORITY_API_VERSION) <= LooseVersion(api_version):
            volfact[volume_name][
                "priority_operator"
            ] = volume_data.priority_adjustment.priority_adjustment_operator
            volfact[volume_name][
                "priority_value"
            ] = volume_data.priority_adjustment.priority_adjustment_value
        if LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version):
            volfact[volume_name]["context"] = volume_data.context.name
    else:
        volfact = {}
    return volfact


def _create_nguid(serial):
    nguid = "eui.00" + serial[0:14] + "24a937" + serial[-10:]
    return nguid


def get_pod(module, array):
    """Get ActiveCluster Pod"""
    api_version = array.get_rest_version()
    pod_name = "::".join(module.params["pgroup"].split("::")[:-1])
    res = get_with_context(
        array, "get_pods", CONTEXT_API_VERSION, module, names=[pod_name]
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def get_pending_pgroup(module, array):
    """Get Protection Group"""
    api_version = array.get_rest_version()
    res = get_with_context(
        array,
        "get_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["pgroup"]],
    )
    if res.status_code == 200:
        pgroup = list(res.items)[0]
        if pgroup.destroyed:
            return list(res.items)[0]
    return None


def get_pgroup(module, array):
    """Get Protection Group"""
    api_version = array.get_rest_version()
    res = get_with_context(
        array,
        "get_protection_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["pgroup"]],
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def pg_exists(module, pgs, array):
    """Get Protection Group"""
    api_version = array.get_rest_version()
    res = get_with_context(
        array, "get_protection_groups", CONTEXT_API_VERSION, module, names=[pgs]
    )
    return bool(res.status_code == 200)


def get_multi_volumes(module, array):
    """Return True is all volumes exist or None"""
    names = []
    api_version = array.get_rest_version()
    for vol_num in range(
        module.params["start"], module.params["count"] + module.params["start"]
    ):
        names.append(
            module.params["name"]
            + str(vol_num).zfill(module.params["digits"])
            + module.params["suffix"]
        )
    res = get_with_context(
        array, "get_volumes", CONTEXT_API_VERSION, module, names=names, destroyed=False
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def get_volume(module, array):
    """Return Volume or None"""
    api_version = array.get_rest_version()
    res = get_with_context(
        array,
        "get_volumes",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        destroyed=False,
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def get_endpoint(module, name, array):
    """Return Endpoint or None"""
    api_version = array.get_rest_version()
    res = get_with_context(
        array, "get_volumes", CONTEXT_API_VERSION, module, names=[name]
    )
    if res.status_code == 200:
        volume = list(res.items)[0]
        if volume.subtype == "protocol_endpoint":
            return volume
    return None


def get_destroyed_volume(module, array):
    """Return Destroyed Volume or None"""
    api_version = array.get_rest_version()
    res = get_with_context(
        array,
        "get_volumes",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        destroyed=True,
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def get_target(module, array):
    """Return Volume or None"""
    api_version = array.get_rest_version()
    res = get_with_context(
        array,
        "get_volumes",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["target"]],
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def get_source_snapshot(module, array):
    """Return the volume snapshot named by I(name), or None.

    A copy source may be a volume snapshot as well as a volume, including a
    protection group snapshot inside a pod (``pod::pgroup.suffix.volume``).
    """
    res = get_with_context(
        array,
        "get_volume_snapshots",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
    )
    if res.status_code == 200:
        return list(res.items)[0]
    return None


def check_vgroup(module, array):
    """Check is the requested VG to create volume in exists"""
    api_version = array.get_rest_version()
    vg_name = module.params["name"].split("/")[0]
    res = get_with_context(
        array, "get_volume_groups", CONTEXT_API_VERSION, module, names=[vg_name]
    )
    return bool(res.status_code == 200)


def check_pod(module, array):
    """Check is the requested pod to create volume in exists"""
    api_version = array.get_rest_version()
    pod_name = "::".join(module.params["name"].split("::")[:-1])
    res = get_with_context(
        array, "get_pods", CONTEXT_API_VERSION, module, names=[pod_name]
    )
    return bool(res.status_code == 200)


def create_volume(module, array):
    """Create Volume"""
    changed = False
    api_version = array.get_rest_version()
    if module.params["add_to_pgs"]:
        module.fail_json(msg="For Purity//FA 6.3.4 or lower, use pgroup parameter")
    if "/" in module.params["name"] and not check_vgroup(module, array):
        module.fail_json(
            msg="Failed to create volume {0}. Volume Group does not exist.".format(
                module.params["name"]
            )
        )
    if "::" in module.params["name"]:
        if not check_pod(module, array):
            module.fail_json(
                msg="Failed to create volume {0}. Pod does not exist".format(
                    module.params["name"]
                )
            )
        pod_name = "::".join(module.params["name"].split("::")[:-1])
        res = list(
            get_with_context(
                array, "get_pods", CONTEXT_API_VERSION, module, names=[pod_name]
            ).items
        )[0]
        if res.promotion_status == "demoted":
            module.fail_json(msg="Volume cannot be created in a demoted pod")
    if not module.params["size"]:
        module.fail_json(msg="Size for a new volume must be specified")
    if module.params["bw_qos"] or module.params["iops_qos"]:
        if module.params["bw_qos"] and not module.params["iops_qos"]:
            changed = True
            if not module.check_mode:
                res = post_with_context(
                    array,
                    "post_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=VolumePost(
                        provisioned=int(human_to_bytes(module.params["size"])),
                        qos=Qos(
                            bandwidth_limit=int(human_to_bytes(module.params["bw_qos"]))
                        ),
                    ),
                )
                check_response(res, module, f"Volume {module.params['name']} creation")
        elif module.params["iops_qos"] and not module.params["bw_qos"]:
            changed = True
            if not module.check_mode:
                res = post_with_context(
                    array,
                    "post_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=VolumePost(
                        provisioned=int(human_to_bytes(module.params["size"])),
                        qos=Qos(iops_limit=int(module.params["iops_qos"])),
                    ),
                )
                check_response(res, module, f"Volume {module.params['name']} creation")
        else:
            changed = True
            if not module.check_mode:
                res = post_with_context(
                    array,
                    "post_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=VolumePost(
                        provisioned=int(human_to_bytes(module.params["size"])),
                        qos=Qos(
                            iops_limit=int(human_to_real(module.params["iops_qos"])),
                            bandwidth_limit=int(
                                human_to_bytes(module.params["bw_qos"])
                            ),
                        ),
                    ),
                )
                check_response(res, module, f"Volume {module.params['name']} creation")
    else:
        changed = True
        if not module.check_mode:
            res = post_with_context(
                array,
                "post_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume=VolumePost(
                    provisioned=int(human_to_bytes(module.params["size"]))
                ),
            )
            check_response(res, module, f"Volume {module.params['name']} creation")
    if module.params["promotion_state"]:
        volume = VolumePatch(requested_promotion_state=module.params["promotion_state"])
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume=volume,
            )
            if res.status_code != 200:
                message = res.errors[0].message
                patch_with_context(
                    array,
                    "patch_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=VolumePatch(destroyed=True),
                )
                array.delete_volumes(names=[module.params["name"]])
                module.fail_json(
                    msg="Failed to set Promotion State for volume {0}. Error: {1}".format(
                        module.params["name"],
                        message,
                    )
                )
    if module.params["priority_operator"]:
        volume = VolumePatch(
            priority_adjustment=PriorityAdjustment(
                priority_adjustment_operator=module.params["priority_operator"],
                priority_adjustment_value=module.params["priority_value"],
            )
        )
        res = patch_with_context(
            array,
            "patch_volumes",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            volume=volume,
        )
        if res.status_code != 200:
            message = res.errors[0].message
            patch_with_context(
                array,
                "patch_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume=VolumePatch(destroyed=True),
            )
            array.delete_volumes(names=[module.params["name"]])
            module.fail_json(
                msg="Failed to set DMM Priority Adjustment on volume {0}. Error: {1}".format(
                    module.params["name"], message
                )
            )
    if module.params["pgroup"]:
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                add_to_protection_groups=ReferenceType(name=module.params["pgroup"]),
            )
            if res.status_code != 200:
                module.warn(
                    "Failed to add {0} to protection group {1}. Error: {2}".format(
                        module.params["name"],
                        module.params["pgroup"],
                        res.errors[0].message,
                    )
                )

    module.exit_json(
        changed=changed, volume=_volfact(module, array, module.params["name"])
    )


def create_multi_volume(module, array, single=False):
    """Create Volume"""
    volfact = {}
    vols = VolumePost()
    changed = True
    api_version = array.get_rest_version()
    if module.params["pgroup"]:
        module.fail_json(msg="For Purity//FA 6.3.4 or higher, use add_to_pgs parameter")
    names = []
    if "/" in module.params["name"] and not check_vgroup(module, array):
        module.fail_json(
            msg="Multi-volume create failed. Volume Group {0} does not exist.".format(
                module.params["name"].split("/")[0]
            )
        )
    if "::" in module.params["name"]:
        if not check_pod(module, array):
            module.fail_json(
                msg="Multi-volume create failed. Pod {0} does not exist".format(
                    "::".join(module.params["name"].split("::")[:-1])
                )
            )
        pod_name = "::".join(module.params["name"].split("::")[:-1])
        if (
            list(
                get_with_context(
                    array, "get_pods", CONTEXT_API_VERSION, module, names=[pod_name]
                ).items
            )[0].promotion_status
            == "demoted"
        ):
            module.fail_json(msg="Volume cannot be created in a demoted pod")
    if not single:
        for vol_num in range(
            module.params["start"], module.params["count"] + module.params["start"]
        ):
            names.append(
                module.params["name"]
                + str(vol_num).zfill(module.params["digits"])
                + module.params["suffix"]
            )
    else:
        names.append(module.params["name"])
    if module.params["bw_qos"] and module.params["iops_qos"]:
        vols = VolumePost(
            provisioned=int(human_to_bytes(module.params["size"])),
            qos=Qos(
                bandwidth_limit=int(human_to_bytes(module.params["bw_qos"])),
                iops_limit=int(human_to_real(module.params["iops_qos"])),
            ),
            subtype="regular",
        )
    elif not module.params["bw_qos"] and not module.params["iops_qos"]:
        vols = VolumePost(
            provisioned=int(human_to_bytes(module.params["size"])), subtype="regular"
        )
    elif not module.params["bw_qos"] and module.params["iops_qos"]:
        vols = VolumePost(
            provisioned=int(human_to_bytes(module.params["size"])),
            qos=Qos(iops_limit=int(human_to_real(module.params["iops_qos"]))),
            subtype="regular",
        )
    elif module.params["bw_qos"] and not module.params["iops_qos"]:
        vols = VolumePost(
            provisioned=int(human_to_bytes(module.params["size"])),
            qos=Qos(bandwidth_limit=int(human_to_bytes(module.params["bw_qos"]))),
            subtype="regular",
        )
    if not module.check_mode:
        if module.params["add_to_pgs"]:
            add_to_pgs = []
            for add_pg in module.params["add_to_pgs"]:
                add_to_pgs.append(ReferenceType(name=add_pg))
            if LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(
                api_version
            ) and module.params["context"] not in [
                "",
                list(array.get_arrays().items)[0].name,
            ]:
                module.fail_json(
                    msg="Cannot specify a remote fleet member and a protection group"
                )
            else:
                if "::" in module.params["name"]:
                    pod_name = "::".join(module.params["name"].split("::")[:-1])
                    for pgs in module.params["add_to_pgs"]:
                        if "::" not in pgs:
                            module.fail_json(msg="Specified PG is not a pod PG")
                        elif pg_exists(module, pgs, array) and pod_name != "::".join(
                            pgs.split("::")[:-1]
                        ):
                            module.fail_json(
                                msg="Protection Group {0} is not associated with pod {1}".format(
                                    pgs,
                                    pod_name,
                                )
                            )
                        elif not pg_exists(module, pgs, array):
                            module.fail_json(
                                msg="Protection Group {0} does not exist".format(pgs)
                            )
                    res = array.post_volumes(
                        names=names,
                        volume=vols,
                        with_default_protection=module.params[
                            "with_default_protection"
                        ],
                    )
                else:
                    res = array.post_volumes(
                        names=names,
                        volume=vols,
                        with_default_protection=module.params[
                            "with_default_protection"
                        ],
                        add_to_protection_groups=add_to_pgs,
                    )
        else:
            # Initialize res
            res = {}
            if (
                LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version)
                and module.params["context"]
                not in ["", list(array.get_arrays().items)[0].name]
                and module.params["with_default_protection"]
            ):
                module.fail_json(
                    msg="Cannot specify a remote fleet member and default protection group"
                )
            else:
                res = post_with_context(
                    array,
                    "post_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=names,
                    volume=vols,
                    with_default_protection=module.params["with_default_protection"],
                )
        check_response(
            res,
            module,
            f"Multi-Volume {module.params['name']}#{module.params['suffix']} creation",
        )
        if module.params["promotion_state"]:
            volume = VolumePatch(
                requested_promotion_state=module.params["promotion_state"]
            )
            prom_res = patch_with_context(
                array,
                "patch_volumes",
                CONTEXT_API_VERSION,
                module,
                names=names,
                volume=volume,
            )
            if prom_res.status_code != 200:
                patch_with_context(
                    array,
                    "patch_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=names,
                    volume=VolumePatch(destroyed=True),
                )
                array.delete_volumes(names=names)
                module.warn(
                    "Failed to set promotion status on volumes. Error: {0}".format(
                        prom_res.errors[0].message
                    )
                )
        if module.params["priority_operator"]:
            volume = VolumePatch(
                priority_adjustment=PriorityAdjustment(
                    priority_adjustment_operator=module.params["priority_operator"],
                    priority_adjustment_value=module.params["priority_value"],
                )
            )
            prio_res = patch_with_context(
                array,
                "patch_volumes",
                CONTEXT_API_VERSION,
                module,
                names=names,
                volume=volume,
            )
            if prio_res.status_code != 200:
                patch_with_context(
                    array,
                    "patch_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=names,
                    volume=VolumePatch(destroyed=True),
                )
                array.delete_volumes(names=names)
                module.fail_json(
                    msg="Failed to set DMM Priority Adjustment on volumes. Error: {0}".format(
                        prio_res.errors[0].message
                    )
                )
            prio_temp = list(prio_res.items)
        temp = list(res.items)
        for count, item in enumerate(temp):
            vol_name = item.name

            # Base volume info
            volfact[vol_name] = {
                "size": item.provisioned,
                "serial": item.serial,
                "created": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(item.created / 1000)
                ),
                "page83_naa": PURE_OUI + item.serial.lower(),
                "nvme_nguid": _create_nguid(item.serial.lower()),
            }

            # Optional fields
            if module.params["bw_qos"]:
                volfact[vol_name]["bandwidth_limit"] = item.qos.bandwidth_limit
            if module.params["iops_qos"]:
                volfact[vol_name]["iops_limit"] = item.qos.iops_limit
            if module.params["promotion_state"]:
                volfact[vol_name]["promotion_status"] = prio_temp[
                    count
                ].promotion_status
            if module.params["priority_operator"]:
                adj = prio_temp[count].priority_adjustment
                volfact[vol_name][
                    "priority_operator"
                ] = adj.priority_adjustment_operator
                volfact[vol_name]["priority_value"] = adj.priority_adjustment_value

    module.exit_json(changed=changed, volume=volfact)


def copy_from_volume(module, array):
    """Create Volume Clone"""
    changed = False
    tgt = get_target(module, array)
    api_version = array.get_rest_version()
    if tgt is None:
        changed = True
        if not module.check_mode:
            if LooseVersion(DEFAULT_API_VERSION) <= LooseVersion(api_version):
                if module.params["add_to_pgs"]:
                    add_to_pgs = []
                    for add_pg in module.params["add_to_pgs"]:
                        add_to_pgs.append(ReferenceType(name=add_pg))
                    res = post_with_context(
                        array,
                        "post_volumes",
                        CONTEXT_API_VERSION,
                        module,
                        with_default_protection=module.params[
                            "with_default_protection"
                        ],
                        add_to_protection_groups=add_to_pgs,
                        names=[module.params["target"]],
                        volume=VolumePost(source=Reference(name=module.params["name"])),
                    )
                else:
                    res = post_with_context(
                        array,
                        "post_volumes",
                        CONTEXT_API_VERSION,
                        module,
                        with_default_protection=module.params[
                            "with_default_protection"
                        ],
                        names=[module.params["target"]],
                        volume=VolumePost(source=Reference(name=module.params["name"])),
                    )

                check_response(
                    res,
                    module,
                    f"Failed to copy volume {module.params['name']} to {module.params['target']}",
                )
            else:
                res = array.post_volumes(
                    names=[module.params["target"]],
                    volume=VolumePost(source=Reference(name=module.params["name"])),
                )
                check_response(
                    res,
                    module,
                    f"Copy volume {module.params['name']} to volume {module.params['target']}",
                )
    elif tgt is not None and module.params["overwrite"]:
        changed = True
        if not module.check_mode:
            res = post_with_context(
                array,
                "post_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["target"]],
                volume=VolumePost(source=Reference(name=module.params["name"])),
                overwrite=module.params["overwrite"],
            )
            check_response(
                res,
                module,
                f"Copy volume {module.params['name']} to volume {module.params['target']}",
            )
    module.exit_json(
        changed=changed, volume=_volfact(module, array, module.params["target"])
    )


def update_volume(module, array):
    """Update Volume size and/or QoS"""
    changed = False
    api_version = array.get_rest_version()
    if (
        LooseVersion(api_version) >= LooseVersion(DEFAULT_API_VERSION)
        and module.params["pgroup"]
    ):
        module.fail_json(msg="For Purity//FA 6.3.4 or higher, use add_to_pgs parameter")
    elif (
        LooseVersion(api_version) <= LooseVersion(DEFAULT_API_VERSION)
        and module.params["add_to_pgs"]
    ):
        module.fail_json(msg="For Purity//FA 6.3.4 or lower, use pgroup parameter")
    vol = list(
        get_with_context(
            array,
            "get_volumes",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        ).items
    )[0]
    vol_qos = vol.qos
    if not hasattr(vol_qos, "bandwidth_limit"):
        vol.qos.bandwidth_limit = 549755813888
    if not hasattr(vol_qos, "iops_limit"):
        vol.qos.iops_limit = 100000000
    if module.params["size"]:
        if human_to_bytes(module.params["size"]) != vol.provisioned:
            if human_to_bytes(module.params["size"]) > vol.provisioned:
                changed = True
                if not module.check_mode:
                    res = patch_with_context(
                        array,
                        "patch_volumes",
                        CONTEXT_API_VERSION,
                        module,
                        names=[module.params["name"]],
                        volume=VolumePatch(
                            provisioned=int(human_to_bytes(module.params["size"]))
                        ),
                    )
                    check_response(
                        res, module, f"Volume {module.params['name']} resize"
                    )
    if module.params["bw_qos"]:
        # "0" (or an empty string) means "no limit", which the array
        # represents as the maximum bandwidth value.
        new_bw_limit = int(human_to_bytes(module.params["bw_qos"]))
        if new_bw_limit == 0:
            new_bw_limit = 549755813888
        if new_bw_limit != int(vol_qos.bandwidth_limit):
            changed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=VolumePatch(qos=Qos(bandwidth_limit=new_bw_limit)),
                )
                if new_bw_limit == 549755813888:
                    msg = f"Volume {module.params['name']} Bandwidth QoS removal"
                else:
                    msg = f"Volume {module.params['name']} Bandwidth QoS change"
                check_response(res, module, msg)
    if module.params["iops_qos"]:
        # "0" (or an empty string) means "no limit", which the array
        # represents as the maximum IOPs value.
        new_iops_limit = int(human_to_real(module.params["iops_qos"]))
        if new_iops_limit == 0:
            new_iops_limit = 100000000
        if new_iops_limit != int(vol_qos.iops_limit):
            changed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=VolumePatch(qos=Qos(iops_limit=new_iops_limit)),
                )
                if new_iops_limit == 100000000:
                    msg = f"Volume {module.params['name']} IOPs QoS removal"
                else:
                    msg = f"Volume {module.params['name']} IOPs QoS change"
                check_response(res, module, msg)
    if module.params["promotion_state"]:
        if module.params["promotion_state"] != vol.promotion_status:
            volume_patch = VolumePatch(
                requested_promotion_state=module.params["promotion_state"]
            )
            changed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=volume_patch,
                )
                check_response(
                    res,
                    module,
                    f"Failed to change promotion status for volume {module.params['name']}",
                )
    if module.params["priority_operator"]:
        change_prio = False
        if (
            module.params["priority_operator"]
            != vol.priority_adjustment.priority_adjustment_operator
        ):
            change_prio = True
            newop = module.params["priority_operator"]
        else:
            newop = vol.priority_adjustment.priority_adjustment_operator
        if (
            module.params["priority_value"]
            and module.params["priority_value"]
            != vol.priority_adjustment.priority_adjustment_value
        ):
            change_prio = True
            newval = module.params["priority_value"]
        elif (
            not module.params["priority_value"]
            and vol.priority_adjustment.priority_adjustment_value != 0
        ):
            change_prio = True
            newval = 0
        else:
            newval = vol.priority_adjustment.priority_adjustment_value
        volumepatch = VolumePatch(
            priority_adjustment=PriorityAdjustment(
                priority_adjustment_operator=newop,
                priority_adjustment_value=newval,
            )
        )
        if change_prio:
            changed = True
            if not module.check_mode:
                prio_res = patch_with_context(
                    array,
                    "patch_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=volumepatch,
                )
                check_response(
                    prio_res,
                    module,
                    f"Failed to change DMM Priority Adjustment for {module.params['name']}",
                )
    if module.params["add_to_pgs"]:
        pgs_now = []
        current_pgs = list(
            get_with_context(
                array,
                "get_protection_groups_volumes",
                CONTEXT_API_VERSION,
                module,
                member_names=[module.params["name"]],
            ).items
        )
        for current_pg in current_pgs:
            pgs_now.append(current_pg.group.name)
        new_pgs = list(filter(lambda x: x not in pgs_now, module.params["add_to_pgs"]))
        if new_pgs:
            changed = True
            res = post_with_context(
                array,
                "post_volumes_protection_groups",
                CONTEXT_API_VERSION,
                module,
                member_names=[module.params["name"]],
                group_names=new_pgs,
            )
            check_response(
                res,
                module,
                f"Failed to add volume {module.params['name']} to new PGs {new_pgs}",
            )
    module.exit_json(
        changed=changed, volume=_volfact(module, array, module.params["name"])
    )


def rename_volume(module, array, source_exists=True):
    """Rename volume within a container, ie pod, vgroup or local array"""
    changed = False
    pod_name = ""
    vgroup_name = ""
    target_exists = False
    api_version = array.get_rest_version()
    if "::" in module.params["name"]:
        pod_name = "::".join(module.params["name"].split("::")[:-1])
        target_name = pod_name + "::" + module.params["rename"]
    elif "/" in module.params["name"]:
        vgroup_name = module.params["name"].split("/")[0]
        target_name = vgroup_name + "/" + module.params["rename"]
    else:
        target_name = module.params["rename"]
    target_exists = bool(
        get_with_context(
            array, "get_volumes", CONTEXT_API_VERSION, module, names=[target_name]
        ).status_code
        == 200
    )
    if target_exists:
        if source_exists:
            module.fail_json(
                msg="Target volume {0} already exists.".format(target_name)
            )
        # Source is gone and the target is there: the rename has already
        # been done, so this is a no-op.
        module.exit_json(changed=False, volume=_volfact(module, array, target_name))
    elif not source_exists:
        module.fail_json(
            msg="Volume {0} does not exist - rename failed".format(
                module.params["name"]
            )
        )
    else:
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume=VolumePatch(name=module.params["rename"]),
            )
            check_response(
                res,
                module,
                f"Rename volume {module.params['name']} to {module.params['rename']}",
            )

    module.exit_json(changed=changed, volume=_volfact(module, array, target_name))


def move_volume(module, array):
    """Move volume between pods, vgroups or local array"""
    api_version = array.get_rest_version()
    changed = vgroup_exists = target_exists = pod_exists = False
    pod_name = ""
    vgroup_name = ""
    volume_name = module.params["name"]
    if "::" in module.params["name"]:
        volume_name = module.params["name"].rsplit("::", 1)[1]
        pod_name = "::".join(module.params["name"].split("::")[:-1])
    if "/" in module.params["name"]:
        volume_name = module.params["name"].split("/")[1]
        vgroup_name = module.params["name"].split("/")[0]
    if module.params["move"] == "local":
        if "::" not in module.params["name"]:
            if "/" not in module.params["name"]:
                module.fail_json(
                    msg="Source and destination [local] cannot be the same."
                )
        target_exists = bool(
            get_with_context(
                array, "get_volumes", CONTEXT_API_VERSION, module, names=[volume_name]
            ).status_code
            == 200
        )
        if target_exists:
            module.fail_json(msg="Target volume {0} already exists".format(volume_name))
    else:
        pod_exists = bool(
            get_with_context(
                array,
                "get_pods",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["move"]],
            ).status_code
            == 200
        )
        if pod_exists:
            pod = list(
                get_with_context(
                    array,
                    "get_pods",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["move"]],
                ).items
            )[0]
            if pod.array_count > 1:
                module.fail_json(msg="Volume cannot be moved into a stretched pod")
            if pod.link_target_count != 0:
                module.fail_json(msg="Volume cannot be moved into a linked source pod")
            if pod.promotion_status == "demoted":
                module.fail_json(msg="Volume cannot be moved into a demoted pod")
            target_exists = bool(
                get_with_context(
                    array,
                    "get_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["move"] + "::" + volume_name],
                ).status_code
                == 200
            )
        vgroup_exists = bool(
            get_with_context(
                array,
                "get_volume_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["move"]],
            ).status_code
            == 200
        )
        if vgroup_exists:
            target_exists = bool(
                get_with_context(
                    array,
                    "get_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["move"] + "/" + volume_name],
                ).status_code
                == 200
            )
        if target_exists:
            module.fail_json(msg="Volume of same name already exists in move location")
        if pod_exists and vgroup_exists:
            module.fail_json(
                msg="Move location {0} matches both a pod and a vgroup. Please rename one of these.".format(
                    module.params["move"]
                )
            )
        if not pod_exists and not vgroup_exists:
            module.fail_json(
                msg="Move location {0} does not exist.".format(module.params["move"])
            )
        if "::" in module.params["name"] and not vgroup_exists:
            pod = list(
                get_with_context(
                    array, "get_pods", CONTEXT_API_VERSION, module, names=[pod_name]
                ).items
            )[0]
            if pod.array_count > 1:
                module.fail_json(msg="Volume cannot be moved out of a stretched pod")
            if pod.link_target_count != 0:
                module.fail_json(
                    msg="Volume cannot be moved out of a linked source pod"
                )
            if pod.promotion_status == "demoted":
                module.fail_json(msg="Volume cannot be moved out of a demoted pod")
        if "/" in module.params["name"]:
            if (
                vgroup_name == module.params["move"]
                or pod_name == module.params["move"]
            ):
                module.fail_json(msg="Source and destination cannot be the same")
    if get_endpoint(module, module.params["move"], array):
        module.fail_json(
            msg="Target volume {0} is a protocol-endpoinnt".format(
                module.params["move"]
            )
        )
    changed = True
    if not module.check_mode:
        if pod_exists:
            res = patch_with_context(
                array,
                "patch_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume=VolumePatch(pod=Reference(name=module.params["move"])),
            )
        elif vgroup_exists:
            res = patch_with_context(
                array,
                "patch_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume=VolumePatch(volume_group=Reference(name=module.params["move"])),
            )
        elif module.params["move"] == "local":
            if "/" in module.params["name"]:
                res = patch_with_context(
                    array,
                    "patch_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=VolumePatch(volume_group=Reference(name="")),
                )
            else:
                res = patch_with_context(
                    array,
                    "patch_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume=VolumePatch(pod=Reference(name="")),
                )
        check_response(
            res,
            module,
            f"Move of volume {module.params['name']} to {module.params['move']}",
        )
        if res.status_code == 200:
            volume_name = list(res.items)[0].name
    else:
        volume_name = ""
    module.exit_json(changed=changed, volume=_volfact(module, array, volume_name))


def delete_volume(module, array):
    """Delete Volume"""
    api_version = array.get_rest_version()
    changed = False
    if module.params["add_to_pgs"]:
        pgs_now = []
        current_pgs = list(
            get_with_context(
                array,
                "get_protection_groups_volumes",
                CONTEXT_API_VERSION,
                module,
                member_names=[module.params["name"]],
            ).items
        )
        for current_pg in current_pgs:
            pgs_now.append(current_pg.group.name)
        old_pgs = list(filter(lambda x: x in module.params["add_to_pgs"], pgs_now))
        if old_pgs:
            changed = True
            if not module.check_mode:
                res = delete_with_context(
                    array,
                    "delete_volumes_protection_groups",
                    CONTEXT_API_VERSION,
                    module,
                    member_names=[module.params["name"]],
                    group_names=old_pgs,
                )
                check_response(
                    res,
                    module,
                    f"Failed to remove volume {module.params['name']} from PGs {old_pgs}",
                )
    else:
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume=VolumePatch(destroyed=True),
            )
            if res.status_code == 200 and module.params["eradicate"]:
                res = delete_with_context(
                    array,
                    "delete_volumes",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                )
                check_response(res, module, f"Eradicate volume {module.params['name']}")
                module.exit_json(
                    changed=changed,
                )
            elif res.status_code != 200:
                check_response(res, module, f"Delete volume {module.params['name']}")
    module.exit_json(
        changed=changed, volume=_volfact(module, array, module.params["name"])
    )


def eradicate_volume(module, array):
    """Eradicate Deleted Volume"""
    api_version = array.get_rest_version()
    changed = False
    volfact = _volfact(module, array, module.params["name"])
    if module.params["eradicate"]:
        changed = True
        volfact = []
        if not module.check_mode:
            res = delete_with_context(
                array,
                "delete_volumes",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
            )
            check_response(
                res, module, f"Eradication of volume {module.params['name']}"
            )
    module.exit_json(changed=changed, volume=volfact)


def recover_volume(module, array):
    """Recover Deleted Volume"""
    api_version = array.get_rest_version()
    changed = True
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_volumes",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            volume=VolumePatch(destroyed=False),
        )
        check_response(res, module, f"Recovery of volume {module.params['name']}")
    module.exit_json(
        changed=changed, volume=_volfact(module, array, module.params["name"])
    )


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            target=dict(type="str"),
            move=dict(type="str"),
            rename=dict(type="str"),
            overwrite=dict(type="bool", default=False),
            eradicate=dict(type="bool", default=False),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            bw_qos=dict(type="str", aliases=["qos"]),
            iops_qos=dict(type="str"),
            pgroup=dict(type="str"),
            count=dict(type="int"),
            start=dict(type="int", default=0),
            digits=dict(type="int", default=1),
            suffix=dict(type="str", default=""),
            priority_operator=dict(type="str", choices=["+", "-", "="]),
            priority_value=dict(type="int", choices=[-10, 0, 10]),
            size=dict(type="str"),
            with_default_protection=dict(type="bool", default=True),
            add_to_pgs=dict(type="list", elements="str"),
            promotion_state=dict(type="str", choices=["promoted", "demoted"]),
            context=dict(type="str", default=""),
        )
    )

    mutually_exclusive = [
        ["size", "target"],
        ["move", "rename", "target", "eradicate"],
        ["rename", "move", "target", "eradicate"],
    ]
    required_together = [["priority_operator", "priority_value"]]

    module = AnsibleModule(
        argument_spec,
        mutually_exclusive=mutually_exclusive,
        required_together=required_together,
        supports_check_mode=True,
    )

    size = module.params["size"]
    bw_qos_size = False
    iops_qos_size = False
    state = module.params["state"]
    destroyed = False
    array = get_array(module)
    volume = get_volume(module, array)
    api_version = array.get_rest_version()
    endpoint = get_endpoint(module, module.params["name"], array)
    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")
    if (
        LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version)
        and not module.params["context"]
    ):
        # If no context is provided set the context to the local array name
        fleet_res = array.get_fleets()
        if fleet_res.status_code == 200 and list(fleet_res.items):
            module.params["context"] = list(array.get_arrays().items)[0].name

    if module.params["bw_qos"]:
        bw_qos = int(human_to_bytes(module.params["bw_qos"]))
        if bw_qos in range(1048576, 549755813888) or bw_qos == 0:
            bw_qos_size = True
        else:
            module.fail_json(msg="Bandwidth QoS value out of range.")
    if module.params["iops_qos"]:
        iops_qos = int(human_to_real(module.params["iops_qos"]))
        if iops_qos in range(100, 100000000) or iops_qos == 0:
            iops_qos_size = True
        else:
            module.fail_json(msg="IOPs QoS value out of range.")

    if endpoint:
        module.fail_json(
            msg="Volume {0} is an endpoint. Use purefa_endpoint module.".format(
                module.params["name"]
            )
        )

    if module.params["pgroup"]:
        pattern = re.compile("^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
        if ":" in module.params["pgroup"]:
            if "::" in module.params["pgroup"]:
                pgname = module.params["pgroup"].split("::")[-1]
            else:
                pgname = module.params["pgroup"].split(":")[1]
            if not pattern.match(pgname):
                module.fail_json(
                    msg="Protection Group name {0} does not conform to naming convention".format(
                        pgname
                    )
                )
        else:
            if not pattern.match(module.params["pgroup"]):
                module.fail_json(
                    msg="Protection Group name {0} does not conform to naming convention".format(
                        module.params["pgroup"]
                    )
                )
        pgroup = get_pgroup(module, array)
        xpgroup = get_pending_pgroup(module, array)
        if "::" in module.params["pgroup"]:
            if not get_pod(module, array):
                module.fail_json(
                    msg="Pod {0} does not exist.".format(
                        "::".join(module.params["pgroup"].split("::")[:-1])
                    )
                )
        if not pgroup:
            if xpgroup:
                module.fail_json(
                    msg="Protection Group {0} is currently deleted. Please restore to use.".format(
                        module.params["pgroup"]
                    )
                )
            else:
                module.fail_json(
                    msg="Protection Group {0} does not exist.".format(
                        module.params["pgroup"]
                    )
                )

    if not volume:
        destroyed = get_destroyed_volume(module, array)
    target = get_target(module, array)
    snapshot = None
    if module.params["target"] and not volume and not destroyed:
        # The copy source is not a volume, so it may be a volume snapshot
        # (including a protection group snapshot inside a pod).
        snapshot = get_source_snapshot(module, array)
    if module.params["count"]:
        if module.params["digits"] and module.params["digits"] not in range(1, 10):
            module.fail_json(msg="'digits' must be in the range of 1 to 10")
        if module.params["start"] < 0:
            module.fail_json(msg="'start' must be a positive number")
        volume = get_multi_volumes(module, array)
        if state == "present" and not volume and size:
            create_multi_volume(module, array)
        elif state == "present" and not volume and not size:
            module.fail_json(msg="Size must be specified to create a new volume")
        elif state == "absent" and not volume:
            module.exit_json(changed=False)
        else:
            module.warn("Method not yet supported for multi-volume")
    else:
        if state == "present" and not volume and not destroyed and size:
            if LooseVersion(DEFAULT_API_VERSION) <= LooseVersion(api_version):
                create_multi_volume(module, array, True)
            else:
                create_volume(module, array)
        elif (
            state == "present"
            and volume
            and not module.params["rename"]
            and not module.params["move"]
            and not module.params["target"]
        ):
            # Covers size/QoS/priority/promotion/add_to_pgs updates as well
            # as a bare "present" on an existing volume (no-op).
            update_volume(module, array)
        elif state == "present" and not volume and module.params["move"]:
            module.fail_json(
                msg="Volume {0} cannot be moved - does not exist (maybe deleted)".format(
                    module.params["name"]
                )
            )
        elif state == "present" and volume and module.params["move"]:
            move_volume(module, array)
        elif state == "present" and module.params["rename"]:
            # Also handles a repeated rename (source gone, target present)
            # by exiting with changed=False.
            rename_volume(module, array, source_exists=bool(volume))
        elif (
            state == "present"
            and destroyed
            and not module.params["move"]
            and not module.params["rename"]
        ):
            recover_volume(module, array)
        elif state == "present" and destroyed and module.params["move"]:
            module.fail_json(
                msg="Volume {0} exists, but in destroyed state".format(
                    module.params["name"]
                )
            )
        elif state == "present" and snapshot and module.params["target"]:
            copy_from_volume(module, array)
        elif state == "present" and volume and module.params["target"]:
            copy_from_volume(module, array)
        elif state == "absent" and volume:
            delete_volume(module, array)
        elif state == "absent" and destroyed:
            eradicate_volume(module, array)
        elif state == "present":
            if not volume and not size:
                module.fail_json(msg="Size must be specified to create a new volume")
        elif state == "absent" and not volume:
            module.exit_json(changed=False, volume=[])

    module.exit_json(changed=False, volume=[])


if __name__ == "__main__":
    main()
