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
module: purefa_qos_policy
version_added: '1.46.0'
short_description: Manage Everpure FlashArray QoS policies
description:
- Create, update, rename or delete QoS policies on Everpure FlashArrays and
  manage the managed directories they are attached to.
- A QoS policy is a reusable object. It stores an aggregate bandwidth ceiling
  and an aggregate operations-per-second ceiling, both totaled across all
  clients of the managed directories it is attached to. The policy has no
  effect on traffic until it is attached to at least one managed directory.
- This release covers managed-directory QoS policy only. File server QoS,
  QoS client-specific rules, QoS priority bands (floors), and block-entity
  (volume, host, volume group) QoS configuration are out of scope and not
  managed by this module.
author:
- Everpure Ansible Team (@avk) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of the QoS policy.
    type: str
    required: true
  state:
    description:
    - Define whether the QoS policy should exist or not.
    - C(absent) fails if the policy is still attached to any managed
      directory. Detach it first (see I(directories)).
    default: present
    type: str
    choices: [ absent, present ]
  enabled:
    description:
    - If C(true) the policy is enabled.
    - Defaults to C(true) on creation if not specified.
    type: bool
  rename:
    description:
    - Value to rename the specified QoS policy to.
    - The destination name must not already be in use.
    - Renaming is a standalone operation. Other field changes given in the
      same task are not applied. Run the module again under the new name to
      apply them.
    type: str
  max_total_bytes_per_sec:
    description:
    - Aggregate bandwidth ceiling, in bytes per second, totaled across all
      clients of the managed directories this policy is attached to.
    - Valid range is 1048576 (1 MiB/s) to 549755813888 (512 GiB/s).
    - Set to C(0) to clear a previously configured limit. Omit the option to
      leave the current limit untouched on update, or to create the policy
      with no limit.
    type: int
  max_total_ops_per_sec:
    description:
    - Aggregate operations-per-second ceiling, totaled across all clients of
      the managed directories this policy is attached to.
    - Valid range is 100 to 100000000.
    - Set to C(0) to clear a previously configured limit. Omit the option to
      leave the current limit untouched on update, or to create the policy
      with no limit.
    type: int
  directories:
    description:
    - Desired set of managed directories this policy should be attached to,
      given as C(filesystem:directory) names.
    - Declarative. Directories in the list that are not attached to this
      policy are attached, and directories attached to this policy that are
      not in the list are detached. An empty list detaches the policy from
      all directories.
    - Omit the option to leave the policy's directory attachments alone.
      Attachments change only when this option is named explicitly.
    - A managed directory already governed by a different QoS policy cannot
      be attached to this one; detach the existing policy first.
    type: list
    elements: str
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
- Requires Purity//FA REST API 2.54 or higher, which is where managed-directory
  QoS policies and their directory attachments first appear.
"""

EXAMPLES = r"""
- name: Create a QoS policy with both limits
  everpure.flasharray.purefa_qos_policy:
    name: qos_gold
    max_total_bytes_per_sec: 107374182400
    max_total_ops_per_sec: 10000
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create a QoS policy with only a bandwidth ceiling
  everpure.flasharray.purefa_qos_policy:
    name: qos_bandwidth_only
    max_total_bytes_per_sec: 52428800
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Change only the operations ceiling without touching anything else
  everpure.flasharray.purefa_qos_policy:
    name: qos_gold
    max_total_ops_per_sec: 20000
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Clear the bandwidth ceiling
  everpure.flasharray.purefa_qos_policy:
    name: qos_gold
    max_total_bytes_per_sec: 0
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Attach a QoS policy to a set of managed directories
  everpure.flasharray.purefa_qos_policy:
    name: qos_gold
    directories:
      - fs1:dir1
      - fs1:dir2
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Detach a QoS policy from all managed directories
  everpure.flasharray.purefa_qos_policy:
    name: qos_gold
    directories: []
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Disable a QoS policy without deleting it
  everpure.flasharray.purefa_qos_policy:
    name: qos_gold
    enabled: false
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Rename a QoS policy
  everpure.flasharray.purefa_qos_policy:
    name: qos_gold
    rename: qos_platinum
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Delete an unattached QoS policy
  everpure.flasharray.purefa_qos_policy:
    name: qos_gold
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        PolicyMemberPost,
        PolicymemberpostMembers,
        PolicyQosPatch,
        PolicyQosPost,
        ReferenceWithType,
    )
except ImportError:
    HAS_PURESTORAGE = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_api_version,
    check_response,
    delete_with_context,
    get_with_context,
    patch_with_context,
    post_with_context,
)

# QoS policies, their attributes, and the policy-member directory attachment
# all arrived together in this version - there is no partial support to work
# around
MIN_API_VERSION_QOS_POLICY = "2.54"
MIN_API_VERSION_QOS_POLICY_MEMBERS = "2.54"

# The managed-directory member type for QoS policy membership. No other
# member type is documented for this policy type in this release.
QOS_MEMBER_RESOURCE_TYPE = "directories"

MIN_BANDWIDTH = 1048576  # 1 MiB/s
MAX_BANDWIDTH = 549755813888  # 512 GiB/s
MIN_IOPS = 100
MAX_IOPS = 100000000


def _validate_limit(module, option, value, minimum, maximum):
    """Fail fast on an out-of-range limit

    C(0) is the documented way to clear a limit, so it is exempt from the
    range check; only a genuine attempt to set a positive limit is validated
    here, the array remains the authority on everything else.
    """
    if value is None or value == 0:
        return
    if value < minimum or value > maximum:
        module.fail_json(
            msg="{0} value {1} out of range. Must be 0 (to clear) or between "
            "{2} and {3}.".format(option, value, minimum, maximum)
        )


def _current_limit(policy, field):
    """Read a limit field off the policy, normalized to this module's sentinel

    Confirmed against a live array: an unset limit is omitted from the
    response entirely, which getattr(..., None) reads as None, not 0. Without
    this normalization, a task that clears a limit with 0 would compare 0
    against None forever and PATCH on every single run.
    """
    value = getattr(policy, field, None)
    return 0 if value is None else value


def _validate_directories(module):
    """Fail fast on duplicate directory names in the task

    Returns the deduplicated, sorted list the rest of the module should use,
    or None when the option was not supplied at all.
    """
    directories = module.params["directories"]
    if directories is None:
        return None
    seen = set()
    duplicates = sorted({d for d in directories if d in seen or seen.add(d)})
    if duplicates:
        module.fail_json(
            msg="directories contains duplicate name(s): {0}".format(duplicates)
        )
    return sorted(directories)


def _read_policy(module, array, name):
    """Return the named QoS policy, or None if the array does not have it"""
    res = get_with_context(
        array, "get_policies_qos", MIN_API_VERSION_QOS_POLICY, module, names=[name]
    )
    if res.status_code != 200:
        return None
    return next(iter(list(res.items)), None)


def _attached_directories(module, array):
    """Names of the managed directories this policy is currently attached to

    A membership names the directory as its C(member) and the policy as its
    C(policy), so this reads the memberships of the policy and picks out the
    directory on each.
    """
    res = get_with_context(
        array,
        "get_policies_qos_members",
        MIN_API_VERSION_QOS_POLICY_MEMBERS,
        module,
        policy_names=[module.params["name"]],
    )
    if res.status_code != 200:
        return []
    names = []
    for item in list(res.items):
        member_name = getattr(getattr(item, "member", None), "name", None)
        if member_name:
            names.append(member_name)
    return sorted(names)


def _validate_attachable(module, array, directories):
    """Validate every directory exists and isn't bound to a different QoS policy

    Called for the to-attach subset only: a directory already bound to this
    policy is a no-op upstream and never reaches here.
    """
    if not directories:
        return
    res = get_with_context(
        array,
        "get_directories",
        MIN_API_VERSION_QOS_POLICY_MEMBERS,
        module,
        names=directories,
    )
    if res.status_code != 200:
        module.fail_json(msg="Managed directory(s) not found: {0}".format(directories))
    found = {getattr(d, "name", None) for d in list(res.items)}
    missing = [d for d in directories if d not in found]
    if missing:
        module.fail_json(msg="Managed directory(s) not found: {0}".format(missing))

    res = get_with_context(
        array,
        "get_policies_qos_members",
        MIN_API_VERSION_QOS_POLICY_MEMBERS,
        module,
        member_names=directories,
    )
    if res.status_code != 200:
        return
    our_name = module.params["name"]
    conflicts = []
    for item in list(res.items):
        policy_name = getattr(getattr(item, "policy", None), "name", None)
        directory_name = getattr(getattr(item, "member", None), "name", None)
        if policy_name and policy_name != our_name:
            conflicts.append((directory_name, policy_name))
    if conflicts:
        formatted = ", ".join("{0}=>{1}".format(d, p) for d, p in conflicts)
        module.fail_json(
            msg="Cannot attach QoS policy {0} - the following managed "
            "directory(s) already have a different QoS policy applied: {1}. "
            "Detach the existing policy before re-attaching.".format(
                our_name, formatted
            )
        )


def _attach_directories(module, array, directories):
    """Attach this policy to one or more managed directories in a single call"""
    res = post_with_context(
        array,
        "post_policies_qos_members",
        MIN_API_VERSION_QOS_POLICY_MEMBERS,
        module,
        policy_names=[module.params["name"]],
        members=PolicyMemberPost(
            members=[
                PolicymemberpostMembers(
                    member=ReferenceWithType(
                        name=directory, resource_type=QOS_MEMBER_RESOURCE_TYPE
                    )
                )
                for directory in directories
            ]
        ),
    )
    check_response(
        res,
        module,
        "Failed to attach QoS policy {0} to managed directory(s) {1}".format(
            module.params["name"], directories
        ),
    )


def _detach_directories(module, array, directories):
    """Detach this policy from one or more managed directories in a single call

    Unlike the attach POST body, which carries resource_type on each member
    reference, DELETE has no body - member_names alone leaves the array unable
    to resolve what kind of resource the names refer to, so member_types is
    required here.
    """
    res = delete_with_context(
        array,
        "delete_policies_qos_members",
        MIN_API_VERSION_QOS_POLICY_MEMBERS,
        module,
        policy_names=[module.params["name"]],
        member_names=directories,
        member_types=[QOS_MEMBER_RESOURCE_TYPE],
    )
    check_response(
        res,
        module,
        "Failed to detach QoS policy {0} from managed directory(s) {1}".format(
            module.params["name"], directories
        ),
    )


def _reconcile_directories(module, array):
    """Make the policy's attached directories match the task

    Returns whether anything needed changing. Does nothing at all when the
    task did not name the option, so a task that says nothing about
    directories never detaches one.
    """
    wanted = _validate_directories(module)
    if wanted is None:
        return False
    current = _attached_directories(module, array)
    to_attach = [d for d in wanted if d not in current]
    to_detach = [d for d in current if d not in wanted]
    if not to_attach and not to_detach:
        return False
    if to_attach:
        _validate_attachable(module, array, to_attach)
    if not module.check_mode:
        if to_attach:
            _attach_directories(module, array, to_attach)
        if to_detach:
            _detach_directories(module, array, to_detach)
    return True


def _build_post_kwargs(module):
    """Build kwargs for PolicyQosPost from the options the task supplied

    Only options the task actually set are included, so the array applies
    its own defaults for the rest. The exception is C(enabled): the array
    requires it on create, so it defaults to C(true) here to match the
    documented behaviour.
    """
    kwargs = {}
    kwargs["enabled"] = (
        module.params["enabled"] if module.params["enabled"] is not None else True
    )
    if module.params["max_total_bytes_per_sec"] is not None:
        kwargs["max_total_bytes_per_sec"] = module.params["max_total_bytes_per_sec"]
    if module.params["max_total_ops_per_sec"] is not None:
        kwargs["max_total_ops_per_sec"] = module.params["max_total_ops_per_sec"]
    return kwargs


def create_policy(module, array):
    """Create a QoS policy and optionally attach it to managed directories"""
    changed = True
    directories = _validate_directories(module)
    if directories:
        _validate_attachable(module, array, directories)
    if not module.check_mode:
        res = post_with_context(
            array,
            "post_policies_qos",
            MIN_API_VERSION_QOS_POLICY,
            module,
            names=[module.params["name"]],
            policy=PolicyQosPost(**_build_post_kwargs(module)),
        )
        check_response(
            res,
            module,
            "Failed to create QoS policy {0}".format(module.params["name"]),
        )
        if directories:
            _attach_directories(module, array, directories)
    module.exit_json(changed=changed)


def update_policy(module, array, policy):
    """Update a QoS policy and reconcile its managed-directory attachments"""
    changed = False
    patch = {}

    if module.params["enabled"] is not None and module.params["enabled"] != getattr(
        policy, "enabled", None
    ):
        patch["enabled"] = module.params["enabled"]

    if module.params["max_total_bytes_per_sec"] is not None and module.params[
        "max_total_bytes_per_sec"
    ] != _current_limit(policy, "max_total_bytes_per_sec"):
        patch["max_total_bytes_per_sec"] = module.params["max_total_bytes_per_sec"]

    if module.params["max_total_ops_per_sec"] is not None and module.params[
        "max_total_ops_per_sec"
    ] != _current_limit(policy, "max_total_ops_per_sec"):
        patch["max_total_ops_per_sec"] = module.params["max_total_ops_per_sec"]

    if patch:
        changed = True
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_policies_qos",
                MIN_API_VERSION_QOS_POLICY,
                module,
                names=[module.params["name"]],
                policy=PolicyQosPatch(**patch),
            )
            check_response(
                res,
                module,
                "Failed to update QoS policy {0}".format(module.params["name"]),
            )

    if _reconcile_directories(module, array):
        changed = True

    module.exit_json(changed=changed)


def rename_policy(module, array):
    """Rename a QoS policy"""
    changed = True
    if _read_policy(module, array, module.params["rename"]):
        module.fail_json(
            msg="Target QoS policy {0} already exists".format(module.params["rename"])
        )
    if not module.check_mode:
        res = patch_with_context(
            array,
            "patch_policies_qos",
            MIN_API_VERSION_QOS_POLICY,
            module,
            names=[module.params["name"]],
            policy=PolicyQosPatch(name=module.params["rename"]),
        )
        check_response(
            res,
            module,
            "Failed to rename QoS policy {0} to {1}".format(
                module.params["name"], module.params["rename"]
            ),
        )
    module.exit_json(changed=changed)


def delete_policy(module, array):
    """Delete a QoS policy, refusing while it is still attached to a directory"""
    changed = True
    attached = _attached_directories(module, array)
    if attached:
        module.fail_json(
            msg="Cannot delete QoS policy {0} while it is attached to managed "
            "directory(s): {1}. Detach it first, for example with "
            "directories: [].".format(module.params["name"], attached)
        )
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_policies_qos",
            MIN_API_VERSION_QOS_POLICY,
            module,
            names=[module.params["name"]],
        )
        check_response(
            res,
            module,
            "Failed to delete QoS policy {0}".format(module.params["name"]),
        )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            enabled=dict(type="bool"),
            rename=dict(type="str"),
            max_total_bytes_per_sec=dict(type="int"),
            max_total_ops_per_sec=dict(type="int"),
            directories=dict(type="list", elements="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required for this module")

    # Validate locally before touching the array
    _validate_limit(
        module,
        "max_total_bytes_per_sec",
        module.params["max_total_bytes_per_sec"],
        MIN_BANDWIDTH,
        MAX_BANDWIDTH,
    )
    _validate_limit(
        module,
        "max_total_ops_per_sec",
        module.params["max_total_ops_per_sec"],
        MIN_IOPS,
        MAX_IOPS,
    )
    _validate_directories(module)

    array = get_array(module)
    check_api_version(array, MIN_API_VERSION_QOS_POLICY, module, "QoS policies")

    state = module.params["state"]
    policy = _read_policy(module, array, module.params["name"])

    if state == "present" and module.params["rename"]:
        if policy:
            rename_policy(module, array)
        elif _read_policy(module, array, module.params["rename"]):
            # Already renamed, so re-running the same task has nothing left to
            # do. Recreating the old name would be the opposite of what was
            # asked for.
            module.exit_json(changed=False)
        else:
            module.fail_json(
                msg="QoS policy {0} not found to rename".format(module.params["name"])
            )
    elif state == "present" and not policy:
        create_policy(module, array)
    elif state == "present":
        update_policy(module, array, policy)
    elif state == "absent" and policy:
        delete_policy(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
