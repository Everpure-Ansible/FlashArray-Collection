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
module: purefa_tgroup
version_added: '1.43.0'
short_description: Manage topology groups on Everpure FlashArrays
description:
- Create, delete or modify topology groups on Everpure FlashArrays.
- Supports topology group rename, parent moves, and direct member management.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - The name of the topology group.
    type: str
    required: true
  state:
    description:
    - Define whether the topology group should exist or not.
    type: str
    default: present
    choices: [ absent, present ]
  rename:
    description:
    - New name of the topology group.
    type: str
  parent:
    description:
    - Parent topology group name.
    type: str
  array:
    description:
    - List of existing arrays to add to or remove from the topology group.
    type: list
    elements: str
  tgroup:
    description:
    - List of existing child topology groups to add to or remove from
      the topology group.
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
"""

EXAMPLES = r"""
- name: Create a topology group
  everpure.flasharray.purefa_tgroup:
    name: app-stack
    fa_url: 10.10.10.2
    api_token: 1234-5678-9012-3456

- name: Create a child topology group under an existing parent
  everpure.flasharray.purefa_tgroup:
    name: app-stack-dev
    parent: app-stack
    fa_url: 10.10.10.2
    api_token: 1234-5678-9012-3456

- name: Rename a topology group
  everpure.flasharray.purefa_tgroup:
    name: app-stack-dev
    rename: app-stack-qa
    fa_url: 10.10.10.2
    api_token: 1234-5678-9012-3456

- name: Add array and child topology group members
  everpure.flasharray.purefa_tgroup:
    name: app-stack
    array:
      - array-a
      - array-b
    tgroup:
      - app-stack-qa
    fa_url: 10.10.10.2
    api_token: 1234-5678-9012-3456

- name: Remove specific members from a topology group
  everpure.flasharray.purefa_tgroup:
    name: app-stack
    array:
      - array-b
    tgroup:
      - app-stack-qa
    state: absent
    fa_url: 10.10.10.2
    api_token: 1234-5678-9012-3456

- name: Delete a topology group
  everpure.flasharray.purefa_tgroup:
    name: app-stack-dev
    state: absent
    fa_url: 10.10.10.2
    api_token: 1234-5678-9012-3456
"""

RETURN = r"""
"""

HAS_PURESTORAGE = True
try:
    from pypureclient.flasharray import (
        NewName,
        ReferenceWithType,
        TgroupMembersPost,
        TgroupMembersPostMember,
        TgroupPatch,
    )
except ImportError:
    HAS_PURESTORAGE = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.flasharray.plugins.module_utils.api_helpers import (
    check_api_version,
    delete_with_context,
    get_with_context,
    patch_with_context,
    post_with_context,
)
from ansible_collections.everpure.flasharray.plugins.module_utils.purefa import (
    get_array,
    purefa_argument_spec,
)

CONTEXT_API_VERSION = "2.38"
TGROUP_API_VERSION = "2.54"


def _extract_members(members, resource_type):
    return [
        member.member.name
        for member in members
        if getattr(getattr(member, "member", None), "resource_type", None)
        == resource_type
        and getattr(getattr(member, "member", None), "name", None)
    ]


def _missing_names(requested_names, items):
    found_names = {
        getattr(item, "name", None) for item in items if getattr(item, "name", None)
    }
    return sorted(set(requested_names or []).difference(found_names))


def _error_text(res):
    """Render every error of an ErrorResponse, message and context included.

    Topology group errors often carry the useful detail in `context` while
    `message` is None, so reporting only errors[0].message loses the cause.
    """
    parts = []
    for err in getattr(res, "errors", None) or []:
        message = getattr(err, "message", None)
        context = getattr(err, "context", None)
        if message and context:
            parts.append(f"{message} ({context})")
        elif message or context:
            parts.append(str(message or context))
    if not parts:
        return f"HTTP {getattr(res, 'status_code', 'unknown')} with no error detail"
    return "; ".join(parts)


def fail_on_error(res, module, operation):
    """Fail the module with the full error list when a response is not 200."""
    status_code = getattr(res, "status_code", None)
    if isinstance(status_code, int) and status_code != 200:
        module.fail_json(
            msg=f"{operation} failed. Error: {_error_text(res)}",
            status_code=status_code,
            changed=False,
        )


def check_fleet_membership(module, array):
    """Topology groups describe fleet topology; fail early outside a fleet."""
    res = array.get_fleets()
    if getattr(res, "status_code", None) == 200 and not list(
        getattr(res, "items", []) or []
    ):
        module.fail_json(
            msg="Topology groups require the array to be a member of a fleet."
        )


def get_tgroup(module, array, name=None):
    res = get_with_context(
        array,
        "get_topology_groups",
        CONTEXT_API_VERSION,
        module,
        names=[name or module.params["name"]],
    )
    items = list(getattr(res, "items", []) or [])
    if res.status_code == 200 and items:
        return items[0]
    return None


def get_tgroup_members(module, array, name=None):
    res = get_with_context(
        array,
        "get_topology_groups_members",
        CONTEXT_API_VERSION,
        module,
        topology_group_names=[name or module.params["name"]],
    )
    if res.status_code == 200:
        return list(res.items)
    return []


def rename_exists(module, array):
    res = get_with_context(
        array,
        "get_topology_groups",
        CONTEXT_API_VERSION,
        module,
        names=[module.params["rename"]],
    )
    return bool(res.status_code == 200 and list(getattr(res, "items", []) or []))


def _build_members_payload(array_members=None, child_tgroups=None):
    members = []
    for array_member in sorted(set(array_members or [])):
        members.append(
            TgroupMembersPostMember(
                member=ReferenceWithType(
                    name=array_member,
                    resource_type="remote-arrays",
                )
            )
        )
    for child_tgroup in sorted(set(child_tgroups or [])):
        members.append(
            TgroupMembersPostMember(
                member=ReferenceWithType(
                    name=child_tgroup, resource_type="topology-groups"
                )
            )
        )
    return TgroupMembersPost(members=members)


def add_members(module, array, tgroup_name, array_members=None, child_tgroups=None):
    if not (array_members or child_tgroups):
        return
    res = post_with_context(
        array,
        "post_topology_groups_members",
        CONTEXT_API_VERSION,
        module,
        topology_group_names=[tgroup_name],
        members=_build_members_payload(array_members, child_tgroups),
    )
    fail_on_error(
        res,
        module,
        f"Failed to add members to topology group {tgroup_name}",
    )


def remove_members(module, array, tgroup_name, member_names):
    if not member_names:
        return
    res = delete_with_context(
        array,
        "delete_topology_groups_members",
        CONTEXT_API_VERSION,
        module,
        topology_group_names=[tgroup_name],
        member_names=member_names,
    )
    fail_on_error(
        res,
        module,
        f"Failed to remove members from topology group {tgroup_name}",
    )


def validate_inputs(module, array, current_tgroup=None, current_members=None):
    requested_children = module.params["tgroup"] or []
    requested_parent = module.params["parent"]
    invalid_self_refs = {module.params["name"]}
    if module.params["rename"]:
        invalid_self_refs.add(module.params["rename"])

    if requested_parent:
        if requested_parent in invalid_self_refs:
            module.fail_json(msg="A topology group cannot be its own parent.")
        if requested_parent in requested_children:
            module.fail_json(
                msg=(
                    "A topology group cannot use the same topology group "
                    "as both parent and child member."
                )
            )
        if not get_tgroup(module, array, requested_parent):
            module.fail_json(
                msg=f"Parent topology group {requested_parent} does not exist."
            )
        if current_tgroup:
            current_child_tgroups = _extract_members(
                current_members or [], "topology-groups"
            )
            if requested_parent in current_child_tgroups:
                module.fail_json(
                    msg=(
                        f"Cannot move topology group {module.params['name']} "
                        f"under direct child topology group {requested_parent}."
                    )
                )

    if requested_children:
        for child_tgroup in requested_children:
            if child_tgroup in invalid_self_refs:
                module.fail_json(
                    msg="A topology group cannot be a child member of itself."
                )
        res = get_with_context(
            array,
            "get_topology_groups",
            CONTEXT_API_VERSION,
            module,
            names=requested_children,
        )
        fail_on_error(res, module, "Child topology group not found")
        missing_children = _missing_names(requested_children, getattr(res, "items", []))
        if missing_children:
            module.fail_json(
                msg=f"Child topology group not found: {', '.join(missing_children)}"
            )

    if module.params["array"]:
        res = array.get_remote_arrays(current_fleet_only=True)
        fail_on_error(res, module, "Array not found")
        missing_arrays = _missing_names(
            module.params["array"], getattr(res, "items", [])
        )
        if missing_arrays:
            module.fail_json(msg=f"Array not found: {', '.join(missing_arrays)}")


def create_tgroup(module, array):
    if module.params["rename"]:
        module.fail_json(
            msg=(
                f"Topology group {module.params['name']} does not exist - "
                "rename failed."
            )
        )

    changed = True
    if not module.check_mode:
        kwargs = {"names": [module.params["name"]]}
        if module.params["parent"]:
            kwargs["parent_topology_group_names"] = [module.params["parent"]]
        res = post_with_context(
            array,
            "post_topology_groups",
            CONTEXT_API_VERSION,
            module,
            **kwargs,
        )
        fail_on_error(
            res,
            module,
            f"Failed to create topology group {module.params['name']}",
        )
        add_members(
            module,
            array,
            module.params["name"],
            module.params["array"],
            module.params["tgroup"],
        )
    module.exit_json(changed=changed)


def update_tgroup(module, array, tgroup=None, members=None):
    changed = False
    renamed = False
    current_tgroup = tgroup or get_tgroup(module, array)
    current_members = (
        members if members is not None else get_tgroup_members(module, array)
    )
    current_name = current_tgroup.name
    current_parent = getattr(
        getattr(current_tgroup, "parent_topology_group", None), "name", None
    )
    current_arrays = _extract_members(current_members, "remote-arrays")
    current_child_tgroups = _extract_members(current_members, "topology-groups")

    if module.params["state"] == "present":
        if module.params["rename"] and module.params["rename"] != current_name:
            if not rename_exists(module, array):
                changed = True
                if not module.check_mode:
                    res = patch_with_context(
                        array,
                        "patch_topology_groups",
                        CONTEXT_API_VERSION,
                        module,
                        names=[current_name],
                        topology_group=TgroupPatch(
                            topology_group=NewName(name=module.params["rename"])
                        ),
                    )
                    fail_on_error(
                        res,
                        module,
                        f"Rename to {module.params['rename']}",
                    )
                current_name = module.params["rename"]
                renamed = True
            else:
                module.warn(
                    (
                        f"Rename failed. Topology group "
                        f"{module.params['rename']} already exists. "
                        "Continuing with other changes..."
                    )
                )

        if module.params["parent"] and module.params["parent"] != current_parent:
            changed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_topology_groups",
                    CONTEXT_API_VERSION,
                    module,
                    names=[current_name],
                    topology_group=TgroupPatch(),
                    to_parent_topology_group_names=[module.params["parent"]],
                )
                fail_on_error(
                    res,
                    module,
                    (
                        f"Failed to move topology group {current_name} "
                        f"under parent {module.params['parent']}"
                    ),
                )

        new_arrays = sorted(
            set(module.params["array"] or []).difference(set(current_arrays))
        )
        new_tgroups = sorted(
            set(module.params["tgroup"] or []).difference(set(current_child_tgroups))
        )
        if new_arrays or new_tgroups:
            changed = True
            if not module.check_mode:
                add_members(
                    module,
                    array,
                    current_name,
                    new_arrays,
                    new_tgroups,
                )
    else:
        old_arrays = sorted(
            set(module.params["array"] or []).intersection(set(current_arrays))
        )
        old_tgroups = sorted(
            set(module.params["tgroup"] or []).intersection(set(current_child_tgroups))
        )
        if old_arrays or old_tgroups:
            changed = True
            if not module.check_mode:
                remove_members(
                    module,
                    array,
                    current_name,
                    old_arrays + old_tgroups,
                )

    module.exit_json(changed=changed or renamed)


def delete_tgroup(module, array):
    changed = True
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_topology_groups",
            CONTEXT_API_VERSION,
            module,
            names=[module.params["name"]],
        )
        fail_on_error(
            res,
            module,
            f"Failed to delete topology group {module.params['name']}",
        )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            state=dict(
                type="str",
                default="present",
                choices=["absent", "present"],
            ),
            rename=dict(type="str"),
            parent=dict(type="str"),
            array=dict(type="list", elements="str"),
            tgroup=dict(type="list", elements="str"),
            context=dict(type="str", default=""),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    if not HAS_PURESTORAGE:
        module.fail_json(msg="py-pure-client sdk is required.")

    array = get_array(module)
    check_api_version(array, TGROUP_API_VERSION, module, "Topology groups")
    check_fleet_membership(module, array)

    current_tgroup = get_tgroup(module, array)
    current_members = get_tgroup_members(module, array) if current_tgroup else []
    validate_inputs(module, array, current_tgroup, current_members)

    if current_tgroup and module.params["state"] == "present":
        update_tgroup(module, array, current_tgroup, current_members)
    elif (
        current_tgroup
        and module.params["state"] == "absent"
        and (module.params["array"] or module.params["tgroup"])
    ):
        update_tgroup(module, array, current_tgroup, current_members)
    elif current_tgroup and module.params["state"] == "absent":
        delete_tgroup(module, array)
    elif current_tgroup is None and module.params["state"] == "absent":
        module.exit_json(changed=False)
    elif (
        current_tgroup is None
        and module.params["rename"]
        and rename_exists(module, array)
    ):
        # Rename already completed on an earlier run
        module.exit_json(changed=False)
    else:
        create_tgroup(module, array)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
