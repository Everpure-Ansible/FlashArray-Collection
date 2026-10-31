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
module: purefa_dsrole
version_added: '1.0.0'
short_description: Configure FlashArray Directory Service Roles
description:
- Set or erase directory services role configurations.
author:
- Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
    - Name of role
    - If not providied, will be assigned to the same as I(role)
    type: str
    version_added: 1.32.0
  state:
    description:
    - Create or delete directory service role
    type: str
    default: present
    choices: [ absent, present ]
  role:
    description:
    - The built-in directory service role to work on.
    - Mutually exclusive with I(access_policy).
    - Either I(role) or I(access_policy) is required when I(state=present).
    type: str
    choices: [ array_admin, ops_admin, readonly, storage_admin ]
  access_policy:
    description:
    - Name of a custom management access policy to bind the directory
      service role to, instead of a built-in I(role).
    - Mutually exclusive with I(role).
    - Either I(role) or I(access_policy) is required when I(state=present).
    - Requires Purity//FA 6.6.9, or higher (REST 2.36).
    type: str
    version_added: '1.44.0'
  group_base:
    type: str
    description:
    - Specifies where the configured group is located in the directory
      tree. This field consists of Organizational Units (OUs) that combine
      with the base DN attribute and the configured group CNs to complete
      the full Distinguished Name of the groups. The group base should
      specify OU= for each OU and multiple OUs should be separated by commas.
      The order of OUs is important and should get larger in scope from left
      to right.
    - Each OU should not exceed 64 characters in length.
  group:
    type: str
    description:
    - Sets the common Name (CN) of the configured directory service group
      containing users for the FlashBlade. This name should be just the
      Common Name of the group without the CN= specifier.
    - Common Names should not exceed 64 characters in length.
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
- name: Delete existing array_admin directory service role
  everpure.flasharray.purefa_dsrole:
    role: array_admin
    state: absent
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create observability directory service role with readonly policy
  everpure.flasharray.purefa_dsrole:
    name: observability
    role: readonly
    group_base: "OU=PureGroups,OU=ReadOnly"
    group: o11y
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Update system-defined array_admin directory service role
  everpure.flasharray.purefa_dsrole:
    role: array_admin
    group_base: "OU=PureGroups,OU=SANManagers"
    group: pureadmins
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Update directory service role policy
  everpure.flasharray.purefa_dsrole:
    name: observability
    role: ops_admin
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592

- name: Create directory service role bound to a custom management access policy
  everpure.flasharray.purefa_dsrole:
    name: realm-admins
    access_policy: my-realm-policy
    group_base: "OU=PureGroups,OU=RealmAdmins"
    group: realmadmins
    fa_url: 10.10.10.2
    api_token: e31060a7-21fc-e277-6240-25983c6c4592
"""

RETURN = r"""
"""

MIN_DSROLE_API_VERSION = "2.30"
POLICY_API_VERSION = "2.36"
CONTEXT_VERSION = "2.42"

HAS_PYPURECLIENT = True
try:
    from pypureclient.flasharray import (
        DirectoryServiceRole,
        DirectoryServiceRolePost,
        Reference,
        ReferenceNoId,
        ReferenceWithType,
        FixedReferenceWithType,
    )
except ImportError:
    HAS_PYPURECLIENT = False


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
    delete_with_context,
    get_with_context,
    patch_with_context,
    post_with_context,
)


def update_role(module, array):
    """Update Directory Service Role"""
    changed = False
    # Check for special case of deleting a system-defined role.
    # Here we have to just blank out the group and group_base fields
    if module.params["state"] == "absent":
        if not module.check_mode:
            res = patch_with_context(
                array,
                "patch_directory_services_roles",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                directory_service_roles=DirectoryServiceRole(
                    group_base="",
                    group="",
                ),
            )
            check_response(
                res,
                module,
                f"Deleting system-defined Directory Service Role "
                f"{module.params['name']}",
            )
        module.exit_json(changed=True)

    res = get_with_context(
        array,
        "get_directory_services_roles",
        CONTEXT_VERSION,
        module,
        names=[module.params["name"]],
    )
    role = list(res.items)[0]
    if module.params["name"] not in [
        "array_admin",
        "storage_admin",
        "ops_admin",
        "readonly",
    ]:
        if module.params.get("access_policy"):
            current_policies = sorted(
                policy.name
                for policy in (getattr(role, "management_access_policies", None) or [])
            )
            if (
                getattr(role, "group_base", None) != module.params["group_base"]
                or getattr(role, "group", None) != module.params["group"]
                or current_policies != [module.params["access_policy"]]
            ):
                changed = True
                if not module.check_mode:
                    res = patch_with_context(
                        array,
                        "patch_directory_services_roles",
                        CONTEXT_VERSION,
                        module,
                        names=[module.params["name"]],
                        directory_service_roles=DirectoryServiceRole(
                            group_base=module.params["group_base"],
                            group=module.params["group"],
                            management_access_policies=[
                                FixedReferenceWithType(
                                    name=module.params["access_policy"]
                                )
                            ],
                        ),
                    )
                    check_response(
                        res,
                        module,
                        f"Update Directory Service Role {module.params['name']}",
                    )
        elif (
            getattr(role, "group_base", None) != module.params["group_base"]
            or getattr(role, "group", None) != module.params["group"]
            or getattr(getattr(role, "role", None), "name", None)
            != module.params["role"]
        ):
            changed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_directory_services_roles",
                    CONTEXT_VERSION,
                    module,
                    names=[module.params["name"]],
                    directory_service_roles=DirectoryServiceRole(
                        group_base=module.params["group_base"],
                        group=module.params["group"],
                        role=Reference(name=module.params["role"]),
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Update Directory Service Role {module.params['name']}",
                )
    else:
        if (
            getattr(role, "group_base", None) != module.params["group_base"]
            or getattr(role, "group", None) != module.params["group"]
        ):
            changed = True
            if not module.check_mode:
                res = patch_with_context(
                    array,
                    "patch_directory_services_roles",
                    CONTEXT_VERSION,
                    module,
                    names=[module.params["name"]],
                    directory_service_roles=DirectoryServiceRole(
                        group_base=module.params["group_base"],
                        group=module.params["group"],
                    ),
                )
                check_response(
                    res,
                    module,
                    f"Update Directory Service Role {module.params['name']}",
                )
    module.exit_json(changed=changed)


def delete_role(module, array):
    """Delete Directory Service Role"""
    changed = True
    if not module.check_mode:
        res = delete_with_context(
            array,
            "delete_directory_services_roles",
            CONTEXT_VERSION,
            module,
            names=[module.params["name"]],
        )
        check_response(
            res,
            module,
            f"Delete Directory Service Role {module.params['name']}",
        )
    module.exit_json(changed=changed)


def create_role(module, array):
    """Create Directory Service Role"""
    changed = False
    api_version = array.get_rest_version()
    if not module.params["group"] == "" or not module.params["group_base"] == "":
        changed = True
        if not module.check_mode:
            if module.params.get("access_policy"):
                role_config = DirectoryServiceRolePost(
                    group_base=module.params["group_base"],
                    group=module.params["group"],
                    management_access_policies=[
                        ReferenceWithType(name=module.params["access_policy"])
                    ],
                )
            elif LooseVersion(api_version) >= LooseVersion(POLICY_API_VERSION):
                role_config = DirectoryServiceRolePost(
                    group_base=module.params["group_base"],
                    group=module.params["group"],
                    role=ReferenceNoId(name=module.params["role"]),
                )
            else:
                role_config = DirectoryServiceRole(
                    group_base=module.params["group_base"],
                    group=module.params["group"],
                )
            res = post_with_context(
                array,
                "post_directory_services_roles",
                CONTEXT_VERSION,
                module,
                names=[module.params["name"]],
                directory_service_roles=role_config,
            )
            check_response(
                res,
                module,
                f"Create Directory Service Role {module.params['name']}",
            )
    module.exit_json(changed=changed)


def main():
    argument_spec = purefa_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str"),
            role=dict(
                type="str",
                choices=["array_admin", "ops_admin", "readonly", "storage_admin"],
            ),
            access_policy=dict(type="str"),
            state=dict(type="str", default="present", choices=["absent", "present"]),
            group_base=dict(type="str"),
            group=dict(type="str"),
            context=dict(type="str", default=""),
        )
    )

    # When creating/updating a role either a built-in role or a custom
    # management access policy must be supplied, but never both.
    required_if = [["state", "present", ["role", "access_policy"], True]]
    required_together = [["group", "group_base"]]
    mutually_exclusive = [["role", "access_policy"]]

    module = AnsibleModule(
        argument_spec,
        required_together=required_together,
        required_if=required_if,
        mutually_exclusive=mutually_exclusive,
        supports_check_mode=True,
    )

    if not HAS_PYPURECLIENT:
        module.fail_json(msg="pypureclient sdk is required for this module")

    state = module.params["state"]
    array = get_array(module)
    if not module.params["name"]:
        module.params["name"] = module.params["role"] or module.params["access_policy"]
    api_version = array.get_rest_version()
    if LooseVersion(MIN_DSROLE_API_VERSION) > LooseVersion(api_version):
        module.fail_json(
            msg="This module requires Purity//FA 6.6.3 and higher. "
            "For older Purity versions please use the ``purefa_dsrole_old`` module"
        )
    if module.params["access_policy"] and LooseVersion(
        POLICY_API_VERSION
    ) > LooseVersion(api_version):
        module.fail_json(
            msg="access_policy requires Purity//FA 6.6.9, or higher (REST 2.36)."
        )
    role_configured = False
    role = {}
    res = get_with_context(
        array,
        "get_directory_services_roles",
        CONTEXT_VERSION,
        module,
        names=[module.params["name"]],
    )
    if res.status_code == 200:
        role = list(res.items)[0]
    # A cleared role reads back with group "" rather than no group at all
    if getattr(role, "group", None):
        role_configured = True

    if state == "absent" and role_configured:
        if module.params["name"] in [
            "array_admin",
            "storage_admin",
            "ops_admin",
            "readonly",
        ]:
            update_role(module, array)
        else:
            delete_role(module, array)
    elif role_configured and state == "present":
        update_role(module, array)
    elif not role_configured and state == "present":
        # check for system-defined role and update it instead of creating it
        if module.params["name"] in [
            "array_admin",
            "storage_admin",
            "ops_admin",
            "readonly",
        ]:
            update_role(module, array)
        else:
            create_role(module, array)
    else:
        module.exit_json(changed=False)


if __name__ == "__main__":
    main()
