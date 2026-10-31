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
module: purefa_pod
short_description:  Manage AC pods in Everpure FlashArrays
version_added: '1.0.0'
description:
- Manage AC pods in a Everpure FlashArray.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the pod.
    - To place a pod inside a realm either set the I(realm) parameter, or
      provide the fully-qualified C(realm::pod) name here (for example
      C(myrealm::mypod)). If I(realm) is set, do not also use the C(::)
      form in this parameter.
    type: str
    required: true
  realm:
    description:
    - Name of the realm the pod belongs to.
    - When set, the pod is created (or managed) as C(realm::pod). This is a
      convenience for the C(realm::pod) naming convention and is mutually
      exclusive with providing C(::) directly in I(name).
    - Requires Purity//FA 6.6.11, or higher (REST 2.36).
    type: str
    version_added: '1.44.0'
  stretch:
    description:
    - The name of the array to stretch to/unstretch from. Must be synchromously replicated.
    - To unstretch an array use state I(absent)
    - You can only specify a remote array, ie you cannot unstretch a pod from the
      current array and then restretch back to the current array.
    - To restretch a pod you must perform this from the remaining array the pod
      resides on.
    type: str
  failover:
    description:
    - The name of the array given priority to stay online if arrays loose
      contact with each other.
    - Options are either array in the cluster, or I(auto)
    type: list
    elements: str
  state:
    description:
    - Define whether the pod should exist or not.
    default: present
    choices: [ absent, present ]
    type: str
  eradicate:
    description:
    - Define whether to eradicate the pod on delete or leave in trash.
    type: bool
    default: false
  target:
    description:
    - Name of clone target pod.
    type: str
  mediator:
    description:
    - Name of the mediator to use for a pod
    type: str
    default: purestorage
  promote:
    description:
      - Promote/demote any pod not in a stretched relationship. .
      - Demoting a pod will render it read-only.
    required: false
    type: bool
  quiesce:
    description:
      - Quiesce/Skip quiesce when I(promote) is false and demoting an ActiveDR pod.
      - Quiesce will ensure all local data has been replicated before demotion.
      - Skipping quiesce looses all pending data to be replicated to the remote pod.
      - Can only demote the pod if it is in a Acrive DR replica link relationship.
      - This will default to True
    required: false
    type: bool
  undo:
    description:
      - Use the I(undo-remote) pod when I(promote) is true and promoting an ActiveDR pod.
      - This will default to True
    required: false
    type: bool
  quota:
    description:
      - Logical quota limit of the pod in K, M, G, T or P units, or bytes.
      - Set to C(0) or C("") to remove an existing quota limit.
    type: str
    version_added: '1.18.0'
  ignore_usage:
    description:
    -  Flag used to override checks for quota management
       operations.
    - If set to true, pod usage is not checked against the
      quota_limits that are set.
    - If set to false, the actual logical bytes in use are prevented
      from exceeding the limits set on the pod.
    - Client operations might be impacted.
    - If the limit exceeds the quota, the operation is not allowed.
    default: false
    type: bool
    version_added: '1.18.0'
  throttle:
    description:
    - Allows pod creation to fail if array health is not optimal
    type: bool
    default: false
    version_added: '1.29.0'
  delete_contents:
    description:
    - This enables you to eradicate pods with contents.
    type: bool
    default: False
    version_added: '1.29.0'
  context:
    description:
    - Name of fleet member on which to perform the operation.
    - This requires the array receiving the request is a member of a fleet
      and the context name to be a member of the same fleet.
    type: str
    default: ""
    version_added: '1.33.0'
  with_default_protection:
    description:
    - Whether to keep the default container protection for the pod
    - Only applicable for first creation of a pod
    type: bool
    default: true
    version_added: '1.37.0'
  default_protection_pg:
      description:
      - Name of the default protection default for the pod
      - Only applicable for existing pods
      - Name must include the pod name
      - Will create the PG in the pod if it doesn't already exist
      - To remove an existing default protection group provide an empty
        list C([]) or an empty string C("").
      - Accepts either a string or a single-element list.
      type: raw
      version_added: '1.37.0'
  retention_lock:
    description:
      - Define if I(default_protection_pg) has retention lock enabled
    type: bool
    default: True
    version_added: '1.37.0'
extends_documentation_fragment:
- everpure.flasharray.everpure.fa
"""

EXAMPLES = r"""
- name: Create new pod named foo without SafeMode default protection
  everpure.flasharray.purefa_pod:
    name: foo
    with_default_protection: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Create new pod bar inside realm myrealm
  everpure.flasharray.purefa_pod:
    name: bar
    realm: myrealm
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Create new pod named foo with default protection PG safe, and with PG retention lock disabled
  everpure.flasharray.purefa_pod:
    name: foo
    default_protection_pg: safe
    retention_lock: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present

- name: Delete and eradicate pod named foo
  everpure.flasharray.purefa_pod:
    name: foo
    eradicate: true
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: absent

- name: Set failover array for pod named foo
  everpure.flasharray.purefa_pod:
    name: foo
    failover:
      - array1
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Set mediator for pod named foo
  everpure.flasharray.purefa_pod:
    name: foo
    mediator: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Stretch a pod named foo to array2
  everpure.flasharray.purefa_pod:
    name: foo
    stretch: array2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Unstretch a pod named foo from array2
  everpure.flasharray.purefa_pod:
    name: foo
    stretch: array2
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create clone of pod foo named bar
  everpure.flasharray.purefa_pod:
    name: foo
    target: bar
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
    state: present
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        PodPost,
        PodPatch,
        Reference,
        ContainerDefaultProtection,
        DefaultProtectionReference,
        ProtectionGroup,
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
)
from ansible_collections.everpure.flasharray.plugins.module_utils.version import (
    LooseVersion,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_response,
    delete_with_context,
    get_with_context,
    patch_with_context,
    post_with_context,
    post_with_throttle_and_context,
)

DEFAULT_API_VERSION = "2.16"
POD_QUOTA_VERSION = "2.23"
THROTTLE_VERSION = "2.31"
MEMBERS_VERSION = "2.36"
REALM_VERSION = "2.36"
CONTEXT_VERSION = "2.38"


def quota_request(module):
    """Return (clear, bytes) for the quota parameter.

    A quota of "0" or "" means remove the limit, which the REST API
    expresses as an empty string in the quota_limit field.
    """
    quota = module.params["quota"]
    if quota is None:
        return False, None
    if str(quota).strip() in ("", "0"):
        return True, None
    return False, human_to_bytes(quota)


def default_protection_request(module):
    """Return (clear, pgname) for the default_protection_pg parameter.

    The option accepts a protection group name, or an empty list / empty
    string to request removal of the current default protection.
    """
    value = module.params["default_protection_pg"]
    if value is None:
        return False, None
    if isinstance(value, (list, tuple)):
        if not value:
            return True, None
        if len(value) > 1:
            module.fail_json(msg="Only one default protection group may be specified")
        value = value[0]
    value = str(value).strip()
    if value in ("", "[]"):
        return True, None
    return False, value


def get_pod(module, array):
    """Return Pod or None"""
    res = get_with_context(
        array,
        "get_pods",
        CONTEXT_VERSION,
        module,
        names=[module.params["name"]],
        destroyed=False,
    )
    return res.status_code == 200


def get_undo_pod(module, array):
    """Return list of Undo Pods or None if none exist"""
    res = get_with_context(
        array,
        "get_pods",
        CONTEXT_VERSION,
        module,
        names=[module.params["name"] + ".undo-demote.*"],
    )
    if res.status_code == 200:
        pods = list(res.items)
        return pods if pods else None
    return None


def get_target(module, array):
    """Return Target Pod or None"""
    res = get_with_context(
        array,
        "get_pods",
        CONTEXT_VERSION,
        module,
        names=[module.params["target"]],
        destroyed=False,
    )
    return res.status_code == 200


def get_destroyed_pod(module, array):
    """Return Destroyed Pod or None"""
    res = get_with_context(
        array,
        "get_pods",
        CONTEXT_VERSION,
        module,
        names=[module.params["name"]],
        destroyed=True,
    )
    return res.status_code == 200


def get_destroyed_target(module, array):
    """Return Destroyed Target Pod or None"""
    res = get_with_context(
        array,
        "get_pods",
        CONTEXT_VERSION,
        module,
        names=[module.params["target"]],
        destroyed=True,
    )
    return res.status_code == 200


def check_arrays(module, array):
    """Check if array name provided are sync-replicated"""
    good_arrays = []
    arrays_res = get_with_context(array, "get_arrays", CONTEXT_VERSION, module)
    good_arrays.append(list(arrays_res.items)[0].name)
    conn_res = get_with_context(array, "get_array_connections", CONTEXT_VERSION, module)
    connected_arrays = list(conn_res.items)
    for arr in connected_arrays:
        if arr.type == "sync-replication":
            good_arrays.append(arr.name)
    if module.params["failover"] is not None:
        if module.params["failover"] == ["auto"]:
            failover_array = []
        else:
            failover_array = module.params["failover"]
        if failover_array != []:
            for arr in failover_array:
                if arr not in good_arrays:
                    module.fail_json(msg="Failover array {0} is not valid.".format(arr))
    if module.params["stretch"] is not None:
        if module.params["stretch"] not in good_arrays:
            module.fail_json(
                msg="Stretch: Array {0} is not connected.".format(
                    module.params["stretch"]
                )
            )
    return None


def create_pod(module, array):
    """Create Pod"""
    api_version = array.get_rest_version()
    changed = True
    if module.params["target"]:
        module.fail_json(msg="Cannot clone non-existent pod.")
    if not module.check_mode:
        if module.params["failover"]:
            failovers = []
            for fo_array in module.params["failover"]:
                failovers.append(Reference(name=fo_array))
            res = post_with_throttle_and_context(
                array,
                "post_pods",
                THROTTLE_VERSION,
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                pod=PodPost(failover_preferences=failovers),
            )
        else:
            res = post_with_throttle_and_context(
                array,
                "post_pods",
                THROTTLE_VERSION,
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                pod=PodPost(),
            )
        check_response(res, module, f"Pod {module.params['name']} creation")
        if module.params["mediator"] != "purestorage":
            res = patch_with_context(
                array,
                "patch_pods",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                pod=PodPatch(mediator=module.params["mediator"]),
            )
            if res.status_code != 200:
                module.warn(
                    f"Failed to communicate with mediator {module.params['mediator']}, using default value."
                )
        if module.params["stretch"]:
            arrays_res = get_with_context(array, "get_arrays", CONTEXT_VERSION, module)
            current_array = list(arrays_res.items)[0].name
            if module.params["stretch"] != current_array:
                if LooseVersion(MEMBERS_VERSION) <= LooseVersion(api_version):
                    res = post_with_context(
                        array,
                        "post_pods_members",
                        CONTEXT_VERSION,
                        module,
                        pod_names=[module.params["name"]],
                        member_names=[module.params["stretch"]],
                    )
                else:
                    res = array.post_pods_arrays(
                        group_names=[module.params["name"]],
                        member_names=[module.params["stretch"]],
                    )
                check_response(
                    res,
                    module,
                    f"Failed to stretch pod {module.params['name']} to array {module.params['stretch']}",
                )
        _clear_quota, quota = quota_request(module)
        if quota and LooseVersion(POD_QUOTA_VERSION) <= LooseVersion(api_version):
            res = patch_with_context(
                array,
                "patch_pods",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                pod=PodPatch(quota_limit=quota),
            )
            check_response(
                res, module, f"Failed to apply quota to pod {module.params['name']}"
            )
        if LooseVersion(DEFAULT_API_VERSION) <= LooseVersion(api_version):
            res = get_with_context(
                array,
                "get_container_default_protections",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
            )
            check_response(
                res,
                module,
                f"Failed to get container default protection for pod {module.params['name']}",
            )
            safemode_pg = list(res.items)[0].default_protections
            if safemode_pg:
                pgname = safemode_pg[0].name
            else:
                pgname = None
            if pgname and not module.params["with_default_protection"]:
                res = patch_with_context(
                    array,
                    "patch_container_default_protections",
                    CONTEXT_VERSION,
                    module,
                    names=[module.params["name"]],
                    container_default_protection=(
                        ContainerDefaultProtection(default_protections=[])
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to remove default protection for pod {module.params['name']}",
                )
                res = patch_with_context(
                    array,
                    "patch_protection_groups",
                    CONTEXT_VERSION,
                    module,
                    names=[pgname],
                    protection_group=ProtectionGroup(destroyed=True),
                )
                check_response(
                    res,
                    module,
                    f"Deleting safemode default pgroup {module.params['name']}",
                )
                res = delete_with_context(
                    array,
                    "delete_protection_groups",
                    CONTEXT_VERSION,
                    module,
                    names=[pgname],
                )
                check_response(
                    res,
                    module,
                    f"Eradicating safemode default pgroup {module.params['name']}",
                )
            clear_dp, new_pg = default_protection_request(module)
            if (
                safemode_pg
                and not module.params["with_default_protection"]
                and (clear_dp or new_pg)
            ):
                if clear_dp:
                    module.fail_json(
                        msg="use with_default_protection: false to set no default protection"
                    )
                res = get_with_context(
                    array,
                    "get_protection_groups",
                    CONTEXT_VERSION,
                    module,
                    names=[new_pg],
                )
                if res.status_code != 200:
                    pg_res = post_with_context(
                        array,
                        "post_protection_groups",
                        CONTEXT_VERSION,
                        module,
                        names=[new_pg],
                    )
                    check_response(
                        pg_res,
                        module,
                        f"Failed to create default protection group {module.params['name']}",
                    )
                if module.params["retention_lock"]:
                    res = patch_with_context(
                        array,
                        "patch_protection_groups",
                        CONTEXT_VERSION,
                        module,
                        names=[new_pg],
                        protection_group=ProtectionGroup(retention_lock="ratcheted"),
                    )
                    check_response(
                        res,
                        module,
                        f"Failed to set retention lock for protection group {new_pg}",
                    )
                patch_with_context(
                    array,
                    "patch_container_default_protections",
                    CONTEXT_VERSION,
                    module,
                    names=[module.params["name"]],
                    container_default_protection=(
                        ContainerDefaultProtection(default_protections=[])
                    ),
                )
                res = patch_with_context(
                    array,
                    "patch_container_default_protections",
                    CONTEXT_VERSION,
                    module,
                    names=[module.params["name"]],
                    container_default_protection=(
                        ContainerDefaultProtection(
                            default_protections=[
                                DefaultProtectionReference(
                                    name=new_pg,
                                    type="protection_group",
                                )
                            ]
                        )
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to set default protection for pod {module.params['name']}",
                )
    module.exit_json(changed=changed)


def clone_pod(module, array):
    """Create Pod Clone"""
    changed = False
    if not get_target(module, array):
        if not get_destroyed_target(module, array):
            changed = True
            if not module.check_mode:
                res = post_with_throttle_and_context(
                    array,
                    "post_pods",
                    THROTTLE_VERSION,
                    CONTEXT_VERSION,
                    module,
                    pod=PodPost(source=Reference(name=module.params["name"])),
                    names=[module.params["target"]],
                )
                check_response(
                    res,
                    module,
                    f"Clone pod {module.params['name']} to pod {module.params['target']}",
                )
        else:
            module.fail_json(
                msg="Target pod {0} already exists but deleted.".format(
                    module.params["target"]
                )
            )

    module.exit_json(changed=changed)


def update_pod(module, array):
    """Update Pod configuration"""
    api_version = array.get_rest_version()
    changed = False
    res = get_with_context(
        array, "get_pods", CONTEXT_VERSION, module, names=[module.params["name"]]
    )
    current_config = list(res.items)[0]
    if module.params["failover"]:
        # failover_preferences is a list of Reference objects; compare names
        current_failover = [
            getattr(fo_array, "name", fo_array)
            for fo_array in (current_config.failover_preferences or [])
        ]
        if module.params["failover"] == ["auto"]:
            desired_failover = []
        else:
            desired_failover = module.params["failover"]
        if sorted(desired_failover) != sorted(current_failover):
            changed = True
            if not module.check_mode:
                if module.params["failover"] == ["auto"]:
                    res = patch_with_context(
                        array,
                        "patch_pods",
                        CONTEXT_VERSION,
                        module,
                        names=[module.params["name"]],
                        pod=PodPatch(failover_preferences=[]),
                    )
                    check_response(
                        res,
                        module,
                        f"Failed to clear failover preference for pod {module.params['name']}",
                    )
                else:
                    failovers = []
                    for fo_array in module.params["failover"]:
                        failovers.append(Reference(name=fo_array))
                    res = patch_with_context(
                        array,
                        "patch_pods",
                        CONTEXT_VERSION,
                        module,
                        names=[module.params["name"]],
                        pod=PodPatch(failover_preferences=failovers),
                    )
                check_response(
                    res,
                    module,
                    f"Failed to set failover preference for pod {module.params['name']}",
                )
    if current_config.mediator != module.params["mediator"]:
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_pods",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                pod=PodPatch(mediator=module.params["mediator"]),
            )
            if res.status_code != 200:
                module.warn(
                    f"Failed to communicate with mediator {module.params['mediator']}. Setting unchanged. Error: {res.errors[0].message}"
                )
    if module.params["promote"] is not None:
        if current_config.array_count > 1:
            module.fail_json(
                msg="Promotion/Demotion not permitted. Pod {0} is stretched".format(
                    module.params["name"]
                )
            )
        else:
            # Check if pod is quiescing - cannot promote/demote during transition
            if current_config.promotion_status == "quiescing":
                module.fail_json(
                    msg="Cannot promote pod {0} as it is still quiesing".format(
                        module.params["name"]
                    )
                )
            # Check if pod is already in desired state (idempotency)
            if (
                module.params["promote"]
                and current_config.promotion_status == "promoted"
            ):
                # Already promoted, nothing to do
                pass
            elif (
                not module.params["promote"]
                and current_config.promotion_status == "demoted"
            ):
                # Already demoted, nothing to do
                pass
            elif (
                current_config.promotion_status == "demoted"
                and module.params["promote"]
            ):
                # Promote a demoted pod
                changed = True
                if not module.check_mode:
                    if module.params["undo"] is None:
                        module.params["undo"] = True
                    if module.params["undo"]:
                        undo_pod = get_undo_pod(module, array)
                        if undo_pod:
                            if len(undo_pod) == 1:
                                res = patch_with_context(
                                    array,
                                    "patch_pods",
                                    CONTEXT_VERSION,
                                    module,
                                    pod=PodPatch(requested_promotion_state="promoted"),
                                    names=[module.params["name"]],
                                    promote_from=undo_pod[0].name,
                                )
                            else:
                                res = patch_with_context(
                                    array,
                                    "patch_pods",
                                    CONTEXT_VERSION,
                                    module,
                                    pod=PodPatch(requested_promotion_state="promoted"),
                                    names=[module.params["name"]],
                                    promote_from=undo_pod[-1].name,
                                )
                                module.warn(
                                    f"undo-demote pod(s) remaining for {module.params['name']}. Consider eradicating."
                                )
                            check_response(
                                res,
                                module,
                                f"Failed to promote pod {module.params['name']}",
                            )
                        else:
                            # No undo-demote pod found, but undo=True was requested
                            # Cannot promote without undo-demote pod when undo=True
                            changed = False
                            module.warn(
                                f"undo-demote pod(s) missing for {module.params['name']}. Check use of `undo` parameter."
                            )
                    else:
                        res = patch_with_context(
                            array,
                            "patch_pods",
                            CONTEXT_VERSION,
                            module,
                            names=[module.params["name"]],
                            pod=PodPatch(requested_promotion_state="promoted"),
                        )
                        check_response(
                            res,
                            module,
                            f"Failed to promote pod {module.params['name']}",
                        )
            elif (
                current_config.promotion_status != "demoted"
                and not module.params["promote"]
            ):
                # Demote a promoted pod
                if get_undo_pod(module, array):
                    module.fail_json(
                        msg=f"Cannot demote pod {module.params['name']} due to associated undo-demote pod not being eradicated"
                    )
                changed = True
                if not module.check_mode:
                    if module.params["quiesce"] is None:
                        module.params["quiesce"] = True
                    if current_config["link_target_count"] == 0:
                        res = patch_with_context(
                            array,
                            "patch_pods",
                            CONTEXT_VERSION,
                            module,
                            names=[module.params["name"]],
                            pod=PodPatch(requested_promotion_state="demoted"),
                        )
                    elif not module.params["quiesce"]:
                        res = patch_with_context(
                            array,
                            "patch_pods",
                            CONTEXT_VERSION,
                            module,
                            names=[module.params["name"]],
                            pod=PodPatch(requested_promotion_state="demoted"),
                            skip_quiesce=True,
                        )
                    else:
                        res = patch_with_context(
                            array,
                            "patch_pods",
                            CONTEXT_VERSION,
                            module,
                            names=[module.params["name"]],
                            pod=PodPatch(requested_promotion_state="demoted"),
                            quiesce=True,
                        )
                    check_response(
                        res, module, f"Failed to demote pod {module.params['name']}"
                    )
    clear_quota, quota = quota_request(module)
    if (clear_quota or quota) and LooseVersion(POD_QUOTA_VERSION) <= LooseVersion(
        api_version
    ):
        # An unset quota is reported as None (or 0); the API clears a quota
        # with an empty string in quota_limit.
        current_quota = getattr(current_config, "quota_limit", None) or None
        desired_quota = None if clear_quota else quota
        if current_quota != desired_quota:
            changed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_pods",
                    CONTEXT_VERSION,
                    module,
                    names=[module.params["name"]],
                    pod=PodPatch(
                        quota_limit="" if clear_quota else quota,
                        ignore_usage=module.params["ignore_usage"],
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to update quota on pod {module.params['name']}",
                )
    clear_dp, new_pg = default_protection_request(module)
    if (clear_dp or new_pg) and LooseVersion(DEFAULT_API_VERSION) <= LooseVersion(
        api_version
    ):
        res = get_with_context(
            array,
            "get_container_default_protections",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
        )
        safemode_pg = list(res.items)[0].default_protections
        if safemode_pg:
            pgname = safemode_pg[0].name
        else:
            pgname = None
        if clear_dp:
            if safemode_pg:
                changed = True
                if not module.check_mode:
                    res = patch_with_context(
                        array,
                        "patch_container_default_protections",
                        CONTEXT_VERSION,
                        module,
                        names=[module.params["name"]],
                        container_default_protection=(
                            ContainerDefaultProtection(default_protections=[])
                        ),
                    )
                    check_response(
                        res,
                        module,
                        f"Failed to remove default protection for pod {module.params['name']}",
                    )
        elif pgname != new_pg:
            changed = True
            if not module.check_mode:
                res = get_with_context(
                    array,
                    "get_protection_groups",
                    CONTEXT_VERSION,
                    module,
                    names=[new_pg],
                )
                if res.status_code != 200:
                    pg_res = post_with_context(
                        array,
                        "post_protection_groups",
                        CONTEXT_VERSION,
                        module,
                        names=[new_pg],
                    )
                    check_response(
                        pg_res,
                        module,
                        f"Failed to create default protection group {module.params['name']}",
                    )
                if module.params["retention_lock"]:
                    res = patch_with_context(
                        array,
                        "patch_protection_groups",
                        CONTEXT_VERSION,
                        module,
                        names=[new_pg],
                        protection_group=ProtectionGroup(retention_lock="ratcheted"),
                    )
                    check_response(
                        res,
                        module,
                        f"Failed to set retention lock for protection group {new_pg}",
                    )
                if safemode_pg:
                    patch_with_context(
                        array,
                        "patch_container_default_protections",
                        CONTEXT_VERSION,
                        module,
                        names=[module.params["name"]],
                        container_default_protection=(
                            ContainerDefaultProtection(default_protections=[])
                        ),
                    )
                res = patch_with_context(
                    array,
                    "patch_container_default_protections",
                    CONTEXT_VERSION,
                    module,
                    names=[module.params["name"]],
                    container_default_protection=(
                        ContainerDefaultProtection(
                            default_protections=[
                                DefaultProtectionReference(
                                    name=new_pg,
                                    type="protection_group",
                                )
                            ]
                        )
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Failed to update default protection for pod {module.params['name']}",
                )
    module.exit_json(changed=changed)


def stretch_pod(module, array):
    """Stretch/unstretch Pod configuration"""
    api_version = array.get_rest_version()
    changed = False
    res = get_with_context(
        array, "get_pods", CONTEXT_VERSION, module, names=[module.params["name"]]
    )
    current_config = list(res.items)[0]
    if module.params["stretch"]:
        current_arrays = []
        for arr in current_config.arrays:
            current_arrays.append(arr["name"])
        if (
            module.params["stretch"] not in current_arrays
            and module.params["state"] == "present"
        ):
            changed = True
            if not module.check_mode:
                if LooseVersion(MEMBERS_VERSION) <= LooseVersion(api_version):
                    res = post_with_context(
                        array,
                        "post_pods_members",
                        CONTEXT_VERSION,
                        module,
                        pod_names=[module.params["name"]],
                        member_names=[module.params["stretch"]],
                    )
                else:
                    res = array.post_pods_arrays(
                        group_names=[module.params["name"]],
                        member_names=[module.params["stretch"]],
                    )
                check_response(
                    res,
                    module,
                    f"Failed to stretch pod {module.params['name']} to array {module.params['stretch']}",
                )

        if (
            module.params["stretch"] in current_arrays
            and module.params["state"] == "absent"
        ):
            changed = True
            if not module.check_mode:
                if LooseVersion(MEMBERS_VERSION) <= LooseVersion(api_version):
                    res = delete_with_context(
                        array,
                        "delete_pods_members",
                        CONTEXT_VERSION,
                        module,
                        pod_names=[module.params["name"]],
                        member_names=[module.params["stretch"]],
                    )
                else:
                    res = array.delete_pods_arrays(
                        group_names=[module.params["name"]],
                        member_names=[module.params["stretch"]],
                    )
                check_response(
                    res,
                    module,
                    f"Failed to unstretch pod {module.params['name']} from array {module.params['stretch']}",
                )

    module.exit_json(changed=changed)


def delete_pod(module, array):
    """Delete Pod"""
    changed = True
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_pods",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            pod=PodPatch(destroyed=True),
            destroy_contents=module.params["delete_contents"],
        )
        check_response(res, module, f"Delete pod {module.params['name']}")
        if module.params["eradicate"]:
            res = delete_with_context(
                array,
                "delete_pods",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                eradicate_contents=module.params["delete_contents"],
            )
            check_response(res, module, f"Eradicate pod {module.params['name']}")
    module.exit_json(changed=changed)


def eradicate_pod(module, array):
    """Eradicate Deleted Pod"""
    changed = False
    if module.params["eradicate"]:
        changed = True
        if not module.check_mode:
            res = delete_with_context(
                array,
                "delete_pods",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                eradicate_contents=module.params["delete_contents"],
            )
            check_response(res, module, f"Eradication of pod {module.params['name']}")
    module.exit_json(changed=changed)


def recover_pod(module, array):
    """Recover Deleted Pod"""
    changed = True
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_pods",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
            pod=PodPatch(destroyed=False),
        )
        check_response(res, module, f"Recovery of pod {module.params['name']}")
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            realm=dict(type="str"),
            stretch=dict(type="str"),
            target=dict(type="str"),
            mediator=dict(type="str", default="purestorage"),
            failover=dict(type="list", elements="str"),
            promote=dict(type="bool"),
            undo=dict(type="bool"),
            quiesce=dict(type="bool"),
            eradicate=dict(type="bool", default=False),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            quota=dict(type="str"),
            ignore_usage=dict(type="bool", default=False),
            throttle=dict(type="bool", default=False),
            delete_contents=dict(type="bool", default=False),
            context=dict(type="str", default=""),
            with_default_protection=dict(type="bool", default=True),
            default_protection_pg=dict(type="raw"),
            retention_lock=dict(type="bool", default=True),
        )
    )

    mutually_exclusive = [
        ["stretch", "failover"],
        ["stretch", "eradicate"],
        ["stretch", "mediator"],
        ["target", "mediator"],
        ["target", "stretch"],
        ["target", "failover"],
        ["target", "eradicate"],
    ]

    module = AnsibleModule(
        argument_spec, mutually_exclusive=mutually_exclusive, supports_check_mode=True
    )

    state = module.params["state"]
    array = get_array(module)

    if module.params.get("realm"):
        if LooseVersion(REALM_VERSION) > LooseVersion(array.get_rest_version()):
            module.fail_json(
                msg="realm parameter requires Purity//FA 6.6.11, or higher (REST 2.36)."
            )
        if "::" in module.params["name"]:
            module.fail_json(
                msg="Use either the 'realm' parameter or the 'realm::pod' "
                "form in 'name', not both."
            )
        module.params["name"] = module.params["realm"] + "::" + module.params["name"]

    pod = get_pod(module, array)
    destroyed = ""
    if not pod:
        destroyed = get_destroyed_pod(module, array)
    if module.params["failover"] or module.params["stretch"]:
        check_arrays(module, array)

    if state == "present" and destroyed:
        recover_pod(module, array)
    elif state == "present" and not pod:
        create_pod(module, array)
    elif pod and module.params["stretch"]:
        stretch_pod(module, array)
    elif state == "present" and pod and module.params["target"]:
        clone_pod(module, array)
    elif state == "present" and pod:
        update_pod(module, array)
    elif state == "absent" and pod and not module.params["stretch"]:
        delete_pod(module, array)
    elif state == "absent" and destroyed:
        eradicate_pod(module, array)
    elif state == "absent" and not pod:
        module.exit_json(changed=False)


if __name__ == "__main__":
    main()
