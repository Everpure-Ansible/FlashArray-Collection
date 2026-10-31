#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2017, Simon Dodsley (simon@everpuredata.com)
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
module: purefa_vg
version_added: '1.0.0'
short_description: Manage volume groups on Everpure FlashArrays
description:
- Create, delete or modify volume groups on Everpure FlashArrays.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the volume group.
    - Multi-volume-group support available from Purity//FA 6.0.0
      B(***NOTE***) Manual deletion or eradication of individual volume groups created
      using multi-volume-group will cause idempotency to fail
    - Multi-volume-group support only exists for volume group creation
    type: str
    required: true
  state:
    description:
    - Define whether the volume group should exist or not.
    type: str
    default: present
    choices: [ absent, present ]
  eradicate:
    description:
    - Define whether to eradicate the volume group on delete and leave in trash.
    type : bool
    default: false
  bw_qos:
    description:
    - Bandwidth limit for vgroup in M or G units.
      M will set MB/s
      G will set GB/s
      To clear an existing QoS setting use 0 (zero)
    type: str
  iops_qos:
    description:
    - IOPs limit for vgroup - use value or K or M
      K will mean 1000
      M will mean 1000000
      To clear an existing IOPs setting use 0 (zero)
    type: str
  count:
    description:
    - Number of volume groups to be created in a multiple volume group creation
    - Only supported from Purity//FA v6.0.0 and higher
    type: int
  start:
    description:
    - Number at which to start the multiple volume group creation index
    - Only supported from Purity//FA v6.0.0 and higher
    type: int
    default: 0
  digits:
    description:
    - Number of digits to use for multiple volume group count. This
      will pad the index number with zeros where necessary
    - Only supported from Purity//FA v6.0.0 and higher
    - Range is between 1 and 10
    type: int
    default: 1
  suffix:
    description:
    - Suffix string, if required, for multiple volume group create
    - Volume group names will be formed as I(<name>#I<suffix>), where
      I(#) is a placeholder for the volume index
      See associated descriptions
    - Only supported from Purity//FA v6.0.0 and higher
    type: str
    default: ""
  priority_operator:
    description:
    - DMM Priority Adjustment operator
    - Only applied when specified; an existing adjustment is left
      untouched by QoS-only or bare I(state=present) calls.
    - Must be specified together with I(priority_value).
    type: str
    choices: [ +, '-' ]
    version_added: '1.13.0'
  priority_value:
    description:
    - DMM Priority Adjustment value
    - Only applied when specified, together with I(priority_operator).
    type: int
    choices: [ 0, 10 ]
    version_added: '1.13.0'
  rename:
    description:
    - Value to rename the specified volume group to
    type: str
    version_added: '1.22.0'
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
- name: Create new volume group
  everpure.flasharray.purefa_vg:
    name: foo
    bw_qos: 50M
    iops_qos: 100
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create 10 volume groups of pattern foo#bar with QoS
  everpure.flasharray.purefa_vg:
    name: foo
    suffix: bar
    count: 10
    start: 10
    digits: 3
    bw_qos: 50M
    iops_qos: 100
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Update volume group QoS limits
  everpure.flasharray.purefa_vg:
    name: foo
    bw_qos: 0
    iops_qos: 5555
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Update volume group DMM Priority Adjustment (Purity//FA 6.1.2+)
  everpure.flasharray.purefa_vg:
    name: foo
    priority_operator: '-'
    priority_value: 10
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Destroy volume group
  everpure.flasharray.purefa_vg:
    name: foo
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Recover deleted volume group - no changes are made to the volume group on recovery
  everpure.flasharray.purefa_vg:
    name: foo
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Destroy and Eradicate volume group
  everpure.flasharray.purefa_vg:
    name: foo
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Rename volume group foo to bar
  everpure.flasharray.purefa_vg:
    name: foo
    rename: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        VolumeGroupPost,
        VolumeGroupPatch,
        Qos,
        PriorityAdjustment,
    )
except ImportError:
    HAS_PURESTORAGE = False

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

PRIORITY_API_VERSION = "2.11"
CONTEXT_API_VERSION = "2.38"
MIN_BWS = 1048576
MIN_IOPS = 100
MAX_BWS = 549755813888
MAX_IOPS = 100000000


def rename_exists(module, array):
    """Determine if rename target already exists"""
    res = get_with_context(
        array,
        "get_volume_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["rename"]],
    )
    return bool(res.status_code == 200)


def get_multi_vgroups(module, array):
    """Return True is all volume groups exist or None"""
    names = []
    for vg_num in range(
        module.params["start"], module.params["count"] + module.params["start"]
    ):
        names.append(
            module.params["name"]
            + str(vg_num).zfill(module.params["digits"])
            + module.params["suffix"]
        )
    res = get_with_context(
        array,
        "get_volume_groups",
        CONTEXT_API_VERSION,
        module,
        names=names,
        destroyed=False,
    )
    return bool(res.status_code == 200)


def get_pending_vgroup(module, array):
    """Get Deleted Volume Group"""
    res = get_with_context(
        array,
        "get_volume_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        destroyed=True,
    )
    return bool(res.status_code == 200)


def get_vgroup(module, array):
    """Get Volume Group"""
    res = get_with_context(
        array,
        "get_volume_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["name"]],
        destroyed=False,
    )
    return bool(res.status_code == 200)


def rename_vgroup(module, array):
    changed = False
    if not rename_exists(module, array):
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_volume_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume_group=VolumeGroupPatch(name=module.params["rename"]),
            )
            check_response(res, module, f"Rename to {module.params['rename']}")
    module.exit_json(changed=changed)


def make_vgroup(module, array):
    """Create Volume Group"""
    api_version = array.get_rest_version()
    changed = True
    if module.params["bw_qos"] and not module.params["iops_qos"]:
        if int(human_to_bytes(module.params["bw_qos"])) in range(MIN_BWS, MAX_BWS):
            changed = True
            if not module.check_mode:
                res = post_with_context(
                    array,
                    "post_volume_groups",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume_group=VolumeGroupPost(
                        qos=Qos(
                            bandwidth_limit=int(human_to_bytes(module.params["bw_qos"]))
                        )
                    ),
                )
                check_response(res, module, f"Vgroup {module.params['name']} creation")
        else:
            module.fail_json(
                msg="Bandwidth QoS value {0} out of range.".format(
                    module.params["bw_qos"]
                )
            )
    elif module.params["iops_qos"] and not module.params["bw_qos"]:
        if int(human_to_real(module.params["iops_qos"])) in range(MIN_IOPS, MAX_IOPS):
            changed = True
            if not module.check_mode:
                res = post_with_context(
                    array,
                    "post_volume_groups",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume_group=VolumeGroupPost(
                        qos=Qos(
                            iops_limit=int(human_to_real(module.params["iops_qos"]))
                        )
                    ),
                )
                check_response(res, module, f"Vgroup {module.params['name']} creation")
        else:
            module.fail_json(
                msg="IOPs QoS value {0} out of range.".format(module.params["iops_qos"])
            )
    elif module.params["iops_qos"] and module.params["bw_qos"]:
        bw_qos_size = int(human_to_bytes(module.params["bw_qos"]))
        if int(human_to_real(module.params["iops_qos"])) in range(
            MIN_IOPS, MAX_IOPS
        ) and bw_qos_size in range(MIN_BWS, MAX_BWS):
            changed = True
            if not module.check_mode:
                res = post_with_context(
                    array,
                    "post_volume_groups",
                    CONTEXT_API_VERSION,
                    module,
                    names=[module.params["name"]],
                    volume_group=VolumeGroupPost(
                        qos=Qos(
                            iops_limit=int(human_to_real(module.params["iops_qos"])),
                            bandwidth_limit=int(
                                human_to_bytes(module.params["bw_qos"])
                            ),
                        )
                    ),
                )
                check_response(res, module, f"Vgroup {module.params['name']} creation")
        else:
            module.fail_json(msg="IOPs or Bandwidth QoS value out of range.")
    else:
        changed = True
        if not module.check_mode:
            res = post_with_context(
                array,
                "post_volume_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume_group=VolumeGroupPost(),
            )
            check_response(res, module, f"Vgroup {module.params['name']} creation")
    if (
        LooseVersion(PRIORITY_API_VERSION) <= LooseVersion(api_version)
        and module.params["priority_operator"] is not None
        and module.params["priority_value"] is not None
    ):
        volume_group = VolumeGroupPatch(
            priority_adjustment=PriorityAdjustment(
                priority_adjustment_operator=module.params["priority_operator"],
                priority_adjustment_value=module.params["priority_value"],
            ),
        )
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_volume_groups",
                CONTEXT_API_VERSION,
                module,
                names=[module.params["name"]],
                volume_group=volume_group,
            )
            check_response(
                res,
                module,
                f"Failed to set priority adjustment for volume group {module.params['name']}",
            )

    module.exit_json(changed=changed)


def make_multi_vgroups(module, array):
    """Create multiple Volume Groups"""
    api_version = array.get_rest_version()
    changed = True
    bw_qos_size = iops_qos_size = 0
    names = []
    for vg_num in range(
        module.params["start"], module.params["count"] + module.params["start"]
    ):
        names.append(
            module.params["name"]
            + str(vg_num).zfill(module.params["digits"])
            + module.params["suffix"]
        )
    if module.params["bw_qos"]:
        bw_qos = int(human_to_bytes(module.params["bw_qos"]))
        if bw_qos in range(MIN_BWS, MAX_BWS):
            bw_qos_size = bw_qos
        else:
            module.fail_json(msg="Bandwidth QoS value out of range.")
    if module.params["iops_qos"]:
        iops_qos = int(human_to_real(module.params["iops_qos"]))
        if iops_qos in range(MIN_IOPS, MAX_IOPS):
            iops_qos_size = iops_qos
        else:
            module.fail_json(msg="IOPs QoS value out of range.")
    if bw_qos_size != 0 and iops_qos_size != 0:
        volume_group = VolumeGroupPost(
            qos=Qos(bandwidth_limit=bw_qos_size, iops_limit=iops_qos_size)
        )
    elif bw_qos_size == 0 and iops_qos_size == 0:
        volume_group = VolumeGroupPost()
    elif bw_qos_size == 0 and iops_qos_size != 0:
        volume_group = VolumeGroupPost(qos=Qos(iops_limit=iops_qos_size))
    elif bw_qos_size != 0 and iops_qos_size == 0:
        volume_group = VolumeGroupPost(qos=Qos(bandwidth_limit=bw_qos_size))
    if not module.check_mode:
        res = post_with_context(
            array,
            "post_volume_groups",
            CONTEXT_API_VERSION,
            module,
            names=names,
            volume_group=volume_group,
        )
        check_response(
            res,
            module,
            f"Multi-Vgroup {module.params['name']}#{module.params['suffix']} creation",
        )
        if (
            LooseVersion(PRIORITY_API_VERSION) <= LooseVersion(api_version)
            and module.params["priority_operator"] is not None
            and module.params["priority_value"] is not None
        ):
            volume_group = VolumeGroupPatch(
                priority_adjustment=PriorityAdjustment(
                    priority_adjustment_operator=module.params["priority_operator"],
                    priority_adjustment_value=module.params["priority_value"],
                ),
            )
            res = patch_with_context(
                array,
                "patch_volume_groups",
                CONTEXT_API_VERSION,
                module,
                names=names,
                volume_group=volume_group,
            )
            check_response(
                res,
                module,
                f"Failed to set priority adjustments for multi-vgroup {module.params['name']}#{module.params['suffix']}",
            )
    module.exit_json(changed=changed)


def update_vgroup(module, array):
    """Update Volume Group safely, only marking changed if needed"""
    api_version = array.get_rest_version()
    changed = False

    # Fetch the volume group
    vg_all = list(
        get_with_context(
            array,
            "get_volume_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        ).items
    )[0]

    kwargs = {"names": [module.params["name"]]}
    if LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version):
        kwargs["context_names"] = [module.params["context"]]

    # ---------- Priority Adjustment ----------
    if LooseVersion(PRIORITY_API_VERSION) <= LooseVersion(api_version):
        vg_prio = vg_all.priority_adjustment
        new_operator = vg_prio.priority_adjustment_operator
        new_value = vg_prio.priority_adjustment_value

        if (
            module.params.get("priority_operator") is not None
            and vg_prio.priority_adjustment_operator
            != module.params["priority_operator"]
        ):
            new_operator = module.params["priority_operator"]
            changed = True

        if (
            module.params.get("priority_value") is not None
            and vg_prio.priority_adjustment_value != module.params["priority_value"]
        ):
            new_value = module.params["priority_value"]
            changed = True

        if changed and not module.check_mode:
            volume_group = VolumeGroupPatch(
                priority_adjustment=PriorityAdjustment(
                    priority_adjustment_operator=new_operator,
                    priority_adjustment_value=new_value,
                )
            )
            res = array.patch_volume_groups(**kwargs, volume_group=volume_group)
            check_response(
                res,
                module,
                f"Failed to change DMM Priority for volume group {module.params['name']}",
            )

    # ---------- QoS ----------
    vg_qos = vg_all.qos
    bw_limit = getattr(vg_qos, "bandwidth_limit", MAX_BWS)
    iops_limit = getattr(vg_qos, "iops_limit", MAX_IOPS)

    if module.params.get("bw_qos") is not None:
        bw_input = module.params["bw_qos"]
        # If user wants to "disable" QoS, set to MAX_BWS
        if bw_input == "0":
            bw_val = MAX_BWS
        else:
            bw_val = int(human_to_bytes(bw_input))

        # Only patch if different
        if bw_val != getattr(vg_qos, "bandwidth_limit", MAX_BWS):
            changed = True
            if not module.check_mode:
                res = array.patch_volume_groups(
                    **kwargs,
                    volume_group=VolumeGroupPatch(qos=Qos(bandwidth_limit=bw_val)),
                )
                check_response(
                    res,
                    module,
                    f"Vgroup {module.params['name']} Bandwidth QoS update",
                )

    if module.params.get("iops_qos") is not None:
        iops_input = module.params["iops_qos"]
        if iops_input == "0":
            iops_val = MAX_IOPS  # unlimited
        else:
            iops_val = int(human_to_real(iops_input))

        if iops_val != getattr(vg_qos, "iops_limit", MAX_IOPS):
            changed = True
            if not module.check_mode:
                res = array.patch_volume_groups(
                    **kwargs,
                    volume_group=VolumeGroupPatch(qos=Qos(iops_limit=iops_val)),
                )
                check_response(
                    res,
                    module,
                    f"Vgroup {module.params['name']} IOPS QoS update",
                )
    module.exit_json(changed=changed)


def recover_vgroup(module, array):
    """Recover Volume Group"""
    changed = True
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_volume_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            volume_group=VolumeGroupPatch(destroyed=False),
        )
        check_response(res, module, f"Recovery of volume group {module.params['name']}")

    module.exit_json(changed=changed)


def eradicate_vgroup(module, array):
    """Eradicate Volume Group"""
    changed = True
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_volume_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        )
        check_response(res, module, f"Eradicating vgroup {module.params['name']}")
    module.exit_json(changed=changed)


def delete_vgroup(module, array):
    """Delete Volume Group"""
    changed = True
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_volume_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
            volume_group=VolumeGroupPatch(destroyed=True),
        )
        check_response(res, module, f"Deletion of volume group {module.params['name']}")
    if module.params["eradicate"]:
        eradicate_vgroup(module, array)

    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            bw_qos=dict(type="str"),
            iops_qos=dict(type="str"),
            count=dict(type="int"),
            start=dict(type="int", default=0),
            digits=dict(type="int", default=1),
            suffix=dict(type="str", default=""),
            priority_operator=dict(type="str", choices=["+", "-"]),
            priority_value=dict(type="int", choices=[0, 10]),
            eradicate=dict(type="bool", default=False),
            rename=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    required_together = [["priority_operator", "priority_value"]]

    module = AnsibleModule(
        argument_spec,
        required_together=required_together,
        supports_check_mode=True,
    )

    if not HAS_PURESTORAGE:
        module.fail_json(
            msg="py-pure-client sdk is required to support 'count' parameter"
        )
    state = module.params["state"]
    array = get_array(module)
    api_version = array.get_rest_version()
    if (
        LooseVersion(CONTEXT_API_VERSION) <= LooseVersion(api_version)
        and not module.params["context"]
    ):
        # If no context is provided set the context to the local array name
        fleet_res = array.get_fleets()
        if fleet_res.status_code == 200 and list(fleet_res.items):
            module.params["context"] = list(array.get_arrays().items)[0].name
    vgroup = get_vgroup(module, array)
    xvgroup = get_pending_vgroup(module, array)

    if module.params["count"]:
        if module.params["digits"] and module.params["digits"] not in range(1, 10):
            module.fail_json(msg="'digits' must be in the range of 1 to 10")
        if module.params["start"] < 0:
            module.fail_json(msg="'start' must be a positive number")
        vgroup = get_multi_vgroups(module, array)
        if state == "present" and not vgroup:
            make_multi_vgroups(module, array)
        elif state == "absent" and not vgroup:
            module.exit_json(changed=False)
        else:
            module.warn("Method not yet supported for multi-vgroup")
    else:
        if xvgroup and state == "present":
            recover_vgroup(module, array)
        elif vgroup and state == "absent":
            delete_vgroup(module, array)
        elif xvgroup and state == "absent" and module.params["eradicate"]:
            eradicate_vgroup(module, array)
        elif (
            not vgroup
            and not xvgroup
            and state == "present"
            and module.params["rename"]
        ):
            if rename_exists(module, array):
                # Source is gone and the rename target exists: the rename
                # has already been done, so this is a no-op.
                module.exit_json(changed=False)
            module.fail_json(
                msg="Volume group {0} does not exist - rename failed".format(
                    module.params["name"]
                )
            )
        elif not vgroup and not xvgroup and state == "present":
            make_vgroup(module, array)
        elif state == "present" and vgroup and module.params["rename"] and not xvgroup:
            rename_vgroup(module, array)
        elif vgroup and state == "present":
            update_vgroup(module, array)
        elif vgroup is None and state == "absent":
            module.exit_json(changed=False)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
